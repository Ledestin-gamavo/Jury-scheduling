"""Solveur d'amélioration locale : :class:`LocalSearchSolver`.

Entrée : une instance et une solution **valide**. Sortie : une solution valide
dont le score n'est jamais pire.

Algorithme (*hill climbing*, sans métaheuristique) : à chaque itération,

1. générer des mouvements candidats (:class:`NeighborhoodGenerator`), au plus
   ``max_moves_per_neighborhood`` par voisinage ;
2. pour chacun, tester sa faisabilité exacte et incrémentale
   (:meth:`MoveOperator.is_feasible`, qui réutilise les règles du
   ``GreedySolver``) ;
3. appliquer le mouvement faisable, l'évaluer avec ``SolutionEvaluator``, puis
   l'annuler ;
4. selon la stratégie (:class:`AcceptancePolicy`), arrêter au premier voisin
   strictement meilleur (*First Improvement*) ou retenir le meilleur de
   l'échantillon (*Best Improvement*) ;
5. accepter le mouvement retenu et le **confirmer par un ``SolutionValidator``
   complet** ; en cas de refus (ne devrait jamais se produire), le mouvement est
   annulé.

La recherche s'arrête sur ``max_iterations``, ``max_non_improving_iterations``,
la limite de temps, un optimum local prouvé (voisinage exhaustif) ou l'absence de
mouvement candidat.

Mesure des améliorations. L'objectif est ``EvaluationResult.total_score`` (somme
pondérée des cinq critères du contrat, poids ``config.weights``). Le rapport
(:class:`LocalSearchReport`) donne les évaluations initiale et finale, donc le
vecteur des cinq critères avant et après. Le contrat n'impose aucune
pondération : comparer deux solutions critère par critère reste possible avec
``EvaluationResult.as_vector`` et ``EvaluationResult.dominates``.

Garanties :

* une solution d'entrée invalide n'est **pas** modifiée (statut ``INVALID_INPUT``) ;
  c'est le cas d'une solution partielle du ``GreedySolver`` ;
* la solution retournée est validée par ``SolutionValidator`` ;
* l'instance et la solution d'entrée ne sont jamais modifiées (travail sur une copie).

Dépendances : ce module importe ``validation`` et ``solvers.greedy``
(``ScheduleState``, ``SessionBuilder``) afin de ne dupliquer aucune règle métier.

Préparation du ``HybridSolver`` : ``improve(instance, solution, context=...)``
accepte le contexte de pré-traitement déjà construit, ce qui évite un recalcul
dans l'enchaînement glouton puis amélioration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from random import Random
from typing import Any

from core.instance import Instance
from core.solution import Solution
from metrics import METRIC_NAMES, EvaluationResult, SolutionEvaluator
from preprocessing import PreprocessingContext, build_preprocessing
from solvers.greedy import GreedyConfig, ScheduleState, SessionBuilder
from validation import SolutionValidator, ValidationResult

from .acceptance import AcceptancePolicy
from .local_search_config import LocalSearchConfig
from .move_operator import Move, MoveOperator
from .neighborhood import NeighborhoodGenerator
from .statistics import SearchStatistics, StopReason

__all__ = ["SOLVER_NAME", "LocalSearchStatus", "LocalSearchReport", "LocalSearchSolver"]

SOLVER_NAME = "local_search"
"""Nom du solveur, utilisé par le futur registre et le banc d'essai."""


class LocalSearchStatus(str, Enum):
    """Statut final d'une amélioration.

    Attributes:
        IMPROVED: Le score total a été amélioré.
        NO_IMPROVEMENT: Aucune amélioration trouvée ; la solution est inchangée.
        INVALID_INPUT: La solution d'entrée est invalide ; elle est retournée telle quelle.
        INVALID_INSTANCE: L'instance est structurellement incohérente ; rien n'a été fait.
        REVERTED: La solution finale a été refusée par la validation (anomalie) ;
            la solution d'entrée est retournée.
    """

    IMPROVED = "improved"
    NO_IMPROVEMENT = "no_improvement"
    INVALID_INPUT = "invalid_input"
    INVALID_INSTANCE = "invalid_instance"
    REVERTED = "reverted"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LocalSearchReport:
    """Rapport détaillé d'une amélioration locale.

    Attributes:
        solution: Solution retournée (la meilleure solution valide trouvée).
        status: Statut final.
        initial_evaluation: Évaluation de la solution d'entrée (``None`` si elle est invalide).
        final_evaluation: Évaluation de la solution retournée (``None`` si non évaluée).
        validation: Validation de la solution retournée (ou d'entrée en cas de rejet).
        statistics: Statistiques de la recherche.
        config: Configuration utilisée.
        elapsed_seconds: Durée totale, en secondes.
        messages: Informations complémentaires (erreurs de validation, anomalies).
    """

    solution: Solution
    status: LocalSearchStatus
    initial_evaluation: EvaluationResult | None
    final_evaluation: EvaluationResult | None
    validation: ValidationResult | None
    statistics: SearchStatistics
    config: LocalSearchConfig
    elapsed_seconds: float
    messages: tuple[str, ...] = ()

    @property
    def improved(self) -> bool:
        """Vrai si le score total a été amélioré."""
        return self.status is LocalSearchStatus.IMPROVED

    @property
    def initial_score(self) -> float | None:
        """Score total initial (``None`` si non évalué)."""
        return None if self.initial_evaluation is None else self.initial_evaluation.total_score

    @property
    def final_score(self) -> float | None:
        """Score total final (``None`` si non évalué)."""
        return None if self.final_evaluation is None else self.final_evaluation.total_score

    @property
    def gain(self) -> float:
        """Amélioration du score total (``initial - final`` ; 0 si non évalué)."""
        if self.initial_score is None or self.final_score is None:
            return 0.0
        return self.initial_score - self.final_score

    @property
    def vector_gain(self) -> tuple[int, ...] | None:
        """Amélioration de chaque critère, dans l'ordre du contrat (``None`` si non évalué)."""
        if self.initial_evaluation is None or self.final_evaluation is None:
            return None
        return tuple(
            a - b
            for a, b in zip(
                self.initial_evaluation.as_vector(), self.final_evaluation.as_vector()
            )
        )

    def as_dict(self) -> dict[str, Any]:
        """Retourne un résumé plat de types simples (ligne de benchmark)."""
        row: dict[str, Any] = {
            "instance_id": self.solution.instance_id,
            "solver": SOLVER_NAME,
            "status": self.status.value,
            "valid": self.validation.valid if self.validation is not None else None,
            "num_sessions": len(self.solution),
            "initial_total_score": self.initial_score,
            "final_total_score": self.final_score,
            "gain": self.gain,
            "elapsed_seconds": self.elapsed_seconds,
            "random_seed": self.config.random_seed,
            "strategy": self.config.strategy.value,
        }
        for prefix, evaluation in (
            ("initial", self.initial_evaluation),
            ("final", self.final_evaluation),
        ):
            if evaluation is not None:
                for name, value in zip(METRIC_NAMES, evaluation.as_vector()):
                    row[f"{prefix}_{name}"] = value
        row.update({f"search_{key}": value for key, value in self.statistics.as_row().items()})
        return row


class LocalSearchSolver:
    """Améliore une solution valide par *hill climbing* (première ou meilleure amélioration).

    Le solveur ne conserve aucun état entre deux appels et peut être réutilisé.
    Deux appels avec les mêmes instance, solution et configuration (donc la même
    graine) donnent le même résultat.

    Exemple ::

        solver = LocalSearchSolver(LocalSearchConfig(strategy="best_improvement"))
        improved = solver.improve(instance, solution)
        report = solver.improve_with_report(instance, solution)

    Args:
        config: Configuration du solveur (configuration par défaut si absente).
    """

    name: str = SOLVER_NAME
    """Nom du solveur, utilisé par le futur registre et le banc d'essai."""

    def __init__(self, config: LocalSearchConfig | None = None) -> None:
        self._config = config if config is not None else LocalSearchConfig()
        self._validator = SolutionValidator(check_instance=False)
        self._evaluator = SolutionEvaluator(weights=self._config.weights)

    @property
    def config(self) -> LocalSearchConfig:
        """Configuration du solveur."""
        return self._config

    # API publique
    def improve(
        self,
        instance: Instance,
        solution: Solution,
        *,
        context: PreprocessingContext | None = None,
    ) -> Solution:
        """Améliore une solution valide.

        Args:
            instance: Instance du problème.
            solution: Solution **valide** (non modifiée).
            context: Contexte de pré-traitement déjà construit (facultatif).

        Returns:
            La meilleure solution valide trouvée, jamais pire que ``solution``. Si
            ``solution`` est invalide, une copie inchangée est retournée : utiliser
            :meth:`improve_with_report` pour connaître le statut.
        """
        return self.improve_with_report(instance, solution, context=context).solution

    def improve_with_report(
        self,
        instance: Instance,
        solution: Solution,
        *,
        context: PreprocessingContext | None = None,
    ) -> LocalSearchReport:
        """Améliore une solution valide et retourne un rapport détaillé.

        Args:
            instance: Instance du problème.
            solution: Solution **valide** (non modifiée).
            context: Contexte de pré-traitement déjà construit (facultatif ;
                construit avec filtrage des enseignants sans disponibilité si absent).

        Returns:
            Le rapport (solution, statut, évaluations avant et après, statistiques).
        """
        started = time.perf_counter()
        stats = SearchStatistics()

        structural_errors = instance.structural_errors()
        if structural_errors:
            return self._rejected(
                solution, LocalSearchStatus.INVALID_INSTANCE, None, structural_errors, stats, started
            )

        validation = self._validator.validate(instance, solution)
        if not validation.valid:
            return self._rejected(
                solution, LocalSearchStatus.INVALID_INPUT, validation, validation.errors, stats, started
            )

        if context is None:
            context = build_preprocessing(instance, prune_unavailable_teachers=True)

        work = solution.copy()
        initial = self._evaluator.evaluate(instance, work)
        stats.start(initial.total_score, initial.as_vector())
        final, reason = self._search(instance, work, context, initial, stats)

        messages: list[str] = []
        final_validation = self._validator.validate(instance, work)
        status = (
            LocalSearchStatus.IMPROVED if stats.moves_accepted > 0 else LocalSearchStatus.NO_IMPROVEMENT
        )
        if not final_validation.valid:
            messages.append(
                "Anomalie : la solution finale est refusée par la validation ; "
                "la solution d'entrée est retournée"
            )
            messages.extend(final_validation.errors[:10])
            work = solution.copy()
            final = initial
            final_validation = validation
            status = LocalSearchStatus.REVERTED

        stats.finish(final.total_score, final.as_vector(), reason)
        return LocalSearchReport(
            solution=work,
            status=status,
            initial_evaluation=initial,
            final_evaluation=final,
            validation=final_validation,
            statistics=stats,
            config=self._config,
            elapsed_seconds=time.perf_counter() - started,
            messages=tuple(messages),
        )

    # Rejet d'une entrée inexploitable
    def _rejected(
        self,
        solution: Solution,
        status: LocalSearchStatus,
        validation: ValidationResult | None,
        errors: Any,
        stats: SearchStatistics,
        started: float,
    ) -> LocalSearchReport:
        """Construit le rapport d'une entrée rejetée : la solution est retournée inchangée."""
        return LocalSearchReport(
            solution=solution.copy(),
            status=status,
            initial_evaluation=None,
            final_evaluation=None,
            validation=validation,
            statistics=stats,
            config=self._config,
            elapsed_seconds=time.perf_counter() - started,
            messages=tuple(list(errors)[:10]),
        )

    # Boucle de recherche
    def _commit(
        self,
        move: Move,
        instance: Instance,
        work: Solution,
        state: ScheduleState,
        operator: MoveOperator,
    ) -> bool:
        """Applique un mouvement retenu et le confirme par une validation complète.

        Returns:
            ``True`` si le mouvement est conservé ; ``False`` s'il a été annulé
            parce que ``SolutionValidator`` l'a refusé.
        """
        operator.apply(move, work)
        operator.apply_to_state(move, state)
        if self._config.validate_accepted_moves:
            if not self._validator.validate(instance, work).valid:
                operator.undo_on_state(move, state)
                operator.undo(move, work)
                return False
        return True

    def _search(
        self,
        instance: Instance,
        work: Solution,
        context: PreprocessingContext,
        initial: EvaluationResult,
        stats: SearchStatistics,
    ) -> tuple[EvaluationResult, StopReason]:
        """Exécute le *hill climbing* sur ``work`` (modifiée en place).

        Returns:
            L'évaluation de la solution finale et le motif d'arrêt.
        """
        config = self._config
        rng = Random(config.random_seed)
        builder = SessionBuilder(context, GreedyConfig(random_seed=config.random_seed), rng)
        state = ScheduleState(instance, context.availability)
        for session in work.sessions:
            state.add(session)
        operator = MoveOperator(builder)
        generator = NeighborhoodGenerator(context, config, rng)
        policy = AcceptancePolicy(config.strategy, config.min_improvement)
        deadline = (
            None
            if config.time_limit_seconds is None
            else time.perf_counter() + config.time_limit_seconds
        )

        def out_of_time() -> bool:
            return deadline is not None and time.perf_counter() >= deadline

        current = initial
        non_improving = 0
        while True:
            if stats.iterations >= config.max_iterations:
                return current, StopReason.MAX_ITERATIONS
            if non_improving >= config.max_non_improving_iterations:
                return current, StopReason.MAX_NON_IMPROVING
            if out_of_time():
                return current, StopReason.TIME_LIMIT

            stats.record_iteration()
            moves = generator.generate_moves(work.sessions, state)
            stats.record_generated(len(moves))
            if not moves:
                return current, StopReason.NO_MOVES

            selection = policy.new_selection(current.total_score)
            timed_out = False
            for move in moves:
                if out_of_time():
                    timed_out = True
                    break
                stats.record_tested(move.type)
                if not operator.is_feasible(move, state):
                    stats.record_infeasible(move.type)
                    continue
                operator.apply(move, work)
                try:
                    evaluation = self._evaluator.evaluate(instance, work)
                finally:
                    operator.undo(move, work)
                stats.record_evaluated(move.type)
                if selection.offer(move, evaluation):
                    break

            chosen, chosen_evaluation = selection.best_move, selection.best_evaluation
            accepted = False
            if chosen is not None and chosen_evaluation is not None:
                if self._commit(chosen, instance, work, state, operator):
                    stats.record_accepted(
                        chosen.type,
                        current.total_score - chosen_evaluation.total_score,
                        chosen_evaluation.total_score,
                    )
                    current = chosen_evaluation
                    accepted = True
                else:
                    stats.record_validator_rejection(chosen.type)

            if accepted:
                non_improving = 0
            else:
                non_improving += 1
                if config.is_exhaustive and chosen is None and not timed_out:
                    return current, StopReason.LOCAL_OPTIMUM
            if timed_out:
                return current, StopReason.TIME_LIMIT