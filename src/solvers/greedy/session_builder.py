"""État d'occupation et construction de séances valides.

Ce module contient deux classes :

* :class:`ScheduleState` : état d'occupation **mutable** d'un planning en cours
  de construction. Il tient à jour, de façon incrémentale, les occupations
  (enseignants, étudiants, salles), les compteurs journaliers (plafonds), les
  charges, l'usage des binômes et les positions des séances par encadrant
  (regroupement). Toutes les requêtes sont en temps constant ou presque.
* :class:`SessionBuilder` : construit une séance **respectant toutes les
  contraintes dures** vis-à-vis de l'état courant, en s'appuyant sur
  ``AvailabilityMatrix``, ``JuryCandidates`` et ``DomainFilters`` du module
  ``preprocessing``.

Contraintes dures garanties par construction (contrat v4.0) : étudiant et
participants disponibles et non en chevauchement ; plafonds journaliers des
enseignants (toutes phases confondues) et des salles (finales seulement) ;
période commune de la phase ; salle ``None`` en ligne, salle existante,
disponible et libre en finale ; président habilité, examinateur habilité et
couvrant le domaine, personnes distinctes (l'encadrant est le troisième membre
d'une finale) ; continuité du binôme entre les deux phases.

Propriété d'indépendance des phases. Les périodes de pré-soutenance et de
finale sont des ensembles de jours **disjoints**, et toutes les contraintes dures
portent sur un créneau précis, un jour précis ou une salle (utilisée seulement
en finale). Placer la pré-soutenance d'un étudiant ne modifie donc jamais la
faisabilité de sa finale, et inversement ; seul le **binôme** les relie. Cela
permet de planifier un étudiant en entier (:meth:`SessionBuilder.build_student`)
sans validation intermédiaire de la première séance.

Ce module ne dépend que de ``core``, ``preprocessing`` et du paquet courant.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable
from random import Random

from core.enums import Phase, Role
from core.instance import Instance
from core.session import Session
from core.solution import Solution
from core.student import Student
from preprocessing import AvailabilityMatrix, Pair, PreprocessingContext, TimeSlot

from .candidate_ranking import rank_jury_pairs, rank_rooms, rank_time_slots
from .greedy_config import GreedyConfig

__all__ = ["ScheduleState", "SessionBuilder"]

_EMPTY_SLOTS: frozenset[int] = frozenset()


def _decrement(counter: Counter, key: object) -> None:
    """Décrémente un compteur et supprime la clé lorsqu'elle atteint zéro."""
    counter[key] -= 1
    if counter[key] <= 0:
        del counter[key]


class ScheduleState:
    """État d'occupation d'un planning en cours de construction.

    L'état est **mutable** et ne contrôle pas la faisabilité : l'appelant doit
    n'ajouter que des séances déjà jugées faisables (par
    :class:`SessionBuilder`). Il garantit en revanche la symétrie
    ``add`` / ``remove``.

    Les compteurs reflètent les définitions du contrat :

    * la charge et le plafond journalier d'un enseignant comptent les séances
      des deux phases, quel que soit son rôle ; l'encadrant participe aux finales
      de ses étudiants ;
    * le plafond d'une salle ne compte que les finales ;
    * les groupes d'encadrant suivent la définition de ``supervisor_group_breaks``.

    Args:
        instance: Instance du problème.
        availability: Matrice de disponibilités de l'instance.
    """

    def __init__(self, instance: Instance, availability: AvailabilityMatrix) -> None:
        self._instance = instance
        self._availability = availability
        self._teacher_cap: dict[str, int] = {t.id: t.max_sessions_per_day for t in instance.teachers}
        self._room_cap: dict[str, int] = {r.id: r.max_sessions_per_day for r in instance.rooms}
        self._room_ids: tuple[str, ...] = instance.room_ids
        self._supervisor: dict[str, str] = {s.id: s.supervisor_id for s in instance.students}
        self._reset()

    def _reset(self) -> None:
        """Vide tout l'état d'occupation."""
        self._sessions: dict[tuple[str, Phase], Session] = {}
        self._teacher_busy: set[tuple[str, int, int]] = set()
        self._student_busy: set[tuple[str, int, int]] = set()
        self._room_busy: set[tuple[str, int, int]] = set()
        self._teacher_day_count: Counter = Counter()
        self._room_day_count: Counter = Counter()
        self._teacher_slots: dict[tuple[str, int], set[int]] = {}
        self._load: dict[str, int] = {tid: 0 for tid in self._instance.teacher_ids}
        self._pair_usage: Counter = Counter()
        self._sup_online: dict[str, Counter] = {}
        self._sup_final: dict[str, set[tuple[int, str, int]]] = {}

    # ==================================================================
    # Modification
    # ==================================================================
    def add(self, session: Session) -> None:
        """Ajoute une séance faisable à l'état.

        Args:
            session: Séance à ajouter (déjà vérifiée par l'appelant).

        Raises:
            ValueError: Si l'étudiant a déjà une séance pour cette phase.
            KeyError: Si l'étudiant est inconnu.
        """
        key = session.key
        if key in self._sessions:
            raise ValueError(f"Séance déjà présente pour {key[0]!r}/{key[1].value}")
        supervisor = self._supervisor[session.student_id]
        day, slot = session.day, session.slot
        for teacher_id in self._instance.attending_teacher_ids(session):
            self._teacher_busy.add((teacher_id, day, slot))
            self._teacher_day_count[(teacher_id, day)] += 1
            self._teacher_slots.setdefault((teacher_id, day), set()).add(slot)
            self._load[teacher_id] += 1
        self._student_busy.add((session.student_id, day, slot))
        if session.phase is Phase.PREDEFENCE:
            self._pair_usage[session.jury_pair] += 1
            self._sup_online.setdefault(supervisor, Counter())[(day, slot)] += 1
        else:
            room_id = session.room_id
            if room_id is None:
                raise ValueError("Une finale doit avoir une salle")
            self._room_busy.add((room_id, day, slot))
            self._room_day_count[(room_id, day)] += 1
            self._sup_final.setdefault(supervisor, set()).add((day, room_id, slot))
        self._sessions[key] = session

    def remove(self, session: Session) -> None:
        """Retire une séance de l'état (opération inverse de :meth:`add`).

        Args:
            session: Séance à retirer (identifiée par ``(étudiant, phase)``).

        Raises:
            KeyError: Si aucune séance n'existe pour cette clé.
        """
        stored = self._sessions.pop(session.key, None)
        if stored is None:
            raise KeyError(f"Aucune séance pour {session.student_id!r}/{session.phase.value}")
        supervisor = self._supervisor[stored.student_id]
        day, slot = stored.day, stored.slot
        for teacher_id in self._instance.attending_teacher_ids(stored):
            self._teacher_busy.discard((teacher_id, day, slot))
            _decrement(self._teacher_day_count, (teacher_id, day))
            slots = self._teacher_slots.get((teacher_id, day))
            if slots is not None:
                slots.discard(slot)
                if not slots:
                    del self._teacher_slots[(teacher_id, day)]
            self._load[teacher_id] -= 1
        self._student_busy.discard((stored.student_id, day, slot))
        if stored.phase is Phase.PREDEFENCE:
            _decrement(self._pair_usage, stored.jury_pair)
            _decrement(self._sup_online[supervisor], (day, slot))
        else:
            room_id = stored.room_id
            self._room_busy.discard((room_id, day, slot))
            _decrement(self._room_day_count, (room_id, day))
            self._sup_final[supervisor].discard((day, room_id, slot))

    def remove_student(self, student_id: str) -> tuple[Session, ...]:
        """Retire toutes les séances d'un étudiant.

        Args:
            student_id: Identifiant de l'étudiant.

        Returns:
            Les séances retirées (vide si l'étudiant n'avait aucune séance).
        """
        removed = self.sessions_of_student(student_id)
        for session in removed:
            self.remove(session)
        return removed

    def snapshot(self) -> tuple[Session, ...]:
        """Retourne les séances courantes, pour une restauration ultérieure."""
        return tuple(self._sessions.values())

    def restore(self, sessions: Iterable[Session]) -> None:
        """Remplace tout l'état par les séances indiquées.

        Args:
            sessions: Séances faisables (typiquement issues de :meth:`snapshot`).
        """
        self._reset()
        for session in sessions:
            self.add(session)

    # ==================================================================
    # Consultation des séances
    # ==================================================================
    def __len__(self) -> int:
        return len(self._sessions)

    def session_of(self, student_id: str, phase: Phase) -> Session | None:
        """Retourne la séance d'un étudiant pour une phase, ou ``None``."""
        return self._sessions.get((student_id, phase))

    def sessions_of_student(self, student_id: str) -> tuple[Session, ...]:
        """Retourne les séances d'un étudiant (pré-soutenance puis finale)."""
        found = (self._sessions.get((student_id, phase)) for phase in Phase)
        return tuple(session for session in found if session is not None)

    def has_student(self, student_id: str) -> bool:
        """Indique si l'étudiant possède au moins une séance."""
        return any((student_id, phase) in self._sessions for phase in Phase)

    def to_solution(self) -> Solution:
        """Construit une :class:`~core.solution.Solution` triée de façon déterministe."""
        return Solution(
            instance_id=self._instance.instance_id,
            sessions=sorted(self._sessions.values(), key=lambda session: session.sort_key),
        )

    # ==================================================================
    # Occupations et capacités
    # ==================================================================
    def teacher_free(self, teacher_id: str, day: int, slot: int) -> bool:
        """Indique si l'enseignant n'a aucune séance à ``(day, slot)``."""
        return (teacher_id, day, slot) not in self._teacher_busy

    def student_free(self, student_id: str, day: int, slot: int) -> bool:
        """Indique si l'étudiant n'a aucune séance à ``(day, slot)``."""
        return (student_id, day, slot) not in self._student_busy

    def room_free(self, room_id: str, day: int, slot: int) -> bool:
        """Indique si la salle n'accueille aucune finale à ``(day, slot)``."""
        return (room_id, day, slot) not in self._room_busy

    def teacher_day_count(self, teacher_id: str, day: int) -> int:
        """Nombre de séances de l'enseignant un jour donné (toutes phases)."""
        return self._teacher_day_count.get((teacher_id, day), 0)

    def teacher_has_capacity(self, teacher_id: str, day: int) -> bool:
        """Indique si l'enseignant peut accepter une séance de plus ce jour-là."""
        return self.teacher_day_count(teacher_id, day) < self._teacher_cap[teacher_id]

    def room_has_capacity(self, room_id: str, day: int) -> bool:
        """Indique si la salle peut accueillir une finale de plus ce jour-là."""
        return self._room_day_count.get((room_id, day), 0) < self._room_cap[room_id]

    def teacher_day_slots(self, teacher_id: str, day: int) -> Collection[int]:
        """Créneaux occupés par l'enseignant un jour donné (lecture seule)."""
        return self._teacher_slots.get((teacher_id, day), _EMPTY_SLOTS)

    def load(self, teacher_id: str) -> int:
        """Nombre total de séances de l'enseignant (charge)."""
        return self._load[teacher_id]

    def pair_used(self, pair: Pair) -> bool:
        """Indique si le binôme est déjà utilisé par une pré-soutenance."""
        return pair in self._pair_usage

    def free_rooms(self, day: int, slot: int) -> tuple[str, ...]:
        """Retourne les salles utilisables à ``(day, slot)``.

        Une salle est utilisable si elle est disponible, libre à ce créneau et si
        son plafond journalier n'est pas atteint. L'ordre est celui de l'instance.
        """
        return tuple(
            room_id
            for room_id in self._room_ids
            if self._availability.room_available(room_id, day, slot)
            and (room_id, day, slot) not in self._room_busy
            and self._room_day_count.get((room_id, day), 0) < self._room_cap[room_id]
        )

    # ==================================================================
    # Regroupement par encadrant (critère supervisor_group_breaks)
    # ==================================================================
    def online_group_count(self, supervisor_id: str) -> int:
        """Nombre de groupes de pré-soutenances en ligne d'un encadrant.

        Un groupe est une suite maximale de créneaux **distincts** consécutifs
        d'un même jour, occupés par les étudiants de l'encadrant.
        """
        positions = self._sup_online.get(supervisor_id)
        if not positions:
            return 0
        return sum(1 for day, slot in positions if (day, slot - 1) not in positions)

    def online_group_delta(self, supervisor_id: str, day: int, slot: int) -> int:
        """Variation du nombre de groupes en ligne si l'on occupe ``(day, slot)``.

        Retourne +1 (nouveau groupe isolé), 0 (prolonge un groupe, ou créneau
        déjà occupé) ou -1 (fusionne deux groupes).
        """
        positions = self._sup_online.get(supervisor_id)
        if not positions:
            return 1
        if (day, slot) in positions:
            return 0
        return 1 - int((day, slot - 1) in positions) - int((day, slot + 1) in positions)

    def final_group_count(self, supervisor_id: str) -> int:
        """Nombre de groupes de finales d'un encadrant.

        Un groupe est une suite de séances de même encadrant, sur des créneaux
        consécutifs d'une même salle et d'un même jour.
        """
        positions = self._sup_final.get(supervisor_id)
        if not positions:
            return 0
        return sum(1 for day, room, slot in positions if (day, room, slot - 1) not in positions)

    def final_group_delta(self, supervisor_id: str, day: int, room_id: str, slot: int) -> int:
        """Variation du nombre de groupes de finales si l'on place ``(day, room_id, slot)``.

        Retourne +1 (nouveau groupe), 0 (prolonge un groupe) ou -1 (fusionne deux groupes).
        """
        positions = self._sup_final.get(supervisor_id)
        if not positions:
            return 1
        return (
            1
            - int((day, room_id, slot - 1) in positions)
            - int((day, room_id, slot + 1) in positions)
        )


class SessionBuilder:
    """Construit des séances faisables à partir du contexte de pré-traitement.

    Le constructeur n'écrit jamais dans l'état : il **retourne** des séances que
    l'appelant ajoute à :class:`ScheduleState`. Il s'appuie sur :

    * ``AvailabilityMatrix`` : créneaux autorisés et disponibilités ;
    * ``JuryCandidates`` : binômes possibles par étudiant et créneaux communs ;
    * ``DomainFilters`` : vérification en temps constant des rôles et domaines.

    Les créneaux communs de chaque (étudiant, binôme, phase) sont mémorisés pour
    éviter tout recalcul (par exemple lors des tours de réparation).

    Args:
        context: Contexte de pré-traitement de l'instance.
        config: Configuration du solveur.
        rng: Générateur pseudo-aléatoire (créé à partir de ``config.random_seed``
            s'il est absent).
    """

    def __init__(
        self,
        context: PreprocessingContext,
        config: GreedyConfig,
        rng: Random | None = None,
    ) -> None:
        self._context = context
        self._config = config
        self._rng = rng if rng is not None else Random(config.random_seed)
        self._slots_cache: dict[tuple[str, str, str, Phase], tuple[TimeSlot, ...]] = {}
        self._difficulty_cache: dict[tuple[str, Phase | None], tuple[int, int, str]] = {}

    # ------------------------------------------------------------------
    # Accès
    # ------------------------------------------------------------------
    @property
    def instance(self) -> Instance:
        """Instance du problème."""
        return self._context.instance

    @property
    def availability(self) -> AvailabilityMatrix:
        """Matrice de disponibilités."""
        return self._context.availability

    @property
    def jury(self):  # type: ignore[no-untyped-def]
        """Candidats de jury (:class:`preprocessing.JuryCandidates`)."""
        return self._context.jury

    @property
    def domains(self):  # type: ignore[no-untyped-def]
        """Filtres de domaine (:class:`preprocessing.DomainFilters`)."""
        return self._context.domains

    @property
    def config(self) -> GreedyConfig:
        """Configuration du solveur."""
        return self._config

    @property
    def rng(self) -> Random:
        """Générateur pseudo-aléatoire partagé."""
        return self._rng

    # ==================================================================
    # Ordre MRV
    # ==================================================================
    def difficulty(self, student_id: str, phase: Phase | None = None) -> tuple[int, int, str]:
        """Calcule la clé de difficulté MRV d'un étudiant (plus petit = plus difficile).

        La clé est ``(nombre minimal de créneaux candidats, nombre de binômes
        possibles, identifiant)``. Le nombre de créneaux candidats est celui de
        :meth:`preprocessing.AvailabilityMatrix.candidate_slots`, minimum sur les
        phases que l'étudiant doit passer (ou sur ``phase`` si indiquée).

        Args:
            student_id: Identifiant de l'étudiant.
            phase: Phase à considérer seule (facultatif).

        Returns:
            La clé de difficulté (comparable lexicographiquement).
        """
        key = (student_id, phase)
        cached = self._difficulty_cache.get(key)
        if cached is None:
            student = self.instance.student(student_id)
            phases = (phase,) if phase is not None else student.required_phases()
            slot_count = min(len(self.availability.candidate_slots(student_id, ph)) for ph in phases)
            cached = (slot_count, self.jury.num_pairs(student_id), student_id)
            self._difficulty_cache[key] = cached
        return cached

    def mrv_order(self, student_ids: Iterable[str], phase: Phase | None = None) -> list[str]:
        """Ordonne des étudiants du plus contraint au moins contraint (MRV).

        Si ``config.use_mrv_ordering`` est faux, l'ordre d'origine est conservé.

        Args:
            student_ids: Identifiants à ordonner.
            phase: Phase à considérer seule pour la difficulté (facultatif).

        Returns:
            Une nouvelle liste ordonnée.
        """
        ids = list(student_ids)
        if not self._config.use_mrv_ordering:
            return ids
        return sorted(ids, key=lambda sid: self.difficulty(sid, phase))

    # ==================================================================
    # Créneaux faisables
    # ==================================================================
    def _pair_slots(self, student: Student, pair: Pair, phase: Phase) -> tuple[TimeSlot, ...]:
        """Créneaux communs statiques (disponibilités et période), avec mémorisation."""
        key = (student.id, pair[0], pair[1], phase)
        cached = self._slots_cache.get(key)
        if cached is None:
            cached = self.jury.pair_slots(student.id, pair[0], pair[1], phase)
            self._slots_cache[key] = cached
        return cached

    def _feasible_predefence_slots(
        self, state: ScheduleState, student: Student, pair: Pair
    ) -> list[TimeSlot]:
        """Créneaux de pré-soutenance faisables pour ce binôme dans l'état courant."""
        president, examiner = pair
        feasible: list[TimeSlot] = []
        for day, slot in self._pair_slots(student, pair, Phase.PREDEFENCE):
            if not state.student_free(student.id, day, slot):
                continue
            if not (state.teacher_free(president, day, slot) and state.teacher_free(examiner, day, slot)):
                continue
            if not (state.teacher_has_capacity(president, day) and state.teacher_has_capacity(examiner, day)):
                continue
            feasible.append((day, slot))
        return feasible

    def _feasible_final_slots(
        self, state: ScheduleState, student: Student, pair: Pair
    ) -> list[TimeSlot]:
        """Créneaux de finale faisables pour ce binôme dans l'état courant.

        Exige : étudiant, président, examinateur et encadrant disponibles, libres
        et sous leur plafond journalier, et au moins une salle utilisable. Un
        binôme contenant l'encadrant est refusé (trois membres distincts).
        """
        supervisor = student.supervisor_id
        if supervisor in pair:
            return []
        teachers = (pair[0], pair[1], supervisor)
        feasible: list[TimeSlot] = []
        for day, slot in self._pair_slots(student, pair, Phase.FINAL):
            if not state.student_free(student.id, day, slot):
                continue
            if not all(
                state.teacher_free(teacher, day, slot) and state.teacher_has_capacity(teacher, day)
                for teacher in teachers
            ):
                continue
            if not state.free_rooms(day, slot):
                continue
            feasible.append((day, slot))
        return feasible

    # ==================================================================
    # Meilleure séance pour un binôme donné
    # ==================================================================
    def _best_predefence(self, state: ScheduleState, student: Student, pair: Pair) -> Session | None:
        """Retourne la meilleure pré-soutenance pour ce binôme, ou ``None``."""
        slots = self._feasible_predefence_slots(state, student, pair)
        if not slots:
            return None
        ranked = rank_time_slots(state, student, Phase.PREDEFENCE, pair, slots, self._config, self._rng)
        day, slot = ranked[0]
        return Session(
            student_id=student.id,
            phase=Phase.PREDEFENCE,
            day=day,
            slot=slot,
            room_id=None,
            president_id=pair[0],
            examiner_id=pair[1],
        )

    def _best_final(self, state: ScheduleState, student: Student, pair: Pair) -> Session | None:
        """Retourne la meilleure finale (créneau et salle) pour ce binôme, ou ``None``."""
        slots = self._feasible_final_slots(state, student, pair)
        if not slots:
            return None
        for day, slot in rank_time_slots(state, student, Phase.FINAL, pair, slots, self._config, self._rng):
            rooms = state.free_rooms(day, slot)
            if not rooms:
                continue
            room_id = rank_rooms(state, student, day, slot, rooms, self._config, self._rng)[0]
            return Session(
                student_id=student.id,
                phase=Phase.FINAL,
                day=day,
                slot=slot,
                room_id=room_id,
                president_id=pair[0],
                examiner_id=pair[1],
            )
        return None

    # ==================================================================
    # API de construction
    # ==================================================================
    def build_predefence(
        self, state: ScheduleState, student_id: str, *, pair: Pair | None = None
    ) -> Session | None:
        """Construit la pré-soutenance en ligne d'un étudiant.

        Les binômes possibles sont classés (:func:`rank_jury_pairs`). Pour un
        étudiant admissible, un binôme n'est retenu que si une finale est encore
        faisable avec lui (anticipation de la continuité du jury). Le premier
        binôme admettant au moins un créneau faisable est utilisé, avec le
        meilleur créneau selon :func:`rank_time_slots`.

        Args:
            state: État d'occupation courant (non modifié).
            student_id: Identifiant de l'étudiant.
            pair: Binôme imposé (facultatif). Ignoré s'il n'est pas un binôme
                possible de l'étudiant.

        Returns:
            La séance construite (à ajouter à l'état par l'appelant), ou
            ``None`` si aucun placement n'est possible.
        """
        student = self.instance.student(student_id)
        if pair is not None:
            if pair not in self.jury.pair_index_for(student_id):
                return None
            candidates: tuple[Pair, ...] = (pair,)
        else:
            candidates = self.jury.pairs_for(student_id)
        for candidate in rank_jury_pairs(state, candidates, self._config, self._rng):
            if student.eligible_final and not self._feasible_final_slots(state, student, candidate):
                continue
            session = self._best_predefence(state, student, candidate)
            if session is not None:
                return session
        return None

    def build_final(
        self, state: ScheduleState, student_id: str, *, pair: Pair | None = None
    ) -> Session | None:
        """Construit la finale d'un étudiant admissible, avec son binôme existant.

        Sauf si ``pair`` est imposé, le binôme est celui de la pré-soutenance
        déjà présente dans l'état (continuité du jury). La salle est choisie
        parmi les salles utilisables (:func:`rank_rooms`).

        Args:
            state: État d'occupation courant (non modifié).
            student_id: Identifiant de l'étudiant.
            pair: Binôme imposé (facultatif).

        Returns:
            La séance construite, ou ``None`` si l'étudiant n'est pas admissible,
            n'a pas de pré-soutenance dans l'état (et aucun binôme imposé), ou
            si aucun placement n'est possible.
        """
        student = self.instance.student(student_id)
        if not student.eligible_final:
            return None
        if pair is None:
            predefence = state.session_of(student_id, Phase.PREDEFENCE)
            if predefence is None:
                return None
            pair = predefence.jury_pair
        return self._best_final(state, student, pair)

    def build_student(self, state: ScheduleState, student_id: str) -> tuple[Session, ...] | None:
        """Planifie un étudiant en entier : binôme, pré-soutenance et finale.

        Pour chaque binôme classé, la pré-soutenance puis (si l'étudiant est
        admissible) la finale sont cherchées. La première combinaison complète
        est retournée. Grâce à l'indépendance des phases (voir la documentation
        du module), aucune séance n'a besoin d'être ajoutée à l'état entre les
        deux recherches. Cette méthode sert à la réparation.

        Args:
            state: État d'occupation courant (non modifié). L'étudiant ne doit
                avoir aucune séance dans l'état.
            student_id: Identifiant de l'étudiant.

        Returns:
            Les séances à ajouter (une ou deux), ou ``None`` si aucun binôme ne
            permet un placement complet.
        """
        student = self.instance.student(student_id)
        for pair in rank_jury_pairs(state, self.jury.pairs_for(student_id), self._config, self._rng):
            predefence = self._best_predefence(state, student, pair)
            if predefence is None:
                continue
            if not student.eligible_final:
                return (predefence,)
            final = self._best_final(state, student, pair)
            if final is None:
                continue
            return (predefence, final)
        return None

    # ==================================================================
    # Contrôle complet d'une séance existante
    # ==================================================================
    def check_session(self, state: ScheduleState, session: Session) -> list[str]:
        """Liste les violations de contrainte dure d'une séance vis-à-vis de l'état.

        Utilisée par la réparation pour décider si une séance existante peut être
        conservée. La séance est comparée aux séances **déjà présentes dans
        l'état** (occupations, plafonds journaliers, salle) et aux données de
        l'instance (disponibilités, périodes, rôles, domaine, distinction des
        personnes, cohérence phase/salle). La continuité du binôme entre les
        phases est contrôlée par l'appelant.

        Args:
            state: État d'occupation courant (non modifié).
            session: Séance à contrôler.

        Returns:
            Les violations (liste vide si la séance est faisable).
        """
        instance, avail = self.instance, self.availability
        if not instance.has_student(session.student_id):
            return [f"étudiant inconnu {session.student_id!r}"]
        student = instance.student(session.student_id)
        phase, day, slot = session.phase, session.day, session.slot
        president, examiner = session.president_id, session.examiner_id
        errors: list[str] = []

        if not student.requires_phase(phase):
            errors.append(f"phase {phase.value!r} non requise pour cet étudiant")
        if state.session_of(student.id, phase) is not None:
            errors.append("séance déjà présente pour cette phase")
        if not avail.is_valid_time_slot(day, slot):
            errors.append(f"créneau hors horizon (jour {day}, créneau {slot})")
            return errors
        if not avail.is_slot_allowed(phase, day, slot):
            errors.append(f"jour {day} hors de la période de la phase {phase.value!r}")

        unknown = [tid for tid in (president, examiner) if not instance.has_teacher(tid)]
        if unknown:
            errors.append(f"enseignant(s) inconnu(s) : {unknown}")
            return errors
        if president == examiner:
            errors.append("président et examinateur identiques")
        if not self.domains.can_preside(president):
            errors.append(f"{president!r} n'a pas le rôle de président")
        if not instance.teacher(examiner).can_serve_as(Role.EXAMINER):
            errors.append(f"{examiner!r} n'a pas le rôle d'examinateur")
        if not self.domains.covers(examiner, student.domain):
            errors.append(f"{examiner!r} ne couvre pas le domaine {student.domain!r}")

        supervisor = student.supervisor_id
        attendees = [president, examiner]
        if phase is Phase.FINAL:
            if supervisor in (president, examiner):
                errors.append("l'encadrant ne peut pas être président ou examinateur de la finale")
            attendees.append(supervisor)
            room_id = session.room_id
            if not isinstance(room_id, str) or not instance.has_room(room_id):
                errors.append(f"salle absente ou inconnue ({room_id!r})")
            else:
                if not avail.room_available(room_id, day, slot):
                    errors.append(f"salle {room_id!r} indisponible")
                if not state.room_free(room_id, day, slot):
                    errors.append(f"salle {room_id!r} déjà occupée à ce créneau")
                if not state.room_has_capacity(room_id, day):
                    errors.append(f"plafond journalier de la salle {room_id!r} atteint")
        elif session.room_id is not None:
            errors.append("une pré-soutenance en ligne ne doit pas avoir de salle")

        for teacher_id in dict.fromkeys(attendees):
            if not avail.teacher_available(teacher_id, day, slot):
                errors.append(f"enseignant {teacher_id!r} indisponible")
            if not state.teacher_free(teacher_id, day, slot):
                errors.append(f"enseignant {teacher_id!r} déjà occupé à ce créneau")
            if not state.teacher_has_capacity(teacher_id, day):
                errors.append(f"plafond journalier de l'enseignant {teacher_id!r} atteint")
        if not avail.student_available(student.id, day, slot):
            errors.append("étudiant indisponible")
        if not state.student_free(student.id, day, slot):
            errors.append("étudiant déjà occupé à ce créneau")
        return errors