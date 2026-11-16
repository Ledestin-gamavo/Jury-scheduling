"""Modèle métier d'une solution (planning complet)."""

from __future__ import annotations
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from .enums import SCHEMA_VERSION, Phase
from .session import Session

__all__ = ["Solution"]

@dataclass
class Solution:
    """Planning : ensemble de séances rattaché à une instance.

    Contrairement aux entités de l'instance, une solution est un conteneur
    **mutable**, afin que les solveurs (glouton, CP-SAT, hybride) puissent la
    construire ou la raffiner. Les :class:`Session` qu'elle contient restent
    immuables : une copie superficielle (:meth:`copy`) suffit donc à dupliquer
    un planning.

    Une solution peut être incomplète ou invalide ; elle ne fait aucun contrôle
    de faisabilité. Elle ne calcule aucune métrique. Les doublons de clé
    ``(student_id, phase)`` sont tolérés ici et détectables via
    :meth:`duplicate_keys`.

    Attributes:
        instance_id: Identifiant de l'instance résolue.
        sessions: Séances du planning, dans l'ordre d'insertion.
        schema_version: Version du contrat de données.
    """

    instance_id: str
    sessions: list[Session] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    # Protocole conteneur
    def __len__(self) -> int:
        return len(self.sessions)

    def __iter__(self) -> Iterator[Session]:
        return iter(self.sessions)

    @property
    def is_empty(self) -> bool:
        """Vrai si la solution ne contient aucune séance."""
        return not self.sessions

    # Modification
    def add(self, session: Session) -> None:
        """Ajoute une séance à la fin du planning."""
        self.sessions.append(session)

    def extend(self, sessions: Iterable[Session]) -> None:
        """Ajoute plusieurs séances à la fin du planning."""
        self.sessions.extend(sessions)

    def remove(self, student_id: str, phase: Phase) -> int:
        """Retire toutes les séances d'un étudiant pour une phase donnée.

        Args:
            student_id: Identifiant de l'étudiant.
            phase: Phase concernée.

        Returns:
            Nombre de séances retirées.
        """
        kept = [s for s in self.sessions if s.key != (student_id, phase)]
        removed = len(self.sessions) - len(kept)
        self.sessions[:] = kept
        return removed

    def clear(self) -> None:
        """Supprime toutes les séances."""
        self.sessions.clear()

    def copy(self) -> Solution:
        """Retourne une copie indépendante (liste dupliquée, séances partagées)."""
        return Solution(
            instance_id=self.instance_id,
            sessions=list(self.sessions),
            schema_version=self.schema_version,
        )

    # Consultation
    def get(self, student_id: str, phase: Phase) -> Session | None:
        """Retourne la première séance d'un étudiant pour une phase, ou ``None``."""
        for session in self.sessions:
            if session.key == (student_id, phase):
                return session
        return None

    def has_session(self, student_id: str, phase: Phase) -> bool:
        """Indique si l'étudiant a au moins une séance pour cette phase."""
        return self.get(student_id, phase) is not None

    def by_phase(self, phase: Phase) -> list[Session]:
        """Retourne les séances d'une phase."""
        return [s for s in self.sessions if s.phase is phase]

    def by_student(self, student_id: str) -> list[Session]:
        """Retourne les séances d'un étudiant (toutes phases)."""
        return [s for s in self.sessions if s.student_id == student_id]

    def by_day(self, day: int) -> list[Session]:
        """Retourne les séances d'un jour donné."""
        return [s for s in self.sessions if s.day == day]

    def by_teacher(self, teacher_id: str) -> list[Session]:
        """Retourne les séances où l'enseignant est président ou examinateur.

        Les séances finales supervisées par cet enseignant (rapporteur) ne sont
        pas incluses ici : elles nécessitent l'instance (voir
        :meth:`core.instance.Instance.attending_teacher_ids`).
        """
        return [
            s
            for s in self.sessions
            if teacher_id in (s.president_id, s.examiner_id)
        ]

    def by_room(self, room_id: str) -> list[Session]:
        """Retourne les finales affectées à une salle."""
        return [s for s in self.sessions if s.room_id == room_id]

    def by_key(self) -> dict[tuple[str, Phase], Session]:
        """Index ``(student_id, phase) -> séance``.

        En cas de doublon, la dernière séance rencontrée l'emporte ; utiliser
        :meth:`duplicate_keys` pour détecter ce cas.
        """
        return {s.key: s for s in self.sessions}

    def student_ids(self) -> frozenset[str]:
        """Ensemble des étudiants ayant au moins une séance."""
        return frozenset(s.student_id for s in self.sessions)

    def duplicate_keys(self) -> list[tuple[str, Phase]]:
        """Retourne les clés ``(student_id, phase)`` présentes plusieurs fois."""
        counts = Counter(s.key for s in self.sessions)
        return sorted(
            (key for key, n in counts.items() if n > 1),
            key=lambda key: (key[0], key[1].value),
        )

    def sorted_sessions(self) -> list[Session]:
        """Retourne les séances triées de façon déterministe (jour, créneau…)."""
        return sorted(self.sessions, key=lambda s: s.sort_key)