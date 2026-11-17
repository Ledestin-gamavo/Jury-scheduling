"""Tests d'intégration du pipeline de résolution."""
import pytest
pytest.importorskip("ortools", reason="OR-Tools requis pour le pipeline complet")

from solvers.hybrid import HybridConfig, HybridSolver
from solvers.greedy import GreedyConfig
from solvers.local_search import LocalSearchConfig
from validation import SolutionValidator


def test_hybrid_pipeline_produces_a_valid_schedule(demo_instance):
    config = HybridConfig(
        run_greedy=True,
        run_local_search=True,
        run_cpsat=True,
        greedy_config=GreedyConfig(random_seed=31),
        local_search_config=LocalSearchConfig(max_iterations=3),
    )
    report = HybridSolver(config).solve_with_report(demo_instance)
    assert report.valid
    assert report.solution is not None
    assert SolutionValidator().validate(demo_instance, report.solution).valid
