"""Orchestration robuste des solveurs Greedy, Local Search et CP-SAT."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from core.instance import Instance
from core.solution import Solution
from metrics import EvaluationResult, SolutionEvaluator
from preprocessing import PreprocessingContext, build_preprocessing
from validation import SolutionValidator, ValidationResult
from solvers.cpsat import CPSATConfig, CPSATReport, CPSATSolver
from solvers.greedy import GreedyReport, GreedySolver
from solvers.local_search import LocalSearchConfig, LocalSearchReport, LocalSearchSolver

from .hybrid_config import HybridConfig


class HybridStatus(str, Enum):
    """Statuts normalisés du pipeline hybride."""

    COMPLETED = "completed"
    GREEDY_FAILED = "greedy_failed"
    INVALID_INITIAL_SOLUTION = "invalid_initial_solution"
    NO_VALID_SOLUTION = "no_valid_solution"


@dataclass(frozen=True)
class HybridStatistics:
    """Indicateurs synthétiques des étapes du pipeline."""

    greedy_elapsed_seconds: float
    greedy_unplaced_students: int
    local_search_elapsed_seconds: float
    local_search_gain: float
    cpsat_elapsed_seconds: float
    cpsat_status: str | None
    cpsat_objective_value: float | None
    cpsat_relative_gap: float | None
    selected_stage: str


@dataclass(frozen=True)
class HybridReport:
    """Rapport complet de résolution hybride.

    Attributes:
        solution: Meilleure solution valide connue, vide en cas d'échec global.
        status: Statut global du pipeline.
        validation: Résultat de validation de la solution retournée.
        evaluation: Évaluation de la solution retournée.
        statistics: Statistiques synthétiques des trois étapes.
        elapsed_seconds: Durée totale du pipeline.
        greedy_report: Rapport Greedy, si exécuté.
        local_search_report: Rapport Local Search, si exécuté.
        cpsat_report: Rapport CP-SAT, si exécuté.
        messages: Diagnostics et décisions de sélection.
    """

    solution: Solution
    status: HybridStatus
    validation: ValidationResult | None
    evaluation: EvaluationResult | None
    statistics: HybridStatistics
    elapsed_seconds: float
    greedy_report: GreedyReport | None = None
    local_search_report: LocalSearchReport | None = None
    cpsat_report: CPSATReport | None = None
    messages: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """Indique si la solution finale a été validée."""
        return self.validation is not None and self.validation.valid

    def as_dict(self) -> dict[str, Any]:
        """Retourne une ligne synthétique adaptée aux journaux de benchmark."""
        row: dict[str, Any] = {
            "instance_id": self.solution.instance_id,
            "solver": "hybrid",
            "status": self.status.value,
            "valid": self.valid,
            "num_sessions": len(self.solution),
            "elapsed_seconds": self.elapsed_seconds,
            "selected_stage": self.statistics.selected_stage,
            "greedy_elapsed_seconds": self.statistics.greedy_elapsed_seconds,
            "greedy_unplaced_students": self.statistics.greedy_unplaced_students,
            "local_search_elapsed_seconds": self.statistics.local_search_elapsed_seconds,
            "local_search_gain": self.statistics.local_search_gain,
            "cpsat_elapsed_seconds": self.statistics.cpsat_elapsed_seconds,
            "cpsat_status": self.statistics.cpsat_status,
            "cpsat_objective_value": self.statistics.cpsat_objective_value,
            "cpsat_relative_gap": self.statistics.cpsat_relative_gap,
        }
        if self.evaluation is not None:
            row.update(self.evaluation.as_dict())
        return row


class HybridSolver:
    """Exécute les trois solveurs sans perdre une solution valide de qualité.

    Toute solution candidate est contrôlée par ``SolutionValidator``. Les
    comparaisons reposent sur ``SolutionEvaluator`` avec les poids CP-SAT afin
    que les trois étapes utilisent exactement la même scalarisation.
    """

    name: str = "hybrid"

    def __init__(self, config: HybridConfig | None = None) -> None:
        """Initialise les solveurs spécialisés et les services métier partagés."""
        self._config = config if config is not None else HybridConfig()
        self._validator = SolutionValidator()
        self._evaluator = SolutionEvaluator(
            weights=self._config.cpsat_config.objective_weights
        )
        self._greedy = GreedySolver(self._config.greedy_config)
        self._local_search = LocalSearchSolver(self._build_local_search_config())
        self._cpsat = CPSATSolver(self._build_cpsat_config())

    @property
    def config(self) -> HybridConfig:
        """Configuration immuable du pipeline."""
        return self._config

    def _build_local_search_config(self) -> LocalSearchConfig:
        """Applique les poids communs et l'éventuelle limite de temps locale."""
        changes: dict[str, Any] = {
            "weights": dict(self._config.cpsat_config.objective_weights)
        }
        if self._config.local_search_time_limit is not None:
            changes["time_limit_seconds"] = self._config.local_search_time_limit
        return replace(self._config.local_search_config, **changes)

    def _build_cpsat_config(self) -> CPSATConfig:
        """Applique les options propres à l'orchestration hybride."""
        changes: dict[str, Any] = {"use_warm_start": self._config.enable_warm_start}
        if self._config.cpsat_time_limit is not None:
            changes["time_limit_seconds"] = self._config.cpsat_time_limit
        return replace(self._config.cpsat_config, **changes)

    def solve(self, instance: Instance, initial_solution: Solution | None = None) -> Solution:
        """Retourne la meilleure solution valide obtenue."""
        return self.solve_with_report(instance, initial_solution).solution

    def solve_with_report(
        self,
        instance: Instance,
        initial_solution: Solution | None = None,
    ) -> HybridReport:
        """Exécute le pipeline et retourne la meilleure solution valide.

        Args:
            instance: Instance à planifier.
            initial_solution: Solution initiale facultative. Elle est obligatoire
                lorsque Greedy est désactivé et doit alors être valide.

        Returns:
            Rapport complet et solution retenue.
        """
        started = time.perf_counter()
        empty = Solution(instance_id=instance.instance_id)
        if instance.structural_errors():
            stats = self._empty_statistics()
            return HybridReport(
                empty, HybridStatus.NO_VALID_SOLUTION, None, None, stats,
                time.perf_counter() - started,
                messages=tuple(instance.structural_errors()),
            )

        context: PreprocessingContext = build_preprocessing(
            instance, prune_unavailable_teachers=True
        )
        messages: list[str] = []
        incumbent: Solution | None = None
        incumbent_validation: ValidationResult | None = None
        incumbent_evaluation: EvaluationResult | None = None
        selected_stage = "none"

        if initial_solution is not None:
            initial_validation = self._validator.validate(instance, initial_solution)
            if not initial_validation.valid:
                if not self._config.run_greedy:
                    return HybridReport(
                        empty, HybridStatus.INVALID_INITIAL_SOLUTION,
                        initial_validation, None, self._empty_statistics(),
                        time.perf_counter() - started,
                        messages=("La solution initiale est invalide.", *initial_validation.errors),
                    )
                messages.append("La solution initiale invalide est ignorée.")
            else:
                incumbent = initial_solution.copy()
                incumbent_validation = initial_validation
                incumbent_evaluation = self._evaluator.evaluate(instance, incumbent)
                selected_stage = "initial_solution"

        greedy_report: GreedyReport | None = None
        local_report: LocalSearchReport | None = None
        cpsat_report: CPSATReport | None = None
        greedy_elapsed = 0.0
        greedy_unplaced = 0
        local_elapsed = 0.0
        local_gain = 0.0
        cpsat_elapsed = 0.0

        if self._config.run_greedy:
            greedy_report = self._greedy.solve_with_report(instance, context=context)
            greedy_elapsed = greedy_report.elapsed_seconds
            greedy_unplaced = len(greedy_report.unplaced_students)
            if greedy_report.valid:
                incumbent, incumbent_validation, incumbent_evaluation, selected_stage = (
                    self._select_if_better(
                        instance, incumbent, incumbent_validation, incumbent_evaluation,
                        greedy_report.solution, "greedy", selected_stage,
                    )
                )
            else:
                messages.append(
                    f"Greedy n'a pas produit de planning complet valide : {greedy_report.status.value}."
                )
                messages.extend(greedy_report.messages)
                stats = self._make_statistics(
                    greedy_elapsed, greedy_unplaced, 0.0, 0.0, 0.0,
                    None, None, None, "none",
                )
                return HybridReport(
                    empty, HybridStatus.GREEDY_FAILED, greedy_report.validation,
                    None, stats, time.perf_counter() - started,
                    greedy_report=greedy_report, messages=tuple(messages),
                )

        if incumbent is None:
            stats = self._make_statistics(
                greedy_elapsed, greedy_unplaced, 0.0, 0.0, 0.0,
                None, None, None, "none",
            )
            return HybridReport(
                empty, HybridStatus.NO_VALID_SOLUTION, None, None, stats,
                time.perf_counter() - started, greedy_report=greedy_report,
                messages=tuple(messages + ["Aucune solution valide disponible."]),
            )

        if self._config.run_local_search:
            local_report = self._local_search.improve_with_report(
                instance, incumbent, context=context
            )
            local_elapsed = local_report.elapsed_seconds
            local_gain = local_report.gain
            if local_report.validation is not None and local_report.validation.valid:
                incumbent, incumbent_validation, incumbent_evaluation, selected_stage = (
                    self._select_if_better(
                        instance, incumbent, incumbent_validation, incumbent_evaluation,
                        local_report.solution, "local_search", selected_stage,
                    )
                )
            else:
                messages.append(
                    "Local Search n'a pas retourné une solution validée ; incumbent conservé."
                )
                messages.extend(local_report.messages)

        if self._config.run_cpsat:
            cpsat_report = self._cpsat.solve_with_report(instance, incumbent)
            cpsat_elapsed = cpsat_report.elapsed_seconds
            if cpsat_report.valid and cpsat_report.validation is not None:
                incumbent, incumbent_validation, incumbent_evaluation, selected_stage = (
                    self._select_if_better(
                        instance, incumbent, incumbent_validation, incumbent_evaluation,
                        cpsat_report.solution, "cpsat", selected_stage,
                    )
                )
            else:
                messages.append(
                    f"CP-SAT n'a pas fourni de solution valide ({cpsat_report.status.value}) ; "
                    "la meilleure solution intermédiaire est conservée."
                )
                messages.extend(cpsat_report.messages)

        final_validation = self._validator.validate(instance, incumbent)
        if not final_validation.valid:
            messages.extend(final_validation.errors)
            stats = self._make_statistics(
                greedy_elapsed, greedy_unplaced, local_elapsed, local_gain,
                cpsat_elapsed,
                cpsat_report.status.value if cpsat_report else None,
                cpsat_report.objective_value if cpsat_report else None,
                cpsat_report.relative_gap if cpsat_report else None,
                "none",
            )
            return HybridReport(
                empty, HybridStatus.NO_VALID_SOLUTION, final_validation, None,
                stats, time.perf_counter() - started, greedy_report,
                local_report, cpsat_report, tuple(messages),
            )

        final_evaluation = self._evaluator.evaluate(instance, incumbent)
        stats = self._make_statistics(
            greedy_elapsed, greedy_unplaced, local_elapsed, local_gain,
            cpsat_elapsed,
            cpsat_report.status.value if cpsat_report else None,
            cpsat_report.objective_value if cpsat_report else None,
            cpsat_report.relative_gap if cpsat_report else None,
            selected_stage,
        )
        return HybridReport(
            solution=incumbent,
            status=HybridStatus.COMPLETED,
            validation=final_validation,
            evaluation=final_evaluation,
            statistics=stats,
            elapsed_seconds=time.perf_counter() - started,
            greedy_report=greedy_report,
            local_search_report=local_report,
            cpsat_report=cpsat_report,
            messages=tuple(messages),
        )

    def _select_if_better(
        self,
        instance: Instance,
        incumbent: Solution | None,
        incumbent_validation: ValidationResult | None,
        incumbent_evaluation: EvaluationResult | None,
        candidate: Solution,
        stage: str,
        selected_stage: str,
    ) -> tuple[Solution, ValidationResult, EvaluationResult, str]:
        """Valide et compare un candidat sans jamais dégrader l'incumbent."""
        validation = self._validator.validate(instance, candidate)
        if not validation.valid:
            return self._require_incumbent(
                incumbent, incumbent_validation, incumbent_evaluation, selected_stage
            )
        evaluation = self._evaluator.evaluate(instance, candidate)
        if incumbent is None or incumbent_evaluation is None or self._is_better(
            evaluation, incumbent_evaluation
        ):
            return candidate.copy(), validation, evaluation, stage
        return self._require_incumbent(
            incumbent, incumbent_validation, incumbent_evaluation, selected_stage
        )

    @staticmethod
    def _require_incumbent(
        solution: Solution | None,
        validation: ValidationResult | None,
        evaluation: EvaluationResult | None,
        stage: str,
    ) -> tuple[Solution, ValidationResult, EvaluationResult, str]:
        """Garantit les types non optionnels après établissement d'un incumbent."""
        if solution is None or validation is None or evaluation is None:
            raise RuntimeError("Invariant interne violé : aucun incumbent valide n'est disponible.")
        return solution, validation, evaluation, stage

    @staticmethod
    def _is_better(candidate: EvaluationResult, incumbent: EvaluationResult) -> bool:
        """Compare le score pondéré puis le vecteur des cinq critères."""
        if candidate.total_score != incumbent.total_score:
            return candidate.total_score < incumbent.total_score
        return candidate.as_vector() < incumbent.as_vector()

    @staticmethod
    def _empty_statistics() -> HybridStatistics:
        """Construit des statistiques nulles pour un arrêt avant résolution."""
        return HybridStatistics(0.0, 0, 0.0, 0.0, 0.0, None, None, None, "none")

    @staticmethod
    def _make_statistics(
        greedy_elapsed: float,
        greedy_unplaced: int,
        local_elapsed: float,
        local_gain: float,
        cpsat_elapsed: float,
        cpsat_status: str | None,
        cpsat_objective: float | None,
        cpsat_gap: float | None,
        selected_stage: str,
    ) -> HybridStatistics:
        """Construit l'objet de statistiques de sortie."""
        return HybridStatistics(
            greedy_elapsed, greedy_unplaced, local_elapsed, local_gain,
            cpsat_elapsed, cpsat_status, cpsat_objective, cpsat_gap, selected_stage,
        )
