"""Mouvements réversibles et opérateur d'application.

Ce module définit :

* :class:`MoveType` : les cinq voisinages ;
* :class:`SessionChange` : le remplacement d'une séance par une autre ;
* :class:`Move` : un mouvement, ensemble de remplacements appliqués ensemble ;
* :class:`MoveOperator` : application et annulation d'un mouvement sur une
  solution ou sur l'état d'occupation, et test de faisabilité exact.

Réversibilité. Un mouvement est une liste de couples ``(ancienne séance,
nouvelle séance)``. Il se défait en échangeant les deux membres de chaque couple
(:meth:`Move.inverse`) : ``undo(move)`` est ``apply(move.inverse())``. Appliquer
puis annuler un mouvement restitue exactement la solution d'origine, **y compris
l'ordre des séances** (remplacement à la même position).

Faisabilité exacte et incrémentale. :meth:`MoveOperator.is_feasible` retire les
anciennes séances de l'état d'occupation, contrôle chaque nouvelle séance avec
:meth:`solvers.greedy.session_builder.SessionBuilder.check_session` (les mêmes
règles que celles du ``GreedySolver``), puis restaure l'état. Aucune règle
métier n'est dupliquée. Le coût est proportionnel au nombre de séances du
mouvement, et non à la taille du planning. La validation complète par
``SolutionValidator`` est faite ensuite par le solveur, uniquement sur les
mouvements acceptés.

Continuité du jury. Aucun mouvement ne sépare le binôme de la pré-soutenance de
celui de la finale : seul le voisinage ``CHANGE_JURY`` modifie un binôme, et il
modifie **toutes** les séances de l'étudiant ensemble.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.session import Session
from core.solution import Solution
from solvers.greedy import ScheduleState, SessionBuilder

__all__ = ["MoveType", "SessionChange", "Move", "MoveOperator"]


class MoveType(str, Enum):
    """Les cinq voisinages de la recherche locale, avec leur justification.

    Attributes:
        CHANGE_SLOT: Voisinage 1. Déplace **une** séance vers un autre créneau
            (jour et créneau) où tous les participants sont disponibles ; pour
            une finale, la salle est conservée si possible. Justification : c'est
            le mouvement le plus élémentaire. Il agit sur ``teacher_presence_days``
            (regrouper les séances d'un enseignant sur moins de jours) et sur
            ``teacher_idle_slots`` (combler les trous).
        CHANGE_ROOM: Voisinage 2. Change la salle d'**une finale**, sans changer
            l'horaire. Justification : seul le critère ``supervisor_group_breaks``
            dépend de la salle (adjacence dans une même salle). Ce mouvement très
            peu coûteux sépare ce critère des autres.
        CHANGE_JURY: Voisinage 3. Remplace le binôme (président, examinateur) d'un
            étudiant, **pour toutes ses séances à la fois** (continuité du jury).
            Justification : c'est le seul levier sur ``distinct_jury_pairs`` et un
            levier fort sur ``teacher_load_range``, sur la présence et sur les
            créneaux creux. Les binômes déjà utilisés par d'autres étudiants sont
            essayés en priorité pour réduire le nombre de binômes distincts.
        SWAP_SESSIONS: Voisinage 4. Échange les placements (jour, créneau, salle)
            de deux séances **de la même phase**, chaque jury restant avec son
            étudiant. Justification : quand deux séances occupent chacune le
            créneau désiré par l'autre, aucun déplacement isolé n'est faisable,
            alors que l'échange l'est. Les échanges entre phases sont impossibles
            car leurs périodes sont disjointes.
        MOVE_SUPERVISOR_BLOCK: Voisinage 5. Déplace un **bloc** de séances d'un
            encadrant (suite maximale de créneaux consécutifs, au sens de
            ``supervisor_group_breaks``) pour le placer juste avant ou juste après
            un autre bloc du même encadrant, dans le même jour (et la même salle
            en finale). Justification : un déplacement séance par séance ne peut
            pas fusionner deux blocs sans passer par des étapes intermédiaires
            qui dégradent le score, ce que le *hill climbing* refuse. Le
            déplacement du bloc entier réalise la fusion en un seul pas.
    """

    CHANGE_SLOT = "change_slot"
    CHANGE_ROOM = "change_room"
    CHANGE_JURY = "change_jury"
    SWAP_SESSIONS = "swap_sessions"
    MOVE_SUPERVISOR_BLOCK = "move_supervisor_block"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SessionChange:
    """Remplacement d'une séance par une autre pour le même étudiant et la même phase.

    Attributes:
        old: Séance avant le mouvement.
        new: Séance après le mouvement.

    Raises:
        ValueError: Si ``old`` et ``new`` n'ont pas la même clé ``(étudiant, phase)``.
    """

    old: Session
    new: Session

    def __post_init__(self) -> None:
        if self.old.key != self.new.key:
            raise ValueError(
                f"Un changement doit garder l'étudiant et la phase : {self.old.key} != {self.new.key}"
            )

    @property
    def is_noop(self) -> bool:
        """Vrai si la nouvelle séance est identique à l'ancienne."""
        return self.old == self.new

    def inverse(self) -> SessionChange:
        """Retourne le changement inverse."""
        return SessionChange(old=self.new, new=self.old)

    def diff(self) -> str:
        """Décrit les champs modifiés, par exemple ``jour 2->3, créneau 1->4``."""
        old, new = self.old, self.new
        parts: list[str] = []
        if old.day != new.day:
            parts.append(f"jour {old.day}->{new.day}")
        if old.slot != new.slot:
            parts.append(f"créneau {old.slot}->{new.slot}")
        if old.room_id != new.room_id:
            parts.append(f"salle {old.room_id}->{new.room_id}")
        if old.jury_pair != new.jury_pair:
            parts.append(
                f"jury {old.president_id}/{old.examiner_id}->{new.president_id}/{new.examiner_id}"
            )
        return ", ".join(parts) if parts else "aucun changement"


@dataclass(frozen=True)
class Move:
    """Un mouvement : remplacements de séances appliqués **ensemble**.

    Attributes:
        type: Voisinage dont le mouvement est issu.
        changes: Remplacements, un par séance modifiée (clés distinctes).

    Raises:
        ValueError: Si la liste est vide, si deux changements portent sur la même
            séance, ou si tous les changements sont neutres.
    """

    type: MoveType
    changes: tuple[SessionChange, ...]

    def __post_init__(self) -> None:
        changes = tuple(self.changes)
        object.__setattr__(self, "type", MoveType(self.type))
        object.__setattr__(self, "changes", changes)
        if not changes:
            raise ValueError("Un mouvement doit contenir au moins un changement")
        keys = [change.old.key for change in changes]
        if len(set(keys)) != len(keys):
            raise ValueError("Un mouvement ne peut pas modifier deux fois la même séance")
        if all(change.is_noop for change in changes):
            raise ValueError("Un mouvement neutre n'a aucun intérêt")

    @classmethod
    def single(cls, move_type: MoveType, old: Session, new: Session) -> Move:
        """Construit un mouvement à un seul changement."""
        return cls(move_type, (SessionChange(old, new),))

    @property
    def num_sessions(self) -> int:
        """Nombre de séances modifiées."""
        return len(self.changes)

    @property
    def student_ids(self) -> tuple[str, ...]:
        """Étudiants concernés, sans doublon."""
        return tuple(dict.fromkeys(change.old.student_id for change in self.changes))

    def inverse(self) -> Move:
        """Retourne le mouvement qui annule celui-ci."""
        return Move(self.type, tuple(change.inverse() for change in self.changes))

    def describe(self) -> str:
        """Retourne une description lisible du mouvement."""
        details = "; ".join(
            f"{c.old.student_id}/{c.old.phase.value} ({c.diff()})" for c in self.changes
        )
        return f"{self.type.value} : {details}"


class MoveOperator:
    """Applique, annule et teste des mouvements.

    L'opérateur agit sur deux représentations qui doivent rester synchronisées
    par l'appelant : la :class:`~core.solution.Solution` de travail (liste de
    séances) et le :class:`~solvers.greedy.session_builder.ScheduleState`
    (occupations et compteurs).

    Args:
        builder: Constructeur de séances, utilisé uniquement pour son contrôle
            de faisabilité :meth:`SessionBuilder.check_session`.
    """

    def __init__(self, builder: SessionBuilder) -> None:
        self._builder = builder

    # Solution
    @staticmethod
    def _index_of(solution: Solution, session: Session) -> int:
        """Retourne la position d'une séance dans la solution.

        Raises:
            KeyError: Si aucune séance n'a cette clé.
            ValueError: Si la séance trouvée diffère de celle attendue.
        """
        for index, candidate in enumerate(solution.sessions):
            if candidate.key == session.key:
                if candidate != session:
                    raise ValueError(
                        f"La séance de {session.student_id!r}/{session.phase.value} a changé "
                        "depuis la génération du mouvement"
                    )
                return index
        raise KeyError(f"Aucune séance pour {session.student_id!r}/{session.phase.value}")

    def apply(self, move: Move, solution: Solution) -> None:
        """Applique un mouvement à la solution, en place et de façon atomique.

        Chaque ancienne séance est remplacée **à la même position** par la
        nouvelle. Si une ancienne séance est absente ou a changé, aucune
        modification n'est faite.

        Args:
            move: Mouvement à appliquer.
            solution: Solution modifiée.

        Raises:
            KeyError: Si une séance du mouvement est absente de la solution.
            ValueError: Si une séance de la solution diffère de ``change.old``.
        """
        indices = [self._index_of(solution, change.old) for change in move.changes]
        for index, change in zip(indices, move.changes):
            solution.sessions[index] = change.new

    def undo(self, move: Move, solution: Solution) -> None:
        """Annule un mouvement précédemment appliqué à la solution.

        Args:
            move: Mouvement à annuler.
            solution: Solution modifiée.
        """
        self.apply(move.inverse(), solution)

    # État d'occupation
    @staticmethod
    def apply_to_state(move: Move, state: ScheduleState) -> None:
        """Reporte un mouvement **faisable** dans l'état d'occupation.

        Args:
            move: Mouvement à reporter (faisabilité déjà vérifiée).
            state: État d'occupation modifié.
        """
        for change in move.changes:
            state.remove(change.old)
        for change in move.changes:
            state.add(change.new)

    def undo_on_state(self, move: Move, state: ScheduleState) -> None:
        """Annule le report d'un mouvement dans l'état d'occupation.

        Args:
            move: Mouvement à annuler.
            state: État d'occupation modifié.
        """
        self.apply_to_state(move.inverse(), state)

    def is_feasible(self, move: Move, state: ScheduleState) -> bool:
        """Indique si le mouvement respecte toutes les contraintes dures.

        Procédure : les anciennes séances sont retirées de l'état ; chaque nouvelle
        séance est contrôlée par :meth:`SessionBuilder.check_session` (disponibilités,
        chevauchements, plafonds journaliers, salles, rôles, domaine, période),
        puis ajoutée pour que les séances suivantes du même mouvement tiennent
        compte d'elle. L'état est **toujours restauré** avant le retour.

        La continuité du binôme est garantie par construction des mouvements.

        Args:
            move: Mouvement à tester.
            state: État d'occupation (restauré à l'identique à la sortie).

        Returns:
            ``True`` si le mouvement est faisable.
        """
        removed: list[Session] = []
        added: list[Session] = []
        try:
            for change in move.changes:
                state.remove(change.old)
                removed.append(change.old)
            for change in move.changes:
                if self._builder.check_session(state, change.new):
                    return False
                state.add(change.new)
                added.append(change.new)
            return True
        finally:
            for session in reversed(added):
                state.remove(session)
            for session in reversed(removed):
                state.add(session)