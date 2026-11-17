"""Tests des objets valeur et conteneurs du noyau métier."""
from dataclasses import FrozenInstanceError
import pytest
from core.enums import Availability, Phase
from core.session import Session
from core.solution import Solution


def test_availability_queries_are_deterministic():
    availability = Availability({1: {2, 0}, 0: {1}})
    assert availability.is_available(1, 2)
    assert not availability.is_available(1, 1)
    assert availability.slots_on(9) == frozenset()
    assert availability.count() == 3
    assert tuple(availability.iter_pairs()) == ((0, 1), (1, 0), (1, 2))


def test_availability_is_immutable():
    availability = Availability({0: {1, 2}})
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        availability.slots_by_day = {}
    assert availability.slots_on(0) == frozenset({1, 2})


def test_solution_copy_does_not_share_session_list():
    original = Solution("instance")
    duplicate = original.copy()
    duplicate.add(Session("student", Phase.PREDEFENCE, 0, 0, None, "p", "e"))
    assert len(original) == 0
    assert len(duplicate) == 1
