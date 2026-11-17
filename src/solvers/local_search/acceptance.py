"""Politique d'acceptation : première ou meilleure amélioration.

Ce module définit :

* :class:`ImprovementStrategy` : les deux stratégies de *hill climbing* ;
* :class:`AcceptancePolicy` : la règle de comparaison de deux scores ;
* :class:`MoveSelection` : l'objet qui, pendant le parcours des voisins d'une
  itération, retient le mouvement à accepter.

Stratégies :

* **First Improvement** (par défaut) : le parcours s'arrête au **premier**
  voisin strictement meilleur. Peu coûteux par itération, adapté aux voisinages
  vastes et à l'évaluation complète de chaque voisin.
* **Best Improvement** : tous les voisins générés sont évalués et le
  **meilleur** est retenu. Plus coûteux, mais chaque pas est le meilleur de
  l'échantillon.

Dans les deux cas, un voisin n'est accepté que s'il est **strictement** meilleur
que la solution courante (d'au moins ``min_improvement``). Les mouvements de
même score (plateaux) sont refusés : ce n'est donc pas une marche aléatoire.
Le critère comparé est ``EvaluationResult.total_score``, à **minimiser**. Le
module ne choisit pas les poids.

En cas d'égalité entre deux voisins améliorants (Best Improvement), le premier
rencontré est conservé : le choix est déterministe pour un ordre de parcours donné.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from metrics import EvaluationResult

from .move_operator import Move

__all__ = ["ImprovementStrategy", "AcceptancePolicy", "MoveSelection"]


class ImprovementStrategy(str, Enum):
    """Stratégie d'acceptation du *hill climbing*.

    Attributes:
        FIRST_IMPROVEMENT: Accepter le premier voisin strictement meilleur.
        BEST_IMPROVEMENT: Accepter le meilleur voisin de l'itération.
    """

    FIRST_IMPROVEMENT = "first_improvement"
    BEST_IMPROVEMENT = "best_improvement"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AcceptancePolicy:
    """Règle d'acceptation d'un voisin.

    Attributes:
        strategy: Première ou meilleure amélioration.
        min_improvement: Gain minimal du score total pour qu'un voisin soit
            jugé améliorant.

    Raises:
        ValueError: Si ``min_improvement`` n'est pas un nombre fini positif ou nul.
    """

    strategy: ImprovementStrategy = ImprovementStrategy.FIRST_IMPROVEMENT
    min_improvement: float = 1e-9

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy", ImprovementStrategy(self.strategy))
        gain = self.min_improvement
        if (
            isinstance(gain, bool)
            or not isinstance(gain, (int, float))
            or not math.isfinite(gain)
            or gain < 0
        ):
            raise ValueError(f"min_improvement doit être un nombre fini >= 0, reçu {gain!r}")

    @property
    def stops_on_first_improvement(self) -> bool:
        """Vrai si le parcours des voisins s'arrête au premier voisin améliorant."""
        return self.strategy is ImprovementStrategy.FIRST_IMPROVEMENT

    def is_improvement(self, current_score: float, candidate_score: float) -> bool:
        """Indique si le score du voisin est strictement meilleur (plus petit).

        Args:
            current_score: Score total de la solution courante.
            candidate_score: Score total du voisin.
        """
        return candidate_score < current_score - self.min_improvement

    def new_selection(self, reference_score: float) -> MoveSelection:
        """Crée la sélection d'une itération.

        Args:
            reference_score: Score total de la solution courante.
        """
        return MoveSelection(self, reference_score)


class MoveSelection:
    """Retient le mouvement à accepter pendant le parcours des voisins d'une itération.

    Utilisation : appeler :meth:`offer` pour chaque voisin faisable évalué, et
    arrêter le parcours dès que l'appel retourne ``True``.

    Args:
        policy: Politique d'acceptation.
        reference_score: Score total de la solution courante.
    """

    def __init__(self, policy: AcceptancePolicy, reference_score: float) -> None:
        self._policy = policy
        self._reference = reference_score
        self._best_move: Move | None = None
        self._best_evaluation: EvaluationResult | None = None
        self._improving_offered = 0

    @property
    def best_move(self) -> Move | None:
        """Mouvement retenu, ou ``None`` si aucun voisin n'est améliorant."""
        return self._best_move

    @property
    def best_evaluation(self) -> EvaluationResult | None:
        """Évaluation de la solution après le mouvement retenu."""
        return self._best_evaluation

    @property
    def best_score(self) -> float | None:
        """Score total après le mouvement retenu."""
        return None if self._best_evaluation is None else self._best_evaluation.total_score

    @property
    def gain(self) -> float:
        """Gain du mouvement retenu (0 si aucun)."""
        score = self.best_score
        return 0.0 if score is None else self._reference - score

    @property
    def num_improving_offered(self) -> int:
        """Nombre de voisins améliorants proposés à cette sélection."""
        return self._improving_offered

    def offer(self, move: Move, evaluation: EvaluationResult) -> bool:
        """Propose un voisin faisable déjà évalué.

        Args:
            move: Mouvement évalué.
            evaluation: Évaluation de la solution obtenue après le mouvement.

        Returns:
            ``True`` si le parcours doit s'arrêter (première amélioration trouvée
            en stratégie *First Improvement*), ``False`` sinon.
        """
        score = evaluation.total_score
        if not self._policy.is_improvement(self._reference, score):
            return False
        self._improving_offered += 1
        best = self.best_score
        if best is None or score < best:
            self._best_move = move
            self._best_evaluation = evaluation
        return self._policy.stops_on_first_improvement