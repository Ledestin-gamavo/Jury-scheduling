"""Modèle métier d'une salle physique."""

from __future__ import annotations
from dataclasses import dataclass, field
from .enums import Availability, Phase, check_identifier

__all__ = ["Room"]

@dataclass(frozen=True)
class Room:
    """Salle physique, utilisée **uniquement** par les soutenances finales.

    Les pré-soutenances en ligne ne mobilisent aucune salle : ni disponibilité,
    ni occupation, ni plafond de salle ne s'y appliquent. La capacité d'accueil
    n'est pas une donnée du problème.

    Attributes:
        id: Identifiant unique, non vide.
        max_sessions_per_day: Plafond quotidien de finales dans la salle,
            entier strictement positif.
        availability: Couples (jour, créneau) où la salle est disponible.

    Raises:
        ValueError: Si ``id`` est vide ou si ``max_sessions_per_day`` < 1.
    """

    id: str
    max_sessions_per_day: int
    availability: Availability = field(default_factory=Availability.empty)

    def __post_init__(self) -> None:
        check_identifier(self.id, "Room.id")
        if self.max_sessions_per_day < 1:
            raise ValueError(
                f"Room {self.id!r} : max_sessions_per_day doit être >= 1, "
                f"reçu {self.max_sessions_per_day}"
            )

    @staticmethod
    def is_used_in_phase(phase: Phase) -> bool:
        """Indique si une salle est mobilisée pendant ``phase`` (finale seulement)."""
        return phase.requires_room

    def is_available(self, day: int, slot: int) -> bool:
        """Indique si la salle est disponible au créneau ``(day, slot)``."""
        return self.availability.is_available(day, slot)

    def allows_sessions_on_a_day(self, count: int) -> bool:
        """Indique si ``count`` finales un même jour respectent le plafond."""
        return count <= self.max_sessions_per_day