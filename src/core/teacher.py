"""Modèle métier d'un enseignant."""

from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass, field
from .enums import Availability, Role, check_identifier

__all__ = ["Teacher"]

@dataclass(frozen=True)
class Teacher:
    """Enseignant susceptible de siéger dans un jury.

    Un enseignant peut aussi être encadrant (et donc rapporteur à la finale) ;
    dans ce cas, c'est la **même personne**, référencée par son identifiant dans
    :attr:`core.student.Student.supervisor_id`.

    L'objet est immuable et hachable, donc partageable sans risque entre
    solveurs. Les itérables passés pour ``domains`` et ``eligible_roles`` sont
    convertis en ``frozenset``.

    Attributes:
        id: Identifiant unique, non vide.
        domains: Domaines que l'enseignant peut examiner.
        eligible_roles: Rôles de jury autorisés (peut être vide).
        max_sessions_per_day: Plafond quotidien de séances attendues (toutes
            phases confondues), entier strictement positif.
        availability: Couples (jour, créneau) où l'enseignant est disponible.

    Raises:
        ValueError: Si ``id`` est vide ou si ``max_sessions_per_day`` < 1.
    """

    id: str
    domains: frozenset[str]
    eligible_roles: frozenset[Role]
    max_sessions_per_day: int
    availability: Availability = field(default_factory=Availability.empty)

    def __post_init__(self) -> None:
        check_identifier(self.id, "Teacher.id")
        if self.max_sessions_per_day < 1:
            raise ValueError(
                f"Teacher {self.id!r} : max_sessions_per_day doit être >= 1, "
                f"reçu {self.max_sessions_per_day}"
            )
        object.__setattr__(self, "domains", frozenset(self.domains))
        object.__setattr__(
            self, "eligible_roles", frozenset(Role(role) for role in self.eligible_roles)
        )

    # Fabrique pratique pour les tests et futurs parseurs
    @classmethod
    def build(
        cls,
        id: str,
        domains: Iterable[str],
        eligible_roles: Iterable[Role | str],
        max_sessions_per_day: int,
        availability: Availability | None = None,
    ) -> Teacher:
        """Construit un enseignant à partir d'itérables quelconques.

        Args:
            id: Identifiant unique.
            domains: Domaines examinables.
            eligible_roles: Rôles autorisés (``Role`` ou chaînes de valeur).
            max_sessions_per_day: Plafond quotidien.
            availability: Disponibilités (vide par défaut).

        Returns:
            L'enseignant construit.
        """
        return cls(
            id=id,
            domains=frozenset(domains),
            eligible_roles=frozenset(Role(role) for role in eligible_roles),
            max_sessions_per_day=max_sessions_per_day,
            availability=availability if availability is not None else Availability.empty(),
        )

    # Règles d'éligibilité
    def can_serve_as(self, role: Role) -> bool:
        """Indique si l'enseignant est habilité à tenir ``role``."""
        return role in self.eligible_roles

    @property
    def can_preside(self) -> bool:
        """Vrai si l'enseignant est habilité comme président."""
        return Role.PRESIDENT in self.eligible_roles

    def covers_domain(self, domain: str) -> bool:
        """Indique si l'enseignant couvre le domaine ``domain``."""
        return domain in self.domains

    def can_examine(self, domain: str) -> bool:
        """Indique si l'enseignant peut être examinateur pour ``domain``.

        Il faut à la fois le rôle ``examiner`` et la couverture du domaine.
        Le président, lui, n'est soumis à aucune condition de domaine.
        """
        return Role.EXAMINER in self.eligible_roles and domain in self.domains

    # Disponibilité et plafond
    def is_available(self, day: int, slot: int) -> bool:
        """Indique si l'enseignant est disponible au créneau ``(day, slot)``."""
        return self.availability.is_available(day, slot)

    def allows_sessions_on_a_day(self, count: int) -> bool:
        """Indique si ``count`` séances un même jour respectent le plafond."""
        return count <= self.max_sessions_per_day