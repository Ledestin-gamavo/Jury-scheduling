"""Fixtures partagées de la suite de tests."""
from pathlib import Path
import pytest
from parsers import load_instance, load_solution

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def demo_instance():
    """Charge l'instance pédagogique fournie avec le dépôt."""
    return load_instance(ROOT / "examples" / "demo_instance.json")

@pytest.fixture(scope="session")
def demo_solution(demo_instance):
    """Charge la solution de référence de l'instance pédagogique."""
    return load_solution(ROOT / "examples" / "demo_solution.json", instance=demo_instance)
