"""Types de base partagés du noyau métier.

Ce module est la couche la plus basse du paquet ``core`` : il ne dépend d'aucun
autre module du projet. Il regroupe :

* les énumérations du domaine (:class:`Phase`, :class:`Role`, :class:`InstanceSize`) ;
* la constante de version du contrat (:data:`SCHEMA_VERSION`) ;
* le type valeur :class:`Availability`, partagé par les enseignants, les
  étudiants et les salles ;
* la fonction utilitaire :func:`check_identifier`.

Remarque d'architecture : l'arborescence du projet ne permet aucun fichier
supplémentaire dans ``core/``. :class:`Availability` est donc hébergée ici, car
elle est utilisée par ``teacher.py``, ``student.py`` et ``room.py`` ; la placer
dans l'un d'eux créerait une dépendance artificielle entre entités.

Les énumérations héritent de ``str`` : leurs membres se comparent et se
sérialisent comme leurs valeurs (``"predefence"``, ``"president"``…), ce qui
facilite le futur export JSON sans code de conversion.
"""

from __future__ import annotations
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "SCHEMA_VERSION",
    "Phase",
    "Role",
    "InstanceSize",
    "Availability",
    "check_identifier",
]

SCHEMA_VERSION: str = "4.0"
"""Version du contrat de données (instances et solutions)."""


class Phase(str, Enum):
    """Phase d'une séance de soutenance.

    Attributes:
        PREDEFENCE: Pré-soutenance en ligne, sans salle.
        FINAL: Soutenance finale en salle, avec l'encadrant comme rapporteur.
    """

    PREDEFENCE = "predefence"
    FINAL = "final"

    def __str__(self) -> str:
        return self.value

    @property
    def is_online(self) -> bool:
        """Vrai si la phase se déroule en ligne (aucune salle mobilisée)."""
        return self is Phase.PREDEFENCE

    @property
    def requires_room(self) -> bool:
        """Vrai si la phase mobilise obligatoirement une salle physique."""
        return self is Phase.FINAL


class Role(str, Enum):
    """Rôle de jury qu'un enseignant peut tenir dans le binôme de jury.

    Attributes:
        PRESIDENT: Président du jury (pas d'obligation de domaine).
        EXAMINER: Examinateur (doit couvrir le domaine de l'étudiant).
    """

    PRESIDENT = "president"
    EXAMINER = "examiner"

    def __str__(self) -> str:
        return self.value


class InstanceSize(str, Enum):
    """Classe de taille d'une instance.

    Attributes:
        DEMO: Instance de démonstration (hors benchmark).
        SMALL: Petite instance.
        MEDIUM: Instance moyenne.
        LARGE: Grande instance.
    """

    DEMO = "demo"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    def __str__(self) -> str:
        return self.value


def check_identifier(value: str, label: str) -> None:
    """Vérifie qu'un identifiant est une chaîne non vide et non blanche.

    Args:
        value: Identifiant à contrôler.
        label: Nom lisible du champ, utilisé dans le message d'erreur.

    Raises:
        ValueError: Si ``value`` n'est pas une chaîne ou ne contient que des blancs.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} doit être une chaîne non vide, reçu : {value!r}")


@dataclass(frozen=True)
class Availability:
    """Ensemble immuable de couples (jour, créneau) disponibles.

    Une absence d'entrée signifie une indisponibilité. Les indices de jours et
    de créneaux sont des entiers à partir de zéro. L'objet est normalisé à la
    construction (clés ``int``, valeurs ``frozenset[int]``) et ne doit pas être
    modifié ensuite.

    Cette classe ne connaît pas les bornes de l'instance (``days``,
    ``slots_per_day``) : leur contrôle relève de
    :meth:`core.instance.Instance.structural_errors` ou de la validation.

    Attributes:
        slots_by_day: Correspondance ``jour -> créneaux disponibles``.
    """

    slots_by_day: Mapping[int, frozenset[int]] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        normalized = {
            int(day): frozenset(int(slot) for slot in slots)
            for day, slots in self.slots_by_day.items()
        }
        object.__setattr__(self, "slots_by_day", normalized)

    # Constructeurs
    @classmethod
    def empty(cls) -> Availability:
        """Retourne une disponibilité vide (aucun créneau disponible)."""
        return cls({})

    @classmethod
    def from_entries(cls, entries: Iterable[tuple[int, Iterable[int]]]) -> Availability:
        """Construit une disponibilité à partir de couples ``(jour, créneaux)``.

        Args:
            entries: Couples ``(jour, créneaux)``. Un jour ne doit apparaître
                qu'une fois, conformément au contrat.

        Returns:
            La disponibilité normalisée.

        Raises:
            ValueError: Si un jour apparaît plusieurs fois.
        """
        mapping: dict[int, frozenset[int]] = {}
        for day, slots in entries:
            if day in mapping:
                raise ValueError(f"Jour {day} répété dans la disponibilité")
            mapping[day] = frozenset(slots)
        return cls(mapping)

    # Requêtes
    def is_available(self, day: int, slot: int) -> bool:
        """Indique si le créneau ``slot`` du jour ``day`` est disponible."""
        return slot in self.slots_by_day.get(day, frozenset())

    def slots_on(self, day: int) -> frozenset[int]:
        """Retourne les créneaux disponibles un jour donné (vide si aucun)."""
        return self.slots_by_day.get(day, frozenset())

    @property
    def days(self) -> frozenset[int]:
        """Jours possédant au moins une entrée de disponibilité."""
        return frozenset(self.slots_by_day)

    @property
    def is_empty(self) -> bool:
        """Vrai si aucun créneau n'est disponible."""
        return not any(self.slots_by_day.values())

    def count(self) -> int:
        """Nombre total de couples (jour, créneau) disponibles."""
        return sum(len(slots) for slots in self.slots_by_day.values())

    def iter_pairs(self) -> Iterator[tuple[int, int]]:
        """Itère sur les couples ``(jour, créneau)`` disponibles, triés."""
        for day in sorted(self.slots_by_day):
            for slot in sorted(self.slots_by_day[day]):
                yield day, slot

    def restricted_to_days(self, days: Iterable[int]) -> Availability:
        """Retourne la disponibilité restreinte à un ensemble de jours.

        Utile pour ne conserver que les jours d'une période commune (par
        exemple lors du pré-calcul d'un modèle CP-SAT).
        """
        wanted = frozenset(days)
        return Availability(
            {day: slots for day, slots in self.slots_by_day.items() if day in wanted}
        )

    def as_entries(self) -> tuple[tuple[int, tuple[int, ...]], ...]:
        """Retourne une vue triée ``((jour, (créneaux…)), …)`` pour l'export."""
        return tuple(
            (day, tuple(sorted(self.slots_by_day[day]))) for day in sorted(self.slots_by_day)
        )