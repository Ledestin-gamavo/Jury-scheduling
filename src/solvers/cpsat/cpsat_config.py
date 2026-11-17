"""Configuration du solveur d'optimisation CP-SAT."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping

from metrics.evaluate import DEFAULT_WEIGHTS, METRIC_NAMES


@dataclass(frozen=True)
class CPSATConfig:
    """Paramètres reproductibles de construction et de résolution CP-SAT.

    Les poids sont des entiers non négatifs, car CP-SAT optimise une expression
    linéaire entière. Les cinq poids absents conservent leur valeur par défaut.

    Attributes:
        random_seed: Graine utilisée par le moteur CP-SAT.
        time_limit_seconds: Limite de temps en secondes, ou ``None``.
        num_search_workers: Nombre de workers CP-SAT.
        relative_gap_limit: Gap relatif d'arrêt, ou ``None``.
        use_warm_start: Active les indications issues de la solution initiale.
        log_search_progress: Active les journaux détaillés du moteur.
        max_memory_mb: Limite mémoire en Mo, ou ``None``.
        objective_weights: Poids entiers des cinq métriques.
    """

    random_seed: int = 0
    time_limit_seconds: float | None = 60.0
    num_search_workers: int = 1
    relative_gap_limit: float | None = None
    use_warm_start: bool = True
    log_search_progress: bool = False
    max_memory_mb: int | None = None
    objective_weights: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def __post_init__(self) -> None:
        """Valide et normalise les paramètres immuables."""
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int) or self.random_seed < 0:
            raise ValueError("random_seed doit être un entier >= 0")
        if self.time_limit_seconds is not None and (
            isinstance(self.time_limit_seconds, bool)
            or not isinstance(self.time_limit_seconds, (int, float))
            or not isfinite(self.time_limit_seconds)
            or self.time_limit_seconds <= 0
        ):
            raise ValueError("time_limit_seconds doit être fini et strictement positif")
        if (isinstance(self.num_search_workers, bool)
                or not isinstance(self.num_search_workers, int)
                or self.num_search_workers < 1):
            raise ValueError("num_search_workers doit être un entier >= 1")
        if self.relative_gap_limit is not None and (
            isinstance(self.relative_gap_limit, bool)
            or not isinstance(self.relative_gap_limit, (int, float))
            or not isfinite(self.relative_gap_limit)
            or self.relative_gap_limit < 0
        ):
            raise ValueError("relative_gap_limit doit être fini et >= 0")
        if self.max_memory_mb is not None and (
            isinstance(self.max_memory_mb, bool)
            or not isinstance(self.max_memory_mb, int)
            or self.max_memory_mb < 1
        ):
            raise ValueError("max_memory_mb doit être un entier >= 1")
        if not isinstance(self.use_warm_start, bool) or not isinstance(self.log_search_progress, bool):
            raise ValueError("use_warm_start et log_search_progress doivent être booléens")
        weights = dict(DEFAULT_WEIGHTS)
        for name, value in self.objective_weights.items():
            if name not in METRIC_NAMES:
                raise ValueError(f"Métrique inconnue dans objective_weights : {name!r}")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"Le poids de {name!r} doit être un entier >= 0")
            weights[name] = value
        object.__setattr__(self, "objective_weights", weights)
