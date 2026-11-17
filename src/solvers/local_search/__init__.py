"""Paquet ``solvers.local_search`` : amélioration locale d'une solution valide.

Le :class:`LocalSearchSolver` améliore un planning **déjà valide** (typiquement
produit par le ``GreedySolver``) par *hill climbing* : à chaque itération, il
génère des voisins, ne garde que ceux qui respectent les contraintes dures, les
note avec ``SolutionEvaluator`` et accepte un voisin **strictement meilleur**.

Pipeline prévu pour le futur ``HybridSolver`` ::

    GreedySolution  ->  LocalSearchSolver  ->  ImprovedSolution

Exemple ::

    from solvers.greedy import GreedySolver
    from solvers.local_search import LocalSearchConfig, LocalSearchSolver

    greedy_solution = GreedySolver().solve(instance)
    solver = LocalSearchSolver(LocalSearchConfig(random_seed=1))
    report = solver.improve_with_report(instance, greedy_solution)
    print(report.status, report.initial_score, "->", report.final_score)
    improved = report.solution

Organisation :

* :mod:`solvers.local_search.local_search_config` : paramètres (:class:`LocalSearchConfig`) ;
* :mod:`solvers.local_search.move_operator` : mouvements réversibles
  (:class:`Move`, :class:`MoveType`, :class:`MoveOperator`) ;
* :mod:`solvers.local_search.neighborhood` : génération bornée des voisins
  (:class:`NeighborhoodGenerator`) ;
* :mod:`solvers.local_search.acceptance` : première ou meilleure amélioration
  (:class:`AcceptancePolicy`) ;
* :mod:`solvers.local_search.statistics` : suivi de la recherche
  (:class:`SearchStatistics`) ;
* :mod:`solvers.local_search.local_search_solver` : orchestration
  (:class:`LocalSearchSolver`).

Périmètre : uniquement du *hill climbing* (première ou meilleure amélioration).
Aucune métaheuristique (ni recherche tabou, ni recuit simulé, ni algorithme
génétique).

Garantie : la solution retournée est toujours valide au sens de
``SolutionValidator`` et son score n'est jamais pire que celui de la solution
d'entrée. ``validator.py`` reste l'arbitre officiel.
"""

from __future__ import annotations

from .acceptance import AcceptancePolicy, ImprovementStrategy, MoveSelection
from .local_search_config import LocalSearchConfig
from .local_search_solver import (
    LocalSearchReport,
    LocalSearchSolver,
    LocalSearchStatus,
)
from .move_operator import Move, MoveOperator, MoveType, SessionChange
from .neighborhood import NeighborhoodGenerator
from .statistics import MoveCounters, SearchStatistics, StopReason

__all__ = [
    "LocalSearchSolver",
    "LocalSearchReport",
    "LocalSearchStatus",
    "LocalSearchConfig",
    "NeighborhoodGenerator",
    "Move",
    "MoveType",
    "SessionChange",
    "MoveOperator",
    "AcceptancePolicy",
    "ImprovementStrategy",
    "MoveSelection",
    "SearchStatistics",
    "MoveCounters",
    "StopReason",
]