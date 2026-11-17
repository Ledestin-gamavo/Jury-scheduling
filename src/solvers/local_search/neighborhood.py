"""Génération bornée des voisins d'une solution.

Le :class:`NeighborhoodGenerator` propose des **mouvements candidats** pour les
cinq voisinages de :class:`~solvers.local_search.move_operator.MoveType`. Il ne
garantit pas la faisabilité : il applique seulement des **préfiltres peu coûteux**
(disponibilités statiques, occupation du créneau cible) qui éliminent la plupart
des candidats impossibles. Le test exact est fait ensuite par
:meth:`~solvers.local_search.move_operator.MoveOperator.is_feasible`.

Aucune explosion combinatoire. Trois garde-fous :

1. chaque voisinage s'arrête après ``max_moves_per_neighborhood`` mouvements ;
2. au plus ``max_alternatives_per_session`` alternatives par séance, par étudiant
   ou par encadrant, tirées au hasard ;
3. l'ordre de parcours des séances est mélangé à chaque appel : des itérations
   successives explorent des régions différentes, sans parcourir tout l'espace.

Reproductibilité : les séances sont d'abord triées de façon déterministe, puis
mélangées par le générateur pseudo-aléatoire fourni. À graine identique, les
mêmes mouvements sont générés dans le même ordre, quel que soit l'ordre des
séances dans la solution.

Les fonctions lisent l'état sans le modifier.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from random import Random
from typing import TypeVar

from core.enums import Phase
from core.session import Session
from preprocessing import PreprocessingContext, TimeSlot
from solvers.greedy import ScheduleState

from .local_search_config import LocalSearchConfig
from .move_operator import Move, MoveType, SessionChange

__all__ = ["NeighborhoodGenerator"]

_T = TypeVar("_T")


@dataclass(frozen=True)
class _Block:
    """Bloc de séances d'un encadrant (usage interne).

    Un bloc est une suite maximale de créneaux consécutifs d'un même jour, pour un
    même encadrant (et une même salle en finale), comme dans la métrique
    ``supervisor_group_breaks``.

    Attributes:
        day: Jour du bloc.
        room_id: Salle du bloc (``None`` en pré-soutenance).
        start: Premier créneau.
        end: Dernier créneau.
        sessions: Séances du bloc.
    """

    day: int
    room_id: str | None
    start: int
    end: int
    sessions: tuple[Session, ...]

    @property
    def length(self) -> int:
        """Nombre de créneaux consécutifs occupés."""
        return self.end - self.start + 1


class NeighborhoodGenerator:
    """Génère des mouvements candidats pour les cinq voisinages.

    Args:
        context: Contexte de pré-traitement (disponibilités, jurys).
        config: Configuration de la recherche locale (limites de voisinage).
        rng: Générateur pseudo-aléatoire (créé à partir de ``config.random_seed``
            s'il est absent).
    """

    def __init__(
        self,
        context: PreprocessingContext,
        config: LocalSearchConfig,
        rng: Random | None = None,
    ) -> None:
        self._context = context
        self._instance = context.instance
        self._avail = context.availability
        self._jury = context.jury
        self._config = config
        self._rng = rng if rng is not None else Random(config.random_seed)
        self._slots_cache: dict[tuple[str, str, str, Phase], tuple[TimeSlot, ...]] = {}
        self._generators = {
            MoveType.CHANGE_SLOT: self.generate_slot_moves,
            MoveType.CHANGE_ROOM: self.generate_room_moves,
            MoveType.CHANGE_JURY: self.generate_jury_moves,
            MoveType.SWAP_SESSIONS: self.generate_swap_moves,
            MoveType.MOVE_SUPERVISOR_BLOCK: self.generate_block_moves,
        }

    # Utilitaires
    def _cap_reached(self, moves: Sequence[Move]) -> bool:
        """Indique si la limite de mouvements du voisinage est atteinte."""
        cap = self._config.max_moves_per_neighborhood
        return cap is not None and len(moves) >= cap

    def _sample(self, items: Sequence[_T], limit: int | None) -> list[_T]:
        """Retourne au plus ``limit`` éléments tirés au hasard (tous si ``limit`` est ``None``)."""
        if limit is None or len(items) <= limit:
            return list(items)
        return self._rng.sample(list(items), limit)

    def _shuffled(self, sessions: Iterable[Session]) -> list[Session]:
        """Trie les séances de façon déterministe puis les mélange."""
        ordered = sorted(sessions, key=lambda session: session.sort_key)
        self._rng.shuffle(ordered)
        return ordered

    @staticmethod
    def _sessions_by_student(sessions: Iterable[Session]) -> dict[str, list[Session]]:
        """Regroupe les séances par étudiant."""
        grouped: dict[str, list[Session]] = {}
        for session in sessions:
            grouped.setdefault(session.student_id, []).append(session)
        return grouped

    def _static_slots(self, session: Session) -> tuple[TimeSlot, ...]:
        """Créneaux où l'étudiant et tout le jury de la séance sont disponibles (mémorisés)."""
        key = (session.student_id, session.president_id, session.examiner_id, session.phase)
        cached = self._slots_cache.get(key)
        if cached is None:
            cached = self._jury.pair_slots(
                session.student_id, session.president_id, session.examiner_id, session.phase
            )
            self._slots_cache[key] = cached
        return cached

    def _room_for_slot(
        self, state: ScheduleState, session: Session, day: int, slot: int
    ) -> str | None:
        """Choisit la salle d'une finale déplacée à ``(day, slot)``.

        Priorité à la salle actuelle si elle est disponible et libre ; sinon une
        salle utilisable tirée au hasard ; ``None`` s'il n'y en a aucune.
        """
        current = session.room_id
        if (
            current is not None
            and session.day == day
            and self._avail.room_available(current, day, slot)
            and state.room_free(current, day, slot)
        ):
            return current
        rooms = state.free_rooms(day, slot)
        if not rooms:
            return None
        if current in rooms:
            return current
        return self._rng.choice(rooms)

    # API principale
    def generate_moves(
        self,
        sessions: Sequence[Session],
        state: ScheduleState,
        *,
        types: Iterable[MoveType] | None = None,
    ) -> list[Move]:
        """Génère les mouvements candidats de tous les voisinages actifs.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant (non modifié).
            types: Voisinages à utiliser (``config.enabled_neighborhoods`` par défaut).

        Returns:
            Les mouvements, au plus ``max_moves_per_neighborhood`` par voisinage,
            mélangés si ``config.shuffle_moves`` est vrai.
        """
        wanted = tuple(types) if types is not None else self._config.enabled_neighborhoods
        moves: list[Move] = []
        for move_type in wanted:
            moves.extend(self._generators[MoveType(move_type)](sessions, state))
        if self._config.shuffle_moves:
            self._rng.shuffle(moves)
        return moves

    # Voisinage 1 : changer de créneau
    def generate_slot_moves(self, sessions: Sequence[Session], state: ScheduleState) -> list[Move]:
        """Génère les déplacements d'une séance vers un autre créneau.

        Pour chaque séance, les créneaux candidats sont ceux où l'étudiant et tous
        les participants sont disponibles (statique), dans la période de la phase,
        et où l'étudiant et les participants ne sont pas déjà occupés. Pour une
        finale, la salle est conservée si possible, sinon une salle utilisable est
        choisie. Les plafonds journaliers sont contrôlés ensuite.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant.

        Returns:
            Les mouvements ``CHANGE_SLOT``.
        """
        moves: list[Move] = []
        limit = self._config.max_alternatives_per_session
        for session in self._shuffled(sessions):
            if self._cap_reached(moves):
                break
            attendees = self._instance.attending_teacher_ids(session)
            candidates = [
                (day, slot)
                for day, slot in self._static_slots(session)
                if (day, slot) != session.time_slot
                and state.student_free(session.student_id, day, slot)
                and all(state.teacher_free(teacher, day, slot) for teacher in attendees)
            ]
            for day, slot in self._sample(candidates, limit):
                room_id: str | None = None
                if session.phase is Phase.FINAL:
                    room_id = self._room_for_slot(state, session, day, slot)
                    if room_id is None:
                        continue
                moved = replace(session, day=day, slot=slot, room_id=room_id)
                moves.append(Move.single(MoveType.CHANGE_SLOT, session, moved))
                if self._cap_reached(moves):
                    break
        return moves

    # Voisinage 2 : changer de salle
    def generate_room_moves(self, sessions: Sequence[Session], state: ScheduleState) -> list[Move]:
        """Génère les changements de salle d'une finale, à horaire constant.

        Les salles candidates sont celles disponibles, libres au créneau de la
        finale et sous leur plafond journalier. Les pré-soutenances n'ont pas de
        salle et ne sont jamais concernées.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant.

        Returns:
            Les mouvements ``CHANGE_ROOM``.
        """
        moves: list[Move] = []
        limit = self._config.max_alternatives_per_session
        finals = (session for session in sessions if session.phase is Phase.FINAL)
        for session in self._shuffled(finals):
            if self._cap_reached(moves):
                break
            rooms = [
                room_id
                for room_id in state.free_rooms(session.day, session.slot)
                if room_id != session.room_id
            ]
            for room_id in self._sample(rooms, limit):
                moves.append(
                    Move.single(MoveType.CHANGE_ROOM, session, session.with_room(room_id))
                )
                if self._cap_reached(moves):
                    break
        return moves

    # Voisinage 3 : changer de binôme de jury
    def _pair_looks_possible(
        self,
        state: ScheduleState,
        pair: tuple[str, str],
        student_sessions: Sequence[Session],
    ) -> bool:
        """Préfiltre : les deux membres sont disponibles et libres pour toutes les séances.

        Un membre déjà présent à une séance de l'étudiant (ancien binôme ou
        encadrant) occupe ce créneau à cause de cette séance : il n'est pas
        considéré comme un conflit.
        """
        for session in student_sessions:
            own = self._instance.attending_teacher_ids(session)
            for member in pair:
                if not self._avail.teacher_available(member, session.day, session.slot):
                    return False
                if member not in own and not state.teacher_free(member, session.day, session.slot):
                    return False
        return True

    @staticmethod
    def _mix(
        preferred: list[tuple[str, str]], others: list[tuple[str, str]], limit: int | None
    ) -> list[tuple[str, str]]:
        """Compose la liste d'alternatives : moitié binômes déjà utilisés, moitié nouveaux."""
        if limit is None:
            return preferred + others
        head = preferred[: (limit + 1) // 2]
        chosen = head + others[: limit - len(head)]
        if len(chosen) < limit:
            chosen += preferred[len(head) : len(head) + limit - len(chosen)]
        return chosen

    def generate_jury_moves(self, sessions: Sequence[Session], state: ScheduleState) -> list[Move]:
        """Génère les changements de binôme (président, examinateur) d'un étudiant.

        Le nouveau binôme remplace l'ancien dans **toutes** les séances de
        l'étudiant (continuité). Les binômes candidats sont ceux de
        ``JuryCandidates`` (rôles, domaine de l'examinateur, personnes distinctes,
        encadrant exclu des étudiants admissibles). Les binômes déjà utilisés par
        d'autres pré-soutenances sont essayés pour moitié, car seuls eux peuvent
        réduire ``distinct_jury_pairs`` ; l'autre moitié est tirée parmi les
        nouveaux binômes, pour agir sur la charge et la présence.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant.

        Returns:
            Les mouvements ``CHANGE_JURY``.
        """
        moves: list[Move] = []
        limit = self._config.max_alternatives_per_session
        by_student = self._sessions_by_student(sessions)
        used = Counter(s.jury_pair for s in sessions if s.phase is Phase.PREDEFENCE)
        student_ids = sorted(by_student)
        self._rng.shuffle(student_ids)
        for student_id in student_ids:
            if self._cap_reached(moves):
                break
            student_sessions = sorted(by_student[student_id], key=lambda s: s.sort_key)
            current = student_sessions[0].jury_pair
            candidates = [
                pair
                for pair in self._jury.pairs_for(student_id)
                if pair != current and self._pair_looks_possible(state, pair, student_sessions)
            ]
            preferred = [pair for pair in candidates if used.get(pair, 0) > 0]
            others = [pair for pair in candidates if used.get(pair, 0) == 0]
            self._rng.shuffle(preferred)
            self._rng.shuffle(others)
            for president_id, examiner_id in self._mix(preferred, others, limit):
                changes = tuple(
                    SessionChange(s, s.with_jury(president_id, examiner_id))
                    for s in student_sessions
                )
                moves.append(Move(MoveType.CHANGE_JURY, changes))
                if self._cap_reached(moves):
                    break
        return moves

    # Voisinage 4 : échanger deux séances
    def _swap_candidate(self, first: Session, second: Session) -> bool:
        """Préfiltre statique d'un échange : participants disponibles aux horaires échangés."""
        if first.key == second.key:
            return False
        if (first.day, first.slot, first.room_id) == (second.day, second.slot, second.room_id):
            return False
        avail = self._avail
        if not avail.student_available(first.student_id, second.day, second.slot):
            return False
        if not avail.student_available(second.student_id, first.day, first.slot):
            return False
        instance = self._instance
        if not all(
            avail.teacher_available(teacher, second.day, second.slot)
            for teacher in instance.attending_teacher_ids(first)
        ):
            return False
        return all(
            avail.teacher_available(teacher, first.day, first.slot)
            for teacher in instance.attending_teacher_ids(second)
        )

    @staticmethod
    def _swap_move(first: Session, second: Session) -> Move:
        """Construit l'échange des placements (jour, créneau, salle) de deux séances."""
        new_first = replace(first, day=second.day, slot=second.slot, room_id=second.room_id)
        new_second = replace(second, day=first.day, slot=first.slot, room_id=first.room_id)
        return Move(
            MoveType.SWAP_SESSIONS,
            (SessionChange(first, new_first), SessionChange(second, new_second)),
        )

    def generate_swap_moves(self, sessions: Sequence[Session], state: ScheduleState) -> list[Move]:
        """Génère les échanges de placements entre deux séances de la même phase.

        Chaque jury reste avec son étudiant. Pour borner le coût, un échantillon
        d'au plus ``4 × max_alternatives_per_session`` partenaires est examiné par
        séance, puis filtré par disponibilité statique. Les paires sont
        dédoublonnées. La faisabilité complète (occupations, plafonds) est testée
        ensuite sur l'état où les deux séances sont retirées ensemble.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant (non utilisé ici ; conservé pour
                l'uniformité de signature des générateurs).

        Returns:
            Les mouvements ``SWAP_SESSIONS``.
        """
        moves: list[Move] = []
        seen: set[frozenset[tuple[str, Phase]]] = set()
        limit = self._config.max_alternatives_per_session
        for phase in Phase:
            group = sorted(
                (s for s in sessions if s.phase is phase), key=lambda s: s.sort_key
            )
            if len(group) < 2:
                continue
            for first in self._shuffled(group):
                if self._cap_reached(moves):
                    break
                pool = group if limit is None else self._sample(group, 4 * limit)
                partners = [second for second in pool if self._swap_candidate(first, second)]
                for second in self._sample(partners, limit):
                    pair_key = frozenset((first.key, second.key))
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)
                    moves.append(self._swap_move(first, second))
                    if self._cap_reached(moves):
                        break
        return moves

    # Voisinage 5 : déplacement d'un bloc d'encadrant
    def _blocks(self, sessions: Sequence[Session], phase: Phase) -> dict[str, list[_Block]]:
        """Calcule les blocs de chaque encadrant pour une phase.

        Définition alignée sur la métrique ``supervisor_group_breaks`` : en
        pré-soutenance, suites de créneaux distincts consécutifs d'un même jour ;
        en finale, suites de créneaux consécutifs d'une même salle et d'un même jour.
        """
        grouped: dict[tuple[str, int, str | None], dict[int, list[Session]]] = {}
        for session in sessions:
            if session.phase is not phase:
                continue
            supervisor = self._instance.student(session.student_id).supervisor_id
            room_id = session.room_id if phase is Phase.FINAL else None
            grouped.setdefault((supervisor, session.day, room_id), {}).setdefault(
                session.slot, []
            ).append(session)

        blocks: dict[str, list[_Block]] = {}

        def close(supervisor: str, day: int, room_id: str | None, run: list[int], by_slot: dict[int, list[Session]]) -> None:
            members = tuple(
                sorted((s for slot in run for s in by_slot[slot]), key=lambda s: s.sort_key)
            )
            blocks.setdefault(supervisor, []).append(
                _Block(day, room_id, run[0], run[-1], members)
            )

        for key in sorted(grouped, key=lambda k: (k[0], k[1], k[2] or "")):
            supervisor, day, room_id = key
            by_slot = grouped[key]
            run: list[int] = []
            for slot in sorted(by_slot):
                if run and slot != run[-1] + 1:
                    close(supervisor, day, room_id, run, by_slot)
                    run = []
                run.append(slot)
            if run:
                close(supervisor, day, room_id, run, by_slot)
        return blocks

    def _block_move(
        self, phase: Phase, moved: _Block, anchor: _Block, after: bool
    ) -> Move | None:
        """Construit le déplacement du bloc ``moved`` juste après ou avant ``anchor``.

        Le bloc garde son organisation interne (mêmes écarts de créneaux). Il
        prend le jour de l'ancre et, en finale, sa salle. Retourne ``None`` si le
        résultat sort des créneaux d'une journée ou de la période de la phase.
        """
        length = moved.length
        target_start = anchor.end + 1 if after else anchor.start - length
        if target_start < 0 or target_start + length > self._instance.slots_per_day:
            return None
        shift = target_start - moved.start
        changes: list[SessionChange] = []
        for session in moved.sessions:
            new_slot = session.slot + shift
            if not self._avail.is_slot_allowed(phase, anchor.day, new_slot):
                return None
            new = replace(session, day=anchor.day, slot=new_slot, room_id=anchor.room_id)
            if new != session:
                changes.append(SessionChange(session, new))
        if not changes:
            return None
        return Move(MoveType.MOVE_SUPERVISOR_BLOCK, tuple(changes))

    def generate_block_moves(self, sessions: Sequence[Session], state: ScheduleState) -> list[Move]:
        """Génère les déplacements d'un bloc d'encadrant vers un autre bloc du même encadrant.

        Seuls les encadrants ayant au moins deux blocs dans une phase sont
        concernés : c'est la situation où ``supervisor_group_breaks`` est positif.
        Pour chaque couple (bloc déplacé, bloc ancre), deux mouvements sont
        proposés : juste après l'ancre, juste avant l'ancre. Le nombre de couples
        par encadrant est borné par ``max_alternatives_per_session``.

        Args:
            sessions: Séances de la solution courante.
            state: État d'occupation correspondant (non utilisé ici ; la
                faisabilité est testée ensuite par :class:`MoveOperator`).

        Returns:
            Les mouvements ``MOVE_SUPERVISOR_BLOCK``.
        """
        moves: list[Move] = []
        limit = self._config.max_alternatives_per_session
        for phase in Phase:
            blocks_by_supervisor = self._blocks(sessions, phase)
            supervisors = sorted(
                supervisor for supervisor, blocks in blocks_by_supervisor.items() if len(blocks) >= 2
            )
            self._rng.shuffle(supervisors)
            for supervisor in supervisors:
                if self._cap_reached(moves):
                    break
                blocks = blocks_by_supervisor[supervisor]
                couples = [(m, a) for m in blocks for a in blocks if m is not a]
                for moved, anchor in self._sample(couples, limit):
                    for after in (True, False):
                        move = self._block_move(phase, moved, anchor, after)
                        if move is not None:
                            moves.append(move)
                        if self._cap_reached(moves):
                            break
                    if self._cap_reached(moves):
                        break
        return moves