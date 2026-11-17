"""Assemblage du modèle complet de planification CP-SAT."""

from __future__ import annotations

from dataclasses import dataclass

from core.instance import Instance
from ortools.sat.python import cp_model

from .constraints import add_hard_constraints
from .cpsat_config import CPSATConfig
from .objectives import add_objective
from .variables import CPSATVariables, create_variables


@dataclass
class CPSATModel:
    """Modèle CP-SAT et registres associés nécessaires à l'extraction."""

    model: cp_model.CpModel
    variables: CPSATVariables
    metrics: dict[str, cp_model.IntVar]


def build_model(instance: Instance, config: CPSATConfig) -> CPSATModel:
    """Construit variables, contraintes dures et objectif pondéré."""
    model = cp_model.CpModel()
    variables = create_variables(model, instance)
    add_hard_constraints(model, instance, variables)
    metrics = add_objective(model, instance, variables, config.objective_weights)
    return CPSATModel(model=model, variables=variables, metrics=metrics)
