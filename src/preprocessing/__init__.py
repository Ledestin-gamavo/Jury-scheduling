"""Module ``preprocessing`` : structures pré-calculées pour les solveurs.

Ce module regroupe tout ce qui peut être calculé **une seule fois** à partir
d'une :class:`core.instance.Instance` et réutilisé ensuite par les futurs
solveurs (``GreedySolver``, ``CPSATSolver``, ``HybridSolver``), par le
benchmarking et par les rapports. Il ne contient **aucune** logique de
résolution : ni heuristique gloutonne, ni modèle CP-SAT, ni optimisation.

Contenu :

* :mod:`preprocessing.availability_matrix` : accès en temps constant aux
  disponibilités (étudiants, enseignants, salles) et aux créneaux autorisés
  par phase ;
* :mod:`preprocessing.domain_filters` : filtres liés aux domaines (enseignants
  couvrant un domaine, examinateurs, présidents, statistiques par domaine) ;
* :mod:`preprocessing.jury_candidates` : présidents, examinateurs et binômes
  possibles pour chaque étudiant, calculés une seule fois et partagés entre
  étudiants équivalents ;
* :mod:`preprocessing.instance_statistics` : statistiques descriptives de
  l'instance (effectifs, densités, créneaux autorisés, capacités).

Règle de dépendance (voir ``current_progress.md``) : ``preprocessing`` dépend
uniquement de ``core``. Il ne dépend ni de ``parsers`` (les objets ``Instance``
sont fournis par l'appelant), ni de ``solvers``.

Hypothèse d'import : le dossier ``src/`` figure dans le chemin d'import Python
(``PYTHONPATH``).

Utilisation typique ::

    from parsers import load_instance
    from preprocessing import build_preprocessing

    instance = load_instance("data/small_01.json")
    context = build_preprocessing(instance)

    context.availability.student_available("S01", 0, 3)
    context.jury.pairs_for("S01")
    print(context.statistics.to_text())

Les objets sont construits une fois puis traités en lecture seule : ils
peuvent être partagés sans risque entre solveurs.
"""

from __future__ import annotations
from dataclasses import dataclass
from core.instance import Instance
from .availability_matrix import AvailabilityMatrix, TimeSlot, group_slots_by_day
from .domain_filters import DomainFilters, DomainStatistics
from .instance_statistics import (
    DensityStats,
    InstanceStatistics,
    compute_instance_statistics,
)
from .jury_candidates import JuryCandidates, JuryCandidatesSummary, Pair

__all__ = [
    # Disponibilités
    "AvailabilityMatrix",
    "TimeSlot",
    "group_slots_by_day",
    # Domaines
    "DomainFilters",
    "DomainStatistics",
    # Jurys
    "JuryCandidates",
    "JuryCandidatesSummary",
    "Pair",
    # Statistiques
    "DensityStats",
    "InstanceStatistics",
    "compute_instance_statistics",
    # Contexte complet
    "PreprocessingContext",
    "build_preprocessing",
]


@dataclass(frozen=True)
class PreprocessingContext:
    """Ensemble des structures pré-calculées pour une instance.

    Ce conteneur évite aux solveurs de reconstruire séparément chaque
    structure et garantit que toutes partagent les mêmes objets (par exemple,
    la même matrice de disponibilités).

    Attributes:
        instance: Instance d'origine.
        availability: Accès en temps constant aux disponibilités.
        domains: Filtres liés aux domaines.
        jury: Candidats de jury par étudiant.
        statistics: Statistiques descriptives de l'instance.
    """

    instance: Instance
    availability: AvailabilityMatrix
    domains: DomainFilters
    jury: JuryCandidates
    statistics: InstanceStatistics


def build_preprocessing(
    instance: Instance, *, prune_unavailable_teachers: bool = False
) -> PreprocessingContext:
    """Construit toutes les structures de pré-calcul d'une instance.

    Args:
        instance: Instance du problème.
        prune_unavailable_teachers: Si vrai, les candidats de jury sont filtrés
            pour exclure les enseignants n'ayant **aucun** créneau disponible
            dans la période d'une phase requise (condition nécessaire, voir
            :class:`preprocessing.jury_candidates.JuryCandidates`). Faux par
            défaut : les candidats ne reflètent alors que les rôles, les
            domaines et les distinctions de personnes.

    Returns:
        Le contexte de pré-traitement complet.
    """
    availability = AvailabilityMatrix(instance)
    domains = DomainFilters(instance)
    jury = JuryCandidates(
        instance,
        domain_filters=domains,
        availability=availability,
        prune_unavailable=prune_unavailable_teachers,
    )
    statistics = compute_instance_statistics(
        instance, availability=availability, domain_filters=domains
    )
    return PreprocessingContext(
        instance=instance,
        availability=availability,
        domains=domains,
        jury=jury,
        statistics=statistics,
    )