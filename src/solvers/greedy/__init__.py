"""Paquet ``solvers.greedy`` : solveur constructif glouton (``GreedySolver``).

Le ``GreedySolver`` construit un planning **sans recherche exhaustive** :

1. **Étape 1.** Toutes les pré-soutenances sont placées (ordre MRV : les
   étudiants les plus contraints d'abord).
2. **Étape 2.** Toutes les finales sont placées, avec le binôme déjà choisi à
   l'étape 1 (continuité du jury).
3. **Étape 3.** Le planning est validé (module ``validation``).
4. **Étape 4.** Si des étudiants ne sont pas placés, une **réparation locale**
   (éviction puis réinsertion de quelques étudiants) est appliquée.
5. La solution est retournée, avec son évaluation (module ``metrics``) si elle
   est valide.

Organisation du paquet :

* :mod:`solvers.greedy.greedy_config` : configuration centralisée (:class:`GreedyConfig`) ;
* :mod:`solvers.greedy.candidate_ranking` : classement des créneaux, salles et binômes ;
* :mod:`solvers.greedy.session_builder` : état d'occupation (:class:`ScheduleState`)
  et construction d'une séance valide (:class:`SessionBuilder`) ;
* :mod:`solvers.greedy.repair` : réparation locale (:class:`RepairOperator`) ;
* :mod:`solvers.greedy.greedy_solver` : orchestration (:class:`GreedySolver`).

Garantie. Le solveur est une **heuristique** : il ne garantit pas de trouver un
planning complet sur toute instance, même réalisable. Il le dit explicitement
(:class:`SolveStatus`, :class:`GreedyReport`) et ne renvoie jamais un planning
présenté comme valide sans que le module ``validation`` l'ait confirmé.
``validator.py`` reste l'arbitre officiel.

Hypothèses d'import : ``src/`` figure dans le ``PYTHONPATH`` ; ``solvers`` peut
être un paquet espace de noms (sans ``__init__.py``).

Exemple ::

    from parsers import load_instance
    from solvers.greedy import GreedyConfig, GreedySolver

    instance = load_instance("data/small_01.json")
    solver = GreedySolver(GreedyConfig(random_seed=42))
    report = solver.solve_with_report(instance)
    print(report.status, report.evaluation.as_vector() if report.evaluation else None)
    solution = report.solution
"""

from __future__ import annotations

from .candidate_ranking import rank_jury_pairs, rank_rooms, rank_time_slots
from .greedy_config import GreedyConfig
from .greedy_solver import GreedyReport, GreedySolver, SolveStatus
from .repair import RepairOperator, RepairResult
from .session_builder import ScheduleState, SessionBuilder

__all__ = [
    "GreedyConfig",
    "GreedySolver",
    "GreedyReport",
    "SolveStatus",
    "RepairOperator",
    "RepairResult",
    "SessionBuilder",
    "ScheduleState",
    "rank_time_slots",
    "rank_rooms",
    "rank_jury_pairs",
]