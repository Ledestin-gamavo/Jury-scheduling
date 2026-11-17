"""Tests du contrat de lecture JSON."""
import pytest
from parsers import JSONFormatError, load_instance, load_solution, parse_json_text


def test_demo_files_round_trip(demo_instance, demo_solution):
    assert demo_instance.instance_id == "demo_pedagogique"
    assert len(demo_solution) > 0


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(JSONFormatError):
        parse_json_text('{"value": 1, "value": 2}')


def test_non_integer_json_numbers_are_rejected():
    with pytest.raises(JSONFormatError):
        parse_json_text('{"value": 1.5}')


def test_missing_json_file_is_rejected(tmp_path):
    with pytest.raises(JSONFormatError):
        load_instance(tmp_path / "missing.json")


def test_solution_instance_mismatch_is_rejected(demo_solution):
    data = {"schema_version": demo_solution.schema_version,
            "instance_id": "another-instance",
            "sessions": []}
    from parsers import solution_from_dict
    with pytest.raises(Exception):
        solution_from_dict(data, instance_id="demo_pedagogique")
