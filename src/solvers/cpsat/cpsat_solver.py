"""Orchestration du solveur CP-SAT pour la planification des soutenances."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ortools.sat.python import cp_model

from core.instance import Instance
from core.session import Session
from core.solution import Solution
from metrics import EvaluationResult, SolutionEvaluator
from validation import SolutionValidator, ValidationResult

from .model import build_model
from .variables import Candidate

__all__ = ["CPSATConfig", "CPSATStatus", "CPSATReport", "CPSATSolver"]

_METRIC_NAMES = (
    "teacher_presence_days",
    "teacher_idle_slots",
    "teacher_load_range",
    "supervisor_group_breaks",
    "distinct_jury_pairs",
)


@dataclass(frozen=True)
class CPSATConfig:
    """Paramètres du solveur CP-SAT.

    Les poids suivent l'ordre des cinq métriques du contrat. Des poids entiers
    sont requis par CP-SAT ; les valeurs par défaut les traitent à égalité.
    """

    time_limit_seconds: float = 60.0
    random_seed: int = 0
    num_search_workers: int = 1
    weights: tuple[int, int, int, int, int] = (1, 1, 1, 1, 1)

    def __post_init__(self) -> None:
        limit = self.time_limit_seconds
        if (
            isinstance(limit, bool)
            or not isinstance(limit, (int, float))
            or not math.isfinite(limit)
            or limit <= 0
        ):
            raise ValueError("time_limit_seconds doit être un nombre fini > 0")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ValueError("random_seed doit être un entier")
        if isinstance(self.num_search_workers, bool) or not isinstance(
            self.num_search_workers, int
        ) or self.num_search_workers < 1:
            raise ValueError("num_search_workers doit être un entier >= 1")
        weights = tuple(self.weights)
        if len(weights) != len(_METRIC_NAMES) or any(
            isinstance(weight, bool) or not isinstance(weight, int) or weight < 0
            for weight in weights
        ):
            raise ValueError("weights doit contenir cinq entiers positifs ou nuls")
        object.__setattr__(self, "weights", weights)


class CPSATStatus(str, Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"
    INVALID_INSTANCE = "invalid_instance"
    INVALID = "invalid"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CPSATReport:
    solution: Solution
    status: CPSATStatus
    validation: ValidationResult | None
    evaluation: EvaluationResult | None
    elapsed_seconds: float
    config: CPSATConfig
    messages: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.validation is not None and self.validation.valid

    def as_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "instance_id": self.solution.instance_id,
            "solver": CPSATSolver.name,
            "status": self.status.value,
            "valid": self.valid,
            "num_sessions": len(self.solution),
            "num_errors": self.validation.error_count if self.validation else None,
            "elapsed_seconds": self.elapsed_seconds,
            "random_seed": self.config.random_seed,
        }
        if self.evaluation is not None:
            row.update(self.evaluation.as_dict())
        return row


class CPSATSolver:
    """Construit, exécute et valide un modèle CP-SAT complet."""

    name = "cpsat"

    def __init__(self, config: CPSATConfig | None = None) -> None:
        self._config = config if config is not None else CPSATConfig()
        self._validator = SolutionValidator(check_instance=False)
        self._evaluator = SolutionEvaluator()

    @property
    def config(self) -> CPSATConfig:
        return self._config

    def solve(self, instance: Instance, *, warm_start: Solution | None = None) -> Solution:
        return self.solve_with_report(instance, warm_start=warm_start).solution

    def solve_with_report(
        self, instance: Instance, *, warm_start: Solution | None = None
    ) -> CPSATReport:
        started = time.perf_counter()
        solution = Solution(instance_id=instance.instance_id)
        structural_errors = instance.structural_errors()
        if structural_errors:
            return CPSATReport(
                solution=solution,
                status=CPSATStatus.INVALID_INSTANCE,
                validation=None,
                evaluation=None,
                elapsed_seconds=time.perf_counter() - started,
                config=self._config,
                messages=tuple(structural_errors[:10]),
            )

        model, candidates = build_model(instance, self._config.weights)
        if warm_start is not None and self._validator.validate(instance, warm_start).valid:
            candidate_variables = {candidate.key: candidate.variable for candidate in candidates}
            for session in warm_start:
                key = (
                    session.student_id,
                    session.phase,
                    session.president_id,
                    session.examiner_id,
                    session.day,
                    session.slot,
                    session.room_id,
                )
                variable = candidate_variables.get(key)
                if variable is not None:
                    model.AddHint(variable, 1)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self._config.time_limit_seconds
        solver.parameters.random_seed = self._config.random_seed
        solver.parameters.num_search_workers = self._config.num_search_workers
        status_code = solver.Solve(model)

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution.extend(
                _session_from_candidate(candidate)
                for candidate in candidates
                if solver.BooleanValue(candidate.variable)
            )
            validation = self._validator.validate(instance, solution)
            if not validation.valid:
                return CPSATReport(
                    solution=solution,
                    status=CPSATStatus.INVALID,
                    validation=validation,
                    evaluation=None,
                    elapsed_seconds=time.perf_counter() - started,
                    config=self._config,
                    messages=("La solution CP-SAT a échoué à la validation.",),
                )
            return CPSATReport(
                solution=solution,
                status=(
                    CPSATStatus.OPTIMAL
                    if status_code == cp_model.OPTIMAL
                    else CPSATStatus.FEASIBLE
                ),
                validation=validation,
                evaluation=self._evaluator.evaluate(instance, solution),
                elapsed_seconds=time.perf_counter() - started,
                config=self._config,
                messages=(solver.StatusName(status_code),),
            )

        status = (
            CPSATStatus.INFEASIBLE
            if status_code == cp_model.INFEASIBLE
            else CPSATStatus.UNKNOWN
        )
        return CPSATReport(
            solution=solution,
            status=status,
            validation=None,
            evaluation=None,
            elapsed_seconds=time.perf_counter() - started,
            config=self._config,
            messages=(solver.StatusName(status_code),),
        )


def _session_from_candidate(candidate: Candidate) -> Session:
    return Session(
        student_id=candidate.student_id,
        phase=candidate.phase,
        day=candidate.day,
        slot=candidate.slot,
        room_id=candidate.room_id,
        president_id=candidate.president_id,
        examiner_id=candidate.examiner_id,
    )
