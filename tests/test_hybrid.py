import pytest
pytest.importorskip("ortools", reason="OR-Tools requis pour le solveur hybride")

"""Tests du pipeline hybride."""
from solvers.hybrid import HybridConfig, HybridSolver
from solvers.greedy import GreedyConfig
from solvers.local_search import LocalSearchConfig


def test_hybrid_returns_valid_solution_from_greedy(demo_instance):
    config = HybridConfig(
        run_greedy=True,
        run_local_search=True,
        run_cpsat=False,
        greedy_config=GreedyConfig(random_seed=11),
        local_search_config=LocalSearchConfig(max_iterations=2),
    )
    report = HybridSolver(config).solve_with_report(demo_instance)
    assert report.valid
    assert report.solution is not None
