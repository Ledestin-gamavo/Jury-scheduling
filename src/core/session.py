"""Modèle métier d'une séance de soutenance."""

from __future__ import annotations
from dataclasses import dataclass, replace
from .enums import Phase

__all__ = ["Session"]


@dataclass(frozen=True)
class Session:
    """Séance de soutenance d'un étudiant pour une phase donnée.

    Une séance occupe exactement un créneau : l'intervalle ``[slot, slot + 1)``.
    L'objet est immuable ; pour « déplacer » une séance, utiliser
    :meth:`moved_to`, :meth:`with_jury` ou :meth:`with_room`, qui retournent une
    copie modifiée.

    Cette classe **ne valide pas** la cohérence métier (salle nulle en
    pré-soutenance, jury distinct, disponibilités, etc.) : elle doit pouvoir
    représenter aussi des plannings invalides afin de les diagnostiquer. La
    validation relève du futur module ``validation``. Seule la cohérence
    ``phase``/``room_id`` est exposée par :attr:`has_consistent_room`.

    Attributes:
        student_id: Identifiant de l'étudiant.
        phase: Phase de la séance.
        day: Indice du jour (à partir de zéro).
        slot: Indice du créneau dans le jour (à partir de zéro).
        room_id: ``None`` en pré-soutenance ; identifiant de salle en finale.
        president_id: Identifiant de l'enseignant président.
        examiner_id: Identifiant de l'enseignant examinateur.
    """

    student_id: str
    phase: Phase
    day: int
    slot: int
    room_id: str | None
    president_id: str
    examiner_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", Phase(self.phase))

    # Identification et regroupement
    @property
    def key(self) -> tuple[str, Phase]:
        """Clé fonctionnelle ``(student_id, phase)`` : unique dans une solution valide."""
        return (self.student_id, self.phase)

    @property
    def time_slot(self) -> tuple[int, int]:
        """Couple ``(day, slot)`` occupé par la séance."""
        return (self.day, self.slot)

    @property
    def jury_pair(self) -> tuple[str, str]:
        """Couple ordonné ``(président, examinateur)``."""
        return (self.president_id, self.examiner_id)

    @property
    def sort_key(self) -> tuple[int, int, str, str, str]:
        """Clé de tri déterministe : jour, créneau, salle, étudiant, phase."""
        return (self.day, self.slot, self.room_id or "", self.student_id, self.phase.value)

    # Prédicats
    @property
    def is_online(self) -> bool:
        """Vrai si la séance est une pré-soutenance en ligne."""
        return self.phase.is_online

    @property
    def is_final(self) -> bool:
        """Vrai si la séance est une soutenance finale."""
        return self.phase is Phase.FINAL

    @property
    def has_consistent_room(self) -> bool:
        """Vrai si ``room_id`` respecte la phase.

        ``None`` est requis en pré-soutenance ; un identifiant non vide en finale.
        """
        if self.phase.requires_room:
            return isinstance(self.room_id, str) and bool(self.room_id.strip())
        return self.room_id is None

    # Copies modifiées
    def moved_to(self, day: int, slot: int) -> Session:
        """Retourne une copie placée au jour et créneau indiqués."""
        return replace(self, day=day, slot=slot)

    def with_jury(self, president_id: str, examiner_id: str) -> Session:
        """Retourne une copie avec un autre binôme président/examinateur."""
        return replace(self, president_id=president_id, examiner_id=examiner_id)

    def with_room(self, room_id: str | None) -> Session:
        """Retourne une copie affectée à une autre salle (ou sans salle)."""
        return replace(self, room_id=room_id)