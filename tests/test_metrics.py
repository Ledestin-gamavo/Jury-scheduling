"""Tests des cinq critères d'évaluation."""
from metrics import SolutionEvaluator


def test_reference_metric_vector(demo_instance, demo_solution):
    result = SolutionEvaluator().evaluate(demo_instance, demo_solution)
    assert result.as_vector() == (6, 6, 5, 2, 2)
    assert result.total_score == 21


def test_evaluation_is_deterministic(demo_instance, demo_solution):
    evaluator = SolutionEvaluator()
    assert evaluator.evaluate(demo_instance, demo_solution).as_vector() == evaluator.evaluate(
        demo_instance, demo_solution
    ).as_vector()
