"""Tests du solveur glouton."""
from solvers.greedy import GreedyConfig, GreedySolver
from validation import SolutionValidator


def test_greedy_builds_a_valid_solution(demo_instance):
    report = GreedySolver(GreedyConfig(random_seed=17)).solve_with_report(demo_instance)
    assert report.valid
    assert report.solution is not None
    assert SolutionValidator().validate(demo_instance, report.solution).valid


def test_greedy_is_reproducible_with_fixed_seed(demo_instance):
    config = GreedyConfig(random_seed=23)
    first = GreedySolver(config).solve_with_report(demo_instance)
    second = GreedySolver(config).solve_with_report(demo_instance)
    assert first.valid and second.valid
    assert first.solution.sorted_sessions() == second.solution.sorted_sessions()
