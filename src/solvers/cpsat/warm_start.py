"""Préparation des indications CP-SAT à partir d'une solution connue."""

from __future__ import annotations

from dataclasses import dataclass

from core.instance import Instance
from core.solution import Solution
from validation.solution_validator import SolutionValidator
from ortools.sat.python import cp_model

from .variables import CPSATVariables


@dataclass(frozen=True)
class WarmStartResult:
    """Résultat de l'application éventuelle d'un démarrage à chaud."""

    applied: bool
    messages: tuple[str, ...] = ()


def add_warm_start(
    model: cp_model.CpModel,
    instance: Instance,
    variables: CPSATVariables,
    initial_solution: Solution | None,
) -> WarmStartResult:
    """Ajoute un hint complet uniquement si la solution initiale est valide.

    Une solution partielle, invalide ou non représentable dans l'espace des
    candidats n'est jamais injectée partiellement : le modèle reste autonome.
    """
    if initial_solution is None:
        return WarmStartResult(False, ("Aucune solution initiale fournie.",))
    validation = SolutionValidator().validate(instance, initial_solution)
    if not validation.valid:
        return WarmStartResult(False, ("Warm start ignoré : solution initiale invalide.",
                                       *validation.errors))
    selected_keys = {
        (session.student_id, session.phase, session.president_id,
         session.examiner_id, session.room_id, session.day, session.slot)
        for session in initial_solution
    }
    candidate_keys = set(variables.assignments)
    if not selected_keys.issubset(candidate_keys):
        return WarmStartResult(
            False,
            ("Warm start ignoré : au moins une affectation initiale n'est pas candidate CP-SAT.",),
        )
    for key, variable in variables.assignments.items():
        model.AddHint(variable, 1 if key in selected_keys else 0)
    return WarmStartResult(True, ("Warm start valide appliqué.",))
