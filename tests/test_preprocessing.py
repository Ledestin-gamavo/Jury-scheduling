"""Tests de construction des structures pré-calculées."""
from preprocessing import build_preprocessing


def test_preprocessing_context_is_consistent(demo_instance):
    context = build_preprocessing(demo_instance)
    assert context.instance is demo_instance
    assert context.availability is not None
    assert context.domains is not None
    assert context.jury is not None
    assert context.statistics is not None


def test_preprocessing_does_not_mutate_instance(demo_instance):
    before = (demo_instance.instance_id, len(demo_instance.students), len(demo_instance.teachers))
    build_preprocessing(demo_instance, prune_unavailable_teachers=True)
    after = (demo_instance.instance_id, len(demo_instance.students), len(demo_instance.teachers))
    assert after == before
