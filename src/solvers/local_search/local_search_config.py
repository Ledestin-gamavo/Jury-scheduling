"""Configuration centralisée du ``LocalSearchSolver``.

Tous les paramètres de la recherche locale sont regroupés dans l'objet immuable
:class:`LocalSearchConfig`.

Paramètres d'arrêt (au moins l'un d'eux borne toujours la recherche) :

* ``max_iterations`` : nombre maximal d'itérations. Une itération génère des
  voisins et accepte **au plus un** mouvement ;
* ``max_non_improving_iterations`` : nombre maximal d'itérations consécutives
  sans mouvement améliorant. Les voisins étant échantillonnés au hasard, une
  itération sans amélioration ne prouve pas un optimum local ; ce paramètre
  fixe la patience avant d'arrêter ;
* ``time_limit_seconds`` : limite de temps facultative.

Paramètres de voisinage (ils évitent toute explosion combinatoire) :

* ``enabled_neighborhoods`` : voisinages actifs ;
* ``max_moves_per_neighborhood`` : nombre maximal de mouvements générés par
  voisinage et par itération (``None`` : aucune limite) ;
* ``max_alternatives_per_session`` : nombre maximal d'alternatives essayées par
  séance, étudiant ou encadrant (``None`` : toutes).

Si les deux limites valent ``None``, la recherche est **exhaustive** : une
itération sans amélioration prouve alors un optimum local (propriété
:attr:`LocalSearchConfig.is_exhaustive`), au prix d'un temps de calcul élevé
sur les grandes instances.

Objectif : ``SolutionEvaluator.total_score``, somme pondérée des cinq critères du
contrat (poids ``weights``, tous égaux à 1 par défaut). Le contrat n'impose
aucune pondération ; c'est une scalarisation de convenance. Le vecteur des cinq
critères est toujours rapporté en plus par le solveur.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from metrics import METRIC_NAMES

from .acceptance import ImprovementStrategy
from .move_operator import MoveType

__all__ = ["DEFAULT_NEIGHBORHOODS", "LocalSearchConfig"]

DEFAULT_NEIGHBORHOODS: tuple[MoveType, ...] = tuple(MoveType)
"""Les cinq voisinages, dans l'ordre de :class:`MoveType`."""


def _check_int(name: str, value: Any, *, minimum: int) -> None:
    """Vérifie qu'un paramètre est un entier (non booléen) supérieur ou égal à ``minimum``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} doit être un entier >= {minimum}, reçu {value!r}")


def _check_optional_int(name: str, value: Any, *, minimum: int) -> None:
    """Comme :func:`_check_int`, mais ``None`` est accepté (sans limite)."""
    if value is not None:
        _check_int(name, value, minimum=minimum)


@dataclass(frozen=True)
class LocalSearchConfig:
    """Paramètres du ``LocalSearchSolver`` (objet immuable et validé).

    Attributes:
        random_seed: Graine du générateur pseudo-aléatoire (échantillonnage des
            voisins). À graine, configuration, instance et solution identiques,
            le résultat est identique.
        strategy: Stratégie d'acceptation : première ou meilleure amélioration.
        max_iterations: Nombre maximal d'itérations.
        max_non_improving_iterations: Nombre maximal d'itérations consécutives
            sans amélioration (>= 1).
        time_limit_seconds: Limite de temps en secondes (``None`` : aucune).
        enabled_neighborhoods: Voisinages actifs (non vide, sans doublon).
        max_moves_per_neighborhood: Mouvements générés au plus par voisinage et
            par itération (``None`` : aucune limite).
        max_alternatives_per_session: Alternatives au plus par séance
            (``None`` : toutes).
        shuffle_moves: Si vrai, les mouvements de tous les voisinages sont
            mélangés avant d'être testés, afin qu'aucun voisinage ne soit
            favorisé en première amélioration.
        validate_accepted_moves: Si vrai, chaque mouvement accepté est confirmé
            par un ``SolutionValidator`` complet (filet de sécurité).
        min_improvement: Gain minimal du score total pour qu'un voisin soit
            jugé améliorant (évite les égalités flottantes).
        weights: Poids du score total par critère (``None`` : tous égaux à 1).
            Les noms valides sont ceux de ``metrics.METRIC_NAMES``. Un objet
            contenant un dictionnaire n'est pas hachable ; il n'est pas destiné
            à servir de clé.

    Raises:
        ValueError: Si un paramètre a un type ou une valeur invalide.
    """

    random_seed: int = 0
    strategy: ImprovementStrategy = ImprovementStrategy.FIRST_IMPROVEMENT
    max_iterations: int = 500
    max_non_improving_iterations: int = 10
    time_limit_seconds: float | None = None
    enabled_neighborhoods: tuple[MoveType, ...] = DEFAULT_NEIGHBORHOODS
    max_moves_per_neighborhood: int | None = 40
    max_alternatives_per_session: int | None = 4
    shuffle_moves: bool = True
    validate_accepted_moves: bool = True
    min_improvement: float = 1e-9
    weights: Mapping[str, int | float] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ValueError(f"random_seed doit être un entier, reçu {self.random_seed!r}")
        object.__setattr__(self, "strategy", ImprovementStrategy(self.strategy))
        _check_int("max_iterations", self.max_iterations, minimum=0)
        _check_int("max_non_improving_iterations", self.max_non_improving_iterations, minimum=1)
        _check_optional_int("max_moves_per_neighborhood", self.max_moves_per_neighborhood, minimum=1)
        _check_optional_int(
            "max_alternatives_per_session", self.max_alternatives_per_session, minimum=1
        )

        limit = self.time_limit_seconds
        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, (int, float))
            or not math.isfinite(limit)
            or limit <= 0
        ):
            raise ValueError(f"time_limit_seconds doit être None ou un nombre > 0, reçu {limit!r}")

        neighborhoods = tuple(MoveType(item) for item in self.enabled_neighborhoods)
        if not neighborhoods:
            raise ValueError("enabled_neighborhoods ne peut pas être vide")
        if len(set(neighborhoods)) != len(neighborhoods):
            raise ValueError("enabled_neighborhoods contient des doublons")
        object.__setattr__(self, "enabled_neighborhoods", neighborhoods)

        for name in ("shuffle_moves", "validate_accepted_moves"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} doit être un booléen, reçu {getattr(self, name)!r}")

        gain = self.min_improvement
        if (
            isinstance(gain, bool)
            or not isinstance(gain, (int, float))
            or not math.isfinite(gain)
            or gain < 0
        ):
            raise ValueError(f"min_improvement doit être un nombre fini >= 0, reçu {gain!r}")

        if self.weights is not None:
            unknown = sorted(set(self.weights) - set(METRIC_NAMES))
            if unknown:
                raise ValueError(
                    f"Critères inconnus dans weights : {unknown} (attendus : {list(METRIC_NAMES)})"
                )
            object.__setattr__(self, "weights", dict(self.weights))

    @property
    def is_exhaustive(self) -> bool:
        """Vrai si aucune limite de voisinage n'est fixée (recherche exhaustive)."""
        return (
            self.max_moves_per_neighborhood is None and self.max_alternatives_per_session is None
        )

    def with_changes(self, **changes: Any) -> LocalSearchConfig:
        """Retourne une copie de la configuration avec des paramètres modifiés.

        Args:
            **changes: Paramètres à remplacer.

        Returns:
            Une nouvelle configuration (l'originale n'est pas modifiée).

        Raises:
            TypeError: Si un nom de paramètre est inconnu.
            ValueError: Si une valeur est invalide.
        """
        return replace(self, **changes)

    def as_dict(self) -> dict[str, Any]:
        """Retourne la configuration sous forme de dictionnaire de types simples.

        Utile pour tracer les paramètres d'une expérience (reproductibilité).
        """
        return {
            "random_seed": self.random_seed,
            "strategy": self.strategy.value,
            "max_iterations": self.max_iterations,
            "max_non_improving_iterations": self.max_non_improving_iterations,
            "time_limit_seconds": self.time_limit_seconds,
            "enabled_neighborhoods": [item.value for item in self.enabled_neighborhoods],
            "max_moves_per_neighborhood": self.max_moves_per_neighborhood,
            "max_alternatives_per_session": self.max_alternatives_per_session,
            "shuffle_moves": self.shuffle_moves,
            "validate_accepted_moves": self.validate_accepted_moves,
            "min_improvement": self.min_improvement,
            "weights": dict(self.weights) if self.weights is not None else None,
        }