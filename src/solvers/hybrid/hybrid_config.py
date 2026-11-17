"""Configuration du solveur hybride."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from solvers.cpsat import CPSATConfig
from solvers.greedy import GreedyConfig
from solvers.local_search import LocalSearchConfig


@dataclass(frozen=True)
class HybridConfig:
    """Paramètres immuables du pipeline Greedy → Local Search → CP-SAT.

    Attributes:
        run_greedy: Exécute la construction gloutonne. Si désactivé, une
            solution initiale valide doit être fournie à ``solve_with_report``.
        run_local_search: Exécute l'amélioration locale.
        run_cpsat: Exécute l'optimisation CP-SAT.
        enable_warm_start: Transmet l'incumbent valide au CP-SAT.
        local_search_time_limit: Limite locale en secondes ; ``None`` conserve
            celle de ``local_search_config``.
        cpsat_time_limit: Limite CP-SAT en secondes ; ``None`` conserve celle
            de ``cpsat_config``.
        greedy_config: Configuration du solveur Greedy.
        local_search_config: Configuration du solveur Local Search.
        cpsat_config: Configuration du solveur CP-SAT.
    """

    run_greedy: bool = True
    run_local_search: bool = True
    run_cpsat: bool = True
    enable_warm_start: bool = True
    local_search_time_limit: float | None = None
    cpsat_time_limit: float | None = None
    greedy_config: GreedyConfig = field(default_factory=GreedyConfig)
    local_search_config: LocalSearchConfig = field(default_factory=LocalSearchConfig)
    cpsat_config: CPSATConfig = field(default_factory=CPSATConfig)

    def __post_init__(self) -> None:
        """Vérifie les options et les limites de temps."""
        for name in ("run_greedy", "run_local_search", "run_cpsat", "enable_warm_start"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} doit être un booléen.")
        for name in ("local_search_time_limit", "cpsat_time_limit"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} doit être None ou un nombre fini strictement positif.")
        if not isinstance(self.greedy_config, GreedyConfig):
            raise TypeError("greedy_config doit être une instance de GreedyConfig.")
        if not isinstance(self.local_search_config, LocalSearchConfig):
            raise TypeError("local_search_config doit être une instance de LocalSearchConfig.")
        if not isinstance(self.cpsat_config, CPSATConfig):
            raise TypeError("cpsat_config doit être une instance de CPSATConfig.")
