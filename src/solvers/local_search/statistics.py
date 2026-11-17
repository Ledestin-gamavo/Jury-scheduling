"""Statistiques de la recherche locale.

:class:`SearchStatistics` suit le déroulement d'une recherche :

* **itérations** effectuées ;
* **mouvements** générés, testés (faisabilité), infaisables, évalués
  (``SolutionEvaluator``), acceptés, et refusés par la validation complète ;
* **amélioration du score** (score total et vecteur des cinq critères, avant et
  après), avec l'historique des scores après chaque mouvement accepté ;
* **temps** écoulé ;
* motif d'arrêt (:class:`StopReason`) ;
* les mêmes compteurs **par voisinage**, pour mesurer l'utilité de chacun
  (:class:`MoveCounters`).

Définitions : un mouvement « testé » est un mouvement dont la faisabilité a été
contrôlée ; « évalué » est un mouvement faisable dont le score a été calculé avec
``SolutionEvaluator``. Un mouvement « accepté » a été appliqué à la solution
courante après confirmation.

Les scores sont ceux de ``EvaluationResult.total_score`` (à minimiser) :
l'amélioration est donc ``score initial - score final``, positive lorsque la
recherche a progressé.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .move_operator import MoveType

__all__ = ["StopReason", "MoveCounters", "SearchStatistics"]


class StopReason(str, Enum):
    """Motif d'arrêt de la recherche.

    Attributes:
        NOT_STARTED: La recherche n'a pas eu lieu.
        MAX_ITERATIONS: Nombre maximal d'itérations atteint.
        MAX_NON_IMPROVING: Trop d'itérations consécutives sans amélioration.
        TIME_LIMIT: Limite de temps atteinte.
        LOCAL_OPTIMUM: Optimum local prouvé (voisinage exhaustif sans amélioration).
        NO_MOVES: Aucun mouvement candidat n'a pu être généré.
    """

    NOT_STARTED = "not_started"
    MAX_ITERATIONS = "max_iterations"
    MAX_NON_IMPROVING = "max_non_improving"
    TIME_LIMIT = "time_limit"
    LOCAL_OPTIMUM = "local_optimum"
    NO_MOVES = "no_moves"

    def __str__(self) -> str:
        return self.value


@dataclass
class MoveCounters:
    """Compteurs d'un voisinage.

    Attributes:
        tested: Mouvements dont la faisabilité a été contrôlée.
        infeasible: Mouvements refusés car infaisables.
        evaluated: Mouvements faisables évalués.
        accepted: Mouvements acceptés.
        total_gain: Somme des gains de score des mouvements acceptés.
    """

    tested: int = 0
    infeasible: int = 0
    evaluated: int = 0
    accepted: int = 0
    total_gain: float = 0.0

    def as_dict(self) -> dict[str, float | int]:
        """Retourne les compteurs sous forme de dictionnaire."""
        return {
            "tested": self.tested,
            "infeasible": self.infeasible,
            "evaluated": self.evaluated,
            "accepted": self.accepted,
            "total_gain": self.total_gain,
        }


@dataclass
class SearchStatistics:
    """Suivi d'une recherche locale (objet mutable, mis à jour par le solveur).

    Attributes:
        iterations: Itérations effectuées.
        moves_generated: Mouvements générés.
        moves_tested: Mouvements dont la faisabilité a été testée.
        moves_infeasible: Mouvements infaisables.
        moves_evaluated: Mouvements faisables évalués.
        moves_accepted: Mouvements acceptés.
        moves_rejected_by_validator: Mouvements refusés par la validation complète
            (devrait rester à 0 : un écart signale une divergence des contrôles).
        initial_score: Score total initial.
        final_score: Score total final.
        initial_vector: Vecteur initial des cinq critères.
        final_vector: Vecteur final des cinq critères.
        stop_reason: Motif d'arrêt.
        elapsed_seconds: Durée de la recherche, en secondes.
        per_type: Compteurs par voisinage.
        history: Couples ``(itération, score total)`` après chaque mouvement accepté.
    """

    iterations: int = 0
    moves_generated: int = 0
    moves_tested: int = 0
    moves_infeasible: int = 0
    moves_evaluated: int = 0
    moves_accepted: int = 0
    moves_rejected_by_validator: int = 0
    initial_score: float | None = None
    final_score: float | None = None
    initial_vector: tuple[int, ...] | None = None
    final_vector: tuple[int, ...] | None = None
    stop_reason: StopReason = StopReason.NOT_STARTED
    elapsed_seconds: float = 0.0
    per_type: dict[MoveType, MoveCounters] = field(
        default_factory=lambda: {move_type: MoveCounters() for move_type in MoveType}
    )
    history: list[tuple[int, float]] = field(default_factory=list)
    _started_at: float | None = field(default=None, repr=False, compare=False)

    # Cycle de vie
    def start(self, initial_score: float, initial_vector: tuple[int, ...]) -> None:
        """Démarre le chronomètre et enregistre l'état initial.

        Args:
            initial_score: Score total initial.
            initial_vector: Vecteur initial des cinq critères.
        """
        self.initial_score = initial_score
        self.final_score = initial_score
        self.initial_vector = tuple(initial_vector)
        self.final_vector = tuple(initial_vector)
        self._started_at = time.perf_counter()

    def finish(
        self, final_score: float, final_vector: tuple[int, ...], reason: StopReason
    ) -> None:
        """Arrête le chronomètre et enregistre l'état final.

        Args:
            final_score: Score total final.
            final_vector: Vecteur final des cinq critères.
            reason: Motif d'arrêt.
        """
        self.final_score = final_score
        self.final_vector = tuple(final_vector)
        self.stop_reason = reason
        if self._started_at is not None:
            self.elapsed_seconds = time.perf_counter() - self._started_at
            self._started_at = None

    @property
    def elapsed(self) -> float:
        """Durée écoulée : en cours de recherche, temps courant ; sinon durée finale."""
        if self._started_at is not None:
            return time.perf_counter() - self._started_at
        return self.elapsed_seconds

    # Enregistrement
    def record_iteration(self) -> None:
        """Compte une itération."""
        self.iterations += 1

    def record_generated(self, count: int) -> None:
        """Compte des mouvements générés."""
        self.moves_generated += count

    def record_tested(self, move_type: MoveType) -> None:
        """Compte un mouvement dont la faisabilité est testée."""
        self.moves_tested += 1
        self.per_type[move_type].tested += 1

    def record_infeasible(self, move_type: MoveType) -> None:
        """Compte un mouvement infaisable."""
        self.moves_infeasible += 1
        self.per_type[move_type].infeasible += 1

    def record_evaluated(self, move_type: MoveType) -> None:
        """Compte un mouvement faisable évalué avec ``SolutionEvaluator``."""
        self.moves_evaluated += 1
        self.per_type[move_type].evaluated += 1

    def record_accepted(self, move_type: MoveType, gain: float, new_score: float) -> None:
        """Compte un mouvement accepté et mémorise le score obtenu.

        Args:
            move_type: Voisinage du mouvement.
            gain: Gain de score du mouvement (positif).
            new_score: Score total après le mouvement.
        """
        self.moves_accepted += 1
        counters = self.per_type[move_type]
        counters.accepted += 1
        counters.total_gain += gain
        self.history.append((self.iterations, new_score))

    def record_validator_rejection(self, move_type: MoveType) -> None:
        """Compte un mouvement refusé par la validation complète."""
        self.moves_rejected_by_validator += 1

    # Résultats
    @property
    def improvement(self) -> float:
        """Amélioration du score total (``initial - final`` ; positive si meilleur)."""
        if self.initial_score is None or self.final_score is None:
            return 0.0
        return self.initial_score - self.final_score

    @property
    def improvement_ratio(self) -> float | None:
        """Amélioration relative (``None`` si le score initial est nul ou inconnu)."""
        if not self.initial_score:
            return None
        return self.improvement / self.initial_score

    @property
    def vector_improvement(self) -> tuple[int, ...] | None:
        """Amélioration de chaque critère (``initial - final`` par composante)."""
        if self.initial_vector is None or self.final_vector is None:
            return None
        return tuple(a - b for a, b in zip(self.initial_vector, self.final_vector))

    def as_dict(self) -> dict[str, Any]:
        """Retourne les statistiques sous forme de dictionnaire de types simples."""
        return {
            "iterations": self.iterations,
            "moves_generated": self.moves_generated,
            "moves_tested": self.moves_tested,
            "moves_infeasible": self.moves_infeasible,
            "moves_evaluated": self.moves_evaluated,
            "moves_accepted": self.moves_accepted,
            "moves_rejected_by_validator": self.moves_rejected_by_validator,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "improvement": self.improvement,
            "improvement_ratio": self.improvement_ratio,
            "initial_vector": list(self.initial_vector) if self.initial_vector else None,
            "final_vector": list(self.final_vector) if self.final_vector else None,
            "stop_reason": self.stop_reason.value,
            "elapsed_seconds": self.elapsed,
            "per_type": {move_type.value: c.as_dict() for move_type, c in self.per_type.items()},
            "history": [list(entry) for entry in self.history],
        }

    def as_row(self) -> dict[str, Any]:
        """Retourne une ligne plate de valeurs simples (benchmark, CSV)."""
        row: dict[str, Any] = {
            "iterations": self.iterations,
            "moves_generated": self.moves_generated,
            "moves_tested": self.moves_tested,
            "moves_infeasible": self.moves_infeasible,
            "moves_evaluated": self.moves_evaluated,
            "moves_accepted": self.moves_accepted,
            "moves_rejected_by_validator": self.moves_rejected_by_validator,
            "improvement": self.improvement,
            "improvement_ratio": self.improvement_ratio,
            "stop_reason": self.stop_reason.value,
            "elapsed_seconds": self.elapsed,
        }
        for move_type, counters in self.per_type.items():
            row[f"accepted_{move_type.value}"] = counters.accepted
        return row

    def to_text(self) -> str:
        """Retourne un rapport texte lisible (en français)."""
        ratio = self.improvement_ratio
        ratio_text = "sans objet" if ratio is None else f"{ratio:.1%}"
        lines = [
            f"Recherche locale : {self.iterations} itération(s), arrêt : {self.stop_reason.value}, "
            f"durée {self.elapsed:.3f} s",
            f"  score total : {self.initial_score} -> {self.final_score} "
            f"(amélioration {self.improvement}, soit {ratio_text})",
            f"  vecteur des critères : {self.initial_vector} -> {self.final_vector}",
            f"  mouvements : {self.moves_generated} générés, {self.moves_tested} testés "
            f"({self.moves_infeasible} infaisables), {self.moves_evaluated} évalués, "
            f"{self.moves_accepted} acceptés, {self.moves_rejected_by_validator} refusés "
            "par la validation",
            "  par voisinage (testés / évalués / acceptés / gain) :",
        ]
        for move_type, c in self.per_type.items():
            lines.append(
                f"    {move_type.value} : {c.tested} / {c.evaluated} / {c.accepted} / {c.total_gain}"
            )
        return "\n".join(lines)