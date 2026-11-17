"""Solveur constructif glouton : :class:`GreedySolver`.

Stratégie (sans recherche exhaustive ni recherche locale) :

* **Étape 1.** Construire toutes les pré-soutenances. Les étudiants sont traités
  selon l'heuristique MRV (*Minimum Remaining Values*) : d'abord ceux qui ont le
  moins de créneaux candidats puis le moins de binômes possibles. Pour chaque
  étudiant, les binômes sont classés (réutilisation des binômes, charge), puis le
  créneau est choisi au coût estimé minimal (présence, créneaux creux,
  regroupement de l'encadrant). Pour un étudiant admissible, un binôme n'est
  retenu que si une finale reste faisable avec lui.
* **Étape 2.** Construire toutes les finales, avec le binôme déjà choisi
  (continuité du jury), même ordre MRV (selon les créneaux de finale), choix du
  créneau puis de la salle au coût minimal. Un étudiant dont la finale échoue
  perd aussi sa pré-soutenance : il sera replanifié en entier.
* **Étape 3.** Valider le planning avec ``SolutionValidator``.
* **Étape 4.** Si des étudiants ne sont pas placés (ou si la validation échoue),
  appliquer la réparation locale de :class:`~solvers.greedy.repair.RepairOperator`.
* **Étape 5.** Retourner la solution (et, si elle est valide, son évaluation par
  ``SolutionEvaluator``).

Usage des métriques. Le guidage glouton utilise des **variations locales**
calculées de façon incrémentale, qui reproduisent les définitions du contrat
(voir :mod:`solvers.greedy.candidate_ranking`). Recalculer ``SolutionEvaluator``
pour chaque candidat serait trop coûteux ; l'évaluateur n'est appelé qu'**une
fois**, sur la solution finale valide.

Garantie. Le ``GreedySolver`` est une heuristique : il ne garantit pas un planning
complet sur toute instance. Si des étudiants restent sans planification, la
solution retournée est **partielle** (elle ne contient que des étudiants entièrement
planifiés), le statut vaut ``INCOMPLETE`` et ``unplaced_students`` les liste.
Une solution n'est déclarée ``VALID`` que si ``SolutionValidator`` la confirme ;
``validator.py`` reste l'arbitre officiel.

Dépendances. Ce module importe ``validation`` (étape 3 demandée), en plus de
``core``, ``preprocessing`` et ``metrics``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from random import Random
from typing import Any

from core.enums import Phase
from core.instance import Instance
from core.solution import Solution
from metrics import EvaluationResult, SolutionEvaluator
from preprocessing import PreprocessingContext, build_preprocessing
from validation import SolutionValidator, ValidationResult

from .greedy_config import GreedyConfig
from .repair import RepairOperator
from .session_builder import ScheduleState, SessionBuilder

__all__ = ["SolveStatus", "GreedyReport", "GreedySolver"]


class SolveStatus(str, Enum):
    """Statut final d'une résolution.

    Attributes:
        VALID: Planning complet et confirmé valide par ``SolutionValidator``.
        INCOMPLETE: Des étudiants n'ont pas pu être planifiés.
        INVALID: Planning complet, mais rejeté par la validation.
        INVALID_INSTANCE: L'instance est structurellement incohérente ; rien n'a été résolu.
    """

    VALID = "valid"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    INVALID_INSTANCE = "invalid_instance"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class GreedyReport:
    """Rapport détaillé d'une résolution gloutonne.

    Attributes:
        solution: Planning obtenu (partiel si ``status`` est ``INCOMPLETE``).
        status: Statut final.
        validation: Résultat de la validation finale (``None`` si l'instance est incohérente).
        evaluation: Vecteur des cinq critères (``None`` si le planning n'est pas valide).
        unplaced_students: Étudiants sans planification.
        repair_iterations: Nombre de tours de réparation effectués.
        elapsed_seconds: Durée totale, en secondes.
        config: Configuration utilisée.
        messages: Informations complémentaires (par exemple erreurs d'instance).
    """

    solution: Solution
    status: SolveStatus
    validation: ValidationResult | None
    evaluation: EvaluationResult | None
    unplaced_students: tuple[str, ...]
    repair_iterations: int
    elapsed_seconds: float
    config: GreedyConfig
    messages: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """Vrai si le planning est complet et valide."""
        return self.status is SolveStatus.VALID

    def as_dict(self) -> dict[str, Any]:
        """Retourne un résumé sous forme de dictionnaire de types simples (ligne de benchmark)."""
        row: dict[str, Any] = {
            "instance_id": self.solution.instance_id,
            "solver": GreedySolver.name,
            "status": self.status.value,
            "valid": self.valid,
            "num_sessions": len(self.solution),
            "num_unplaced_students": len(self.unplaced_students),
            "num_errors": self.validation.error_count if self.validation else None,
            "repair_iterations": self.repair_iterations,
            "elapsed_seconds": self.elapsed_seconds,
            "random_seed": self.config.random_seed,
        }
        if self.evaluation is not None:
            row.update(self.evaluation.as_dict())
        return row


class GreedySolver:
    """Solveur constructif glouton pour la planification des soutenances.

    Le solveur est réutilisable : il ne conserve aucun état entre deux
    résolutions. Deux résolutions de la même instance avec la même configuration
    (donc la même graine) donnent le même résultat.

    Exemple ::

        solver = GreedySolver(GreedyConfig(random_seed=7))
        solution = solver.solve(instance)
        report = solver.solve_with_report(instance)

    Args:
        config: Configuration du solveur (configuration par défaut si absente).
    """

    name: str = "greedy"
    """Nom du solveur, utilisé par le futur registre et le banc d'essai."""

    def __init__(self, config: GreedyConfig | None = None) -> None:
        self._config = config if config is not None else GreedyConfig()
        self._validator = SolutionValidator(check_instance=False)
        self._evaluator = SolutionEvaluator()
        self._repair = RepairOperator(self._config)

    @property
    def config(self) -> GreedyConfig:
        """Configuration du solveur."""
        return self._config

    # API publique
    def solve(
        self, instance: Instance, *, context: PreprocessingContext | None = None
    ) -> Solution:
        """Résout une instance et retourne le planning obtenu.

        Le planning peut être **partiel** si l'heuristique échoue pour certains
        étudiants : utiliser :meth:`solve_with_report` pour connaître le statut.

        Args:
            instance: Instance du problème.
            context: Contexte de pré-traitement déjà construit (facultatif ;
                évite un recalcul dans les benchmarks et le solveur hybride).

        Returns:
            Le planning.
        """
        return self.solve_with_report(instance, context=context).solution

    def solve_with_report(
        self, instance: Instance, *, context: PreprocessingContext | None = None
    ) -> GreedyReport:
        """Résout une instance et retourne un rapport détaillé.

        Args:
            instance: Instance du problème.
            context: Contexte de pré-traitement déjà construit (facultatif).

        Returns:
            Le rapport (planning, statut, validation, évaluation, durée).
        """
        started = time.perf_counter()

        structural_errors = instance.structural_errors()
        if structural_errors:
            return GreedyReport(
                solution=Solution(instance_id=instance.instance_id),
                status=SolveStatus.INVALID_INSTANCE,
                validation=None,
                evaluation=None,
                unplaced_students=instance.student_ids,
                repair_iterations=0,
                elapsed_seconds=time.perf_counter() - started,
                config=self._config,
                messages=tuple(structural_errors[:10]),
            )

        if context is None:
            context = build_preprocessing(instance, prune_unavailable_teachers=True)
        builder = SessionBuilder(context, self._config, Random(self._config.random_seed))

        # Étapes 1 et 2 : construction.
        state, pending = self._construct(instance, builder)
        solution = state.to_solution()

        # Étape 3 : validation.
        validation = self._validator.validate(instance, solution)

        # Étape 4 : réparation.
        iterations = 0
        if self._config.use_repair and (pending or not validation.valid):
            repaired = self._repair.repair(instance, solution, context=context)
            solution = repaired.solution
            pending = list(repaired.unplaced_students)
            iterations = repaired.iterations
            validation = self._validator.validate(instance, solution)

        # Étape 5 : statut et évaluation.
        evaluation: EvaluationResult | None = None
        if pending:
            status = SolveStatus.INCOMPLETE
        elif validation.valid:
            status = SolveStatus.VALID
            evaluation = self._evaluator.evaluate(instance, solution)
        else:
            status = SolveStatus.INVALID

        return GreedyReport(
            solution=solution,
            status=status,
            validation=validation,
            evaluation=evaluation,
            unplaced_students=tuple(pending),
            repair_iterations=iterations,
            elapsed_seconds=time.perf_counter() - started,
            config=self._config,
        )

    # Construction (étapes 1 et 2)
    @staticmethod
    def _construct(instance: Instance, builder: SessionBuilder) -> tuple[ScheduleState, list[str]]:
        """Construit pré-soutenances puis finales ; retourne l'état et les étudiants en attente.

        Un étudiant dont la pré-soutenance ou la finale échoue est retiré de
        l'état (aucune séance orpheline) et ajouté à la liste d'attente.
        """
        state = ScheduleState(instance, builder.availability)
        student_ids = instance.student_ids
        pending: list[str] = []

        # Étape 1 : toutes les pré-soutenances, étudiants les plus contraints d'abord.
        for student_id in builder.mrv_order(student_ids):
            session = builder.build_predefence(state, student_id)
            if session is None:
                pending.append(student_id)
            else:
                state.add(session)

        # Étape 2 : toutes les finales, avec le binôme de la pré-soutenance.
        with_predefence = [
            student_id
            for student_id in student_ids
            if instance.student(student_id).eligible_final
            and state.session_of(student_id, Phase.PREDEFENCE) is not None
        ]
        for student_id in builder.mrv_order(with_predefence, Phase.FINAL):
            final = builder.build_final(state, student_id)
            if final is None:
                state.remove_student(student_id)
                pending.append(student_id)
            else:
                state.add(final)
        return state, pending