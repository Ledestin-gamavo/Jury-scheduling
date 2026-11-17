"""Assemblage du modèle CP-SAT à partir des composants du paquet."""

from __future__ import annotations

from ortools.sat.python import cp_model

from core.instance import Instance

from .constraints import add_constraints
from .objectives import build_objective_terms
from .variables import Candidate, create_candidates

__all__ = ["build_model"]


def build_model(
	instance: Instance, weights: tuple[int, int, int, int, int]
) -> tuple[cp_model.CpModel, list[Candidate]]:
	"""Construit variables, contraintes dures et objectif pondéré."""
	model = cp_model.CpModel()
	candidates = create_candidates(model, instance)
	add_constraints(model, instance, candidates)
	objective_terms = build_objective_terms(model, instance, candidates)
	model.Minimize(
		sum(weight * term for weight, term in zip(weights, objective_terms))
	)
	return model, candidates
