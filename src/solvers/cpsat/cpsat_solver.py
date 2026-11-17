"""Solveur CP-SAT et rapports de résolution validés métier."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution
from metrics.evaluate import EvaluationResult, SolutionEvaluator
from ortools.sat.python import cp_model
from validation.solution_validator import SolutionValidator, ValidationResult

from .cpsat_config import CPSATConfig
from .model import CPSATModel, build_model
from .warm_start import WarmStartResult, add_warm_start


class CPSATStatus(str, Enum):
    """Statuts normalisés du moteur CP-SAT."""

    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    MODEL_INVALID = "model_invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CPSATStatistics:
    """Statistiques numériques communiquées par OR-Tools."""

    conflicts: int
    branches: int
    wall_time_seconds: float
    deterministic_time: float
    response: str


@dataclass(frozen=True)
class CPSATReport:
    """Rapport complet d'une exécution CP-SAT.

    Attributes:
        solution: Solution extraite, vide si aucune solution n'a été trouvée.
        status: Statut du moteur.
        valid: Validité métier après passage dans SolutionValidator.
        validation: Détail de la validation, si une solution a été extraite.
        evaluation: Métriques, uniquement pour une solution valide.
        objective_value: Valeur de l'objectif scalaire, si disponible.
        best_objective_bound: Meilleure borne connue, si disponible.
        relative_gap: Gap relatif calculé, si disponible.
        elapsed_seconds: Temps écoulé côté application.
        statistics: Statistiques détaillées du moteur.
        config: Configuration réellement utilisée.
        warm_start: Résultat d'application du warm start.
        messages: Messages de diagnostic.
    """

    solution: Solution
    status: CPSATStatus
    valid: bool
    validation: ValidationResult | None
    evaluation: EvaluationResult | None
    objective_value: float | None
    best_objective_bound: float | None
    relative_gap: float | None
    elapsed_seconds: float
    statistics: CPSATStatistics | None
    config: CPSATConfig
    warm_start: WarmStartResult
    messages: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Retourne un résumé de types simples adapté aux journaux."""
        return {
            "instance_id": self.solution.instance_id,
            "solver": "cpsat",
            "status": self.status.value,
            "valid": self.valid,
            "num_sessions": len(self.solution),
            "objective_value": self.objective_value,
            "best_objective_bound": self.best_objective_bound,
            "relative_gap": self.relative_gap,
            "elapsed_seconds": self.elapsed_seconds,
            "random_seed": self.config.random_seed,
            "warm_start_applied": self.warm_start.applied,
            "metrics": None if self.evaluation is None else self.evaluation.as_dict(),
            "validation_errors": () if self.validation is None else self.validation.errors,
        }


class CPSATSolver:
    """Construit et résout le modèle combinatoire avec OR-Tools CP-SAT."""

    name: str = "cpsat"

    def __init__(self, config: CPSATConfig | None = None) -> None:
        """Initialise les paramètres, le validateur et l'évaluateur partagés."""
        self._config = config if config is not None else CPSATConfig()
        self._validator = SolutionValidator()
        self._evaluator = SolutionEvaluator(weights=self._config.objective_weights)

    @property
    def config(self) -> CPSATConfig:
        """Configuration immuable du solveur."""
        return self._config

    def solve(self, instance: Instance, initial_solution: Solution | None = None) -> Solution:
        """Retourne la solution trouvée (vide si le modèle est infaisable)."""
        return self.solve_with_report(instance, initial_solution).solution

    def solve_with_report(
        self,
        instance: Instance,
        initial_solution: Solution | None = None,
    ) -> CPSATReport:
        """Résout une instance et vérifie automatiquement toute solution extraite."""
        started = time.perf_counter()
        empty_solution = Solution(instance_id=instance.instance_id)
        structural_errors = instance.structural_errors()
        if structural_errors:
            return CPSATReport(
                empty_solution, CPSATStatus.MODEL_INVALID, False, None, None,
                None, None, None, time.perf_counter() - started, None,
                self._config, WarmStartResult(False), tuple(structural_errors),
            )

        built = build_model(instance, self._config)
        warm_start = (
            add_warm_start(built.model, instance, built.variables, initial_solution)
            if self._config.use_warm_start else WarmStartResult(False, ("Warm start désactivé.",))
        )
        solver = cp_model.CpSolver()
        parameters = solver.parameters
        parameters.random_seed = self._config.random_seed
        parameters.num_search_workers = self._config.num_search_workers
        parameters.log_search_progress = self._config.log_search_progress
        if self._config.time_limit_seconds is not None:
            parameters.max_time_in_seconds = self._config.time_limit_seconds
        if self._config.relative_gap_limit is not None:
            parameters.relative_gap_limit = self._config.relative_gap_limit
        if self._config.max_memory_mb is not None:
            parameters.max_memory_in_mb = self._config.max_memory_mb

        raw_status = solver.Solve(built.model)
        elapsed = time.perf_counter() - started
        status_map = {
            cp_model.OPTIMAL: CPSATStatus.OPTIMAL,
            cp_model.FEASIBLE: CPSATStatus.FEASIBLE,
            cp_model.INFEASIBLE: CPSATStatus.INFEASIBLE,
            cp_model.MODEL_INVALID: CPSATStatus.MODEL_INVALID,
            cp_model.UNKNOWN: CPSATStatus.UNKNOWN,
        }
        status = status_map.get(raw_status, CPSATStatus.UNKNOWN)
        statistics = CPSATStatistics(
            conflicts=solver.NumConflicts(),
            branches=solver.NumBranches(),
            wall_time_seconds=solver.WallTime(),
            deterministic_time=solver.ResponseProto().deterministic_time,
            response=solver.ResponseStats(),
        )
        if raw_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return CPSATReport(
                empty_solution, status, False, None, None, None, None, None,
                elapsed, statistics, self._config, warm_start,
                warm_start.messages,
            )

        solution = self._extract_solution(instance, built, solver)
        validation = self._validator.validate(instance, solution)
        evaluation = self._evaluator.evaluate(instance, solution) if validation.valid else None
        objective = solver.ObjectiveValue()
        bound = solver.BestObjectiveBound()
        gap = abs(objective - bound) / max(1.0, abs(objective))
        messages = list(warm_start.messages)
        if not validation.valid:
            messages.append("La solution extraite a échoué à la validation officielle.")
            messages.extend(validation.errors)
        return CPSATReport(
            solution=solution,
            status=status,
            valid=validation.valid,
            validation=validation,
            evaluation=evaluation,
            objective_value=objective,
            best_objective_bound=bound,
            relative_gap=gap,
            elapsed_seconds=elapsed,
            statistics=statistics,
            config=self._config,
            warm_start=warm_start,
            messages=tuple(messages),
        )

    @staticmethod
    def _extract_solution(
        instance: Instance,
        built: CPSATModel,
        solver: cp_model.CpSolver,
    ) -> Solution:
        """Convertit les variables sélectionnées en objets métier Session."""
        result = Solution(instance_id=instance.instance_id)
        for candidate in built.variables.candidates:
            variable = built.variables.assignments[candidate.key]
            if solver.BooleanValue(variable):
                result.add(Session(
                    student_id=candidate.student_id,
                    phase=candidate.phase,
                    day=candidate.day,
                    slot=candidate.slot,
                    room_id=candidate.room_id,
                    president_id=candidate.president_id,
                    examiner_id=candidate.examiner_id,
                ))
        result.sessions.sort(key=lambda session: session.sort_key)
        return result
