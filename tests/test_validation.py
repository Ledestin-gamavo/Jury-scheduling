"""Tests des contraintes dures et de la couverture."""
from core.enums import Phase
from validation import SolutionValidator


def test_reference_solution_is_valid(demo_instance, demo_solution):
    result = SolutionValidator().validate(demo_instance, demo_solution)
    assert result.valid, result.errors


def test_missing_required_session_is_invalid(demo_instance, demo_solution):
    incomplete = demo_solution.copy()
    first = incomplete.sessions[0]
    incomplete.remove(first.student_id, first.phase)
    result = SolutionValidator().validate(demo_instance, incomplete)
    assert not result.valid
    assert any("COVERAGE" in error for error in result.errors)


def test_session_outside_phase_period_is_invalid(demo_instance, demo_solution):
    changed = demo_solution.copy()
    session = changed.sessions[0]
    changed.sessions[0] = session.moved_to(day=demo_instance.days - 1, slot=session.slot)
    result = SolutionValidator().validate(demo_instance, changed)
    assert not result.valid
