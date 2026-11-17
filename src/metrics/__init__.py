"""Module ``metrics`` : calcul des cinq critères du contrat v4.0.

Ce module transforme une solution **valide** en un vecteur de cinq scores, tous
à **minimiser**, dans l'ordre du contrat :

1. :func:`teacher_presence_days` : jours de présence des enseignants ;
2. :func:`teacher_idle_slots` : créneaux creux des enseignants ;
3. :func:`teacher_load_range` : écart entre la charge maximale et minimale ;
4. :func:`supervisor_group_breaks` : ruptures de regroupement par encadrant ;
5. :func:`distinct_jury_pairs` : nombre de binômes (président, examinateur) distincts.

Le contrat n'impose aucune pondération : le résultat de référence est le
**vecteur** des cinq critères (:class:`EvaluationResult`). Le ``total_score``
est une scalarisation de convenance, configurable (voir
:class:`SolutionEvaluator`).

Précondition commune : les fonctions de ce module supposent une solution
**valide** au sens du contrat (voir le module ``validation``). Le contrat ne
définit des métriques que pour les solutions valides. Sur une solution
invalide, le résultat n'a pas de signification ; seules les références
inconnues sont détectées (:class:`MetricsInputError`). Les métriques **ne
modifient jamais** l'instance ni la solution (lecture seule).

Règle de dépendance (voir ``current_progress.md``) : ``metrics`` dépend
uniquement de ``core``.

Exemple ::

    from metrics import SolutionEvaluator

    result = SolutionEvaluator().evaluate(instance, solution)
    print(result.as_vector())
"""

from __future__ import annotations
from .distinct_jury_pairs import distinct_jury_pairs, jury_pairs
from .evaluate import (
    DEFAULT_WEIGHTS,
    METRIC_NAMES,
    EvaluationResult,
    SolutionEvaluator,
    evaluate_solution,
)
from .supervisor_group_breaks import (
    supervisor_group_breaks,
    supervisor_group_breaks_by_phase,
    supervisor_group_counts,
)
from .teacher_idle_slots import teacher_idle_slots
from .teacher_load_range import teacher_load_range, teacher_session_counts
from .teacher_presence_days import (
    MetricsInputError,
    teacher_attendance,
    teacher_presence_days,
)

__all__ = [
    # Métriques
    "teacher_presence_days",
    "teacher_idle_slots",
    "teacher_load_range",
    "supervisor_group_breaks",
    "distinct_jury_pairs",
    # Détails utiles
    "teacher_attendance",
    "teacher_session_counts",
    "supervisor_group_counts",
    "supervisor_group_breaks_by_phase",
    "jury_pairs",
    # Évaluation globale
    "EvaluationResult",
    "SolutionEvaluator",
    "evaluate_solution",
    "METRIC_NAMES",
    "DEFAULT_WEIGHTS",
    # Exceptions
    "MetricsInputError",
]