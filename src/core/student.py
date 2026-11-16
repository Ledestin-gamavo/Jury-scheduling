"""Modèle métier d'un étudiant."""

from __future__ import annotations
from dataclasses import dataclass, field
from .enums import Availability, Phase, check_identifier

__all__ = ["Student"]

@dataclass(frozen=True)
class Student:
    """Étudiant devant soutenir.

    Tout étudiant passe exactement une pré-soutenance en ligne. Seul un étudiant
    avec ``eligible_final=True`` passe exactement une finale ; les autres n'en
    ont aucune. L'admissibilité est une **donnée** du problème, non une
    décision de l'algorithme.

    Attributes:
        id: Identifiant unique, non vide.
        domain: Domaine scientifique du projet.
        supervisor_id: Identifiant de l'enseignant encadrant, qui est aussi le
            rapporteur à la finale (une seule personne).
        eligible_final: Admissibilité à la soutenance finale.
        availability: Couples (jour, créneau) où l'étudiant est disponible.

    Raises:
        ValueError: Si ``id`` ou ``supervisor_id`` est vide.
    """

    id: str
    domain: str
    supervisor_id: str
    eligible_final: bool
    availability: Availability = field(default_factory=Availability.empty)

    def __post_init__(self) -> None:
        check_identifier(self.id, "Student.id")
        check_identifier(self.supervisor_id, "Student.supervisor_id")

    @property
    def requires_final(self) -> bool:
        """Vrai si une soutenance finale est exigée pour cet étudiant."""
        return self.eligible_final

    def required_phases(self) -> tuple[Phase, ...]:
        """Retourne les phases que l'étudiant doit passer, une fois chacune.

        Returns:
            ``(PREDEFENCE,)`` ou ``(PREDEFENCE, FINAL)`` selon l'admissibilité.
        """
        if self.eligible_final:
            return (Phase.PREDEFENCE, Phase.FINAL)
        return (Phase.PREDEFENCE,)

    def requires_phase(self, phase: Phase) -> bool:
        """Indique si l'étudiant doit passer la phase ``phase``."""
        return phase in self.required_phases()

    def is_available(self, day: int, slot: int) -> bool:
        """Indique si l'étudiant est disponible au créneau ``(day, slot)``."""
        return self.availability.is_available(day, slot)