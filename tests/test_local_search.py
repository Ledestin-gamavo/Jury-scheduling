"""Tests de l'amélioration locale."""
from solvers.local_search import LocalSearchConfig, LocalSearchSolver
from validation import SolutionValidator


def test_local_search_preserves_validity_and_does_not_degrade(demo_instance, demo_solution):
    original_sessions = list(demo_solution.sessions)
    report = LocalSearchSolver(LocalSearchConfig(random_seed=5, max_iterations=4)).improve_with_report(
        demo_instance, demo_solution
    )
    assert report.validation.valid
    assert report.final_score <= report.initial_score
    assert demo_solution.sessions == original_sessions
    assert SolutionValidator().validate(demo_instance, report.solution).valid


def test_local_search_rejects_invalid_solution(demo_instance, demo_solution):
    invalid = demo_solution.copy()
    session = invalid.sessions[0]
    invalid.remove(session.student_id, session.phase)
    before = list(invalid.sessions)
    report = LocalSearchSolver(LocalSearchConfig(max_iterations=1)).improve_with_report(
        demo_instance, invalid
    )
    assert not report.validation.valid
    assert invalid.sessions == before
