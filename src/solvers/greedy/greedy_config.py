"""Configuration centralisée du ``GreedySolver``.

Tous les paramètres du solveur glouton sont regroupés dans l'objet immuable
:class:`GreedyConfig`. Les quatre paramètres demandés sont ``random_seed``,
``use_candidate_ordering``, ``use_repair`` et ``max_repair_iterations``. Sept
paramètres complémentaires, tous dotés de valeurs par défaut, rendent le
guidage glouton réglable sans toucher au code.

Les poids ``weight_*`` pondèrent les termes du **coût estimé** d'un choix. Ils
reproduisent, de façon incrémentale et locale, les critères du contrat :

* ``weight_new_jury_pair`` : coût d'un binôme encore jamais utilisé
  (critère ``distinct_jury_pairs``) ;
* ``weight_teacher_load`` : coût par séance déjà portée par les deux membres du
  binôme (équilibrage, critère ``teacher_load_range``) ;
* ``weight_presence_days`` : coût d'un enseignant convoqué un nouveau jour
  (critère ``teacher_presence_days``) ;
* ``weight_idle_slots`` : coût d'un créneau creux ajouté (critère
  ``teacher_idle_slots``) ;
* ``weight_group_breaks`` : coût d'une rupture de groupe d'encadrant ajoutée
  (critère ``supervisor_group_breaks``).

Ces valeurs par défaut sont des choix heuristiques raisonnables, non des
valeurs imposées par le contrat (qui n'impose aucune pondération). Elles se
règlent par expérimentation.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any

__all__ = ["GreedyConfig"]

_WEIGHT_FIELDS: tuple[str, ...] = (
    "weight_new_jury_pair",
    "weight_teacher_load",
    "weight_presence_days",
    "weight_idle_slots",
    "weight_group_breaks",
)
_FLAG_FIELDS: tuple[str, ...] = (
    "use_candidate_ordering",
    "use_repair",
    "use_mrv_ordering",
)
_COUNT_FIELDS: tuple[str, ...] = ("max_repair_iterations", "repair_eviction_size")


@dataclass(frozen=True)
class GreedyConfig:
    """Paramètres du ``GreedySolver`` (objet immuable et validé).

    Attributes:
        random_seed: Graine du générateur pseudo-aléatoire. Elle départage les
            choix de coût égal et pilote les évictions de la réparation. À
            graine, configuration et instance identiques, le résultat est
            identique.
        use_candidate_ordering: Si vrai, les binômes, créneaux et salles sont
            **classés** par coût estimé. Si faux, le premier candidat faisable
            dans l'ordre naturel de l'instance est retenu (*first-fit*).
        use_repair: Si vrai, une réparation locale est tentée lorsque des
            étudiants ne sont pas placés.
        max_repair_iterations: Nombre maximal de tours d'éviction-réinsertion de
            la réparation (0 : réinsertion simple, sans éviction).
        use_mrv_ordering: Si vrai, les étudiants sont traités du plus contraint
            au moins contraint (*Minimum Remaining Values*). Si faux, ordre de
            l'instance.
        repair_eviction_size: Nombre d'étudiants déjà placés évincés, par
            étudiant non placé et par tour de réparation.
        weight_new_jury_pair: Poids d'un binôme jamais utilisé.
        weight_teacher_load: Poids de la charge cumulée des deux membres du binôme.
        weight_presence_days: Poids d'un nouveau jour de présence d'enseignant.
        weight_idle_slots: Poids d'un créneau creux supplémentaire.
        weight_group_breaks: Poids d'une rupture de groupe d'encadrant.

    Raises:
        ValueError: Si un paramètre a un type ou une valeur invalide.
    """

    random_seed: int = 0
    use_candidate_ordering: bool = True
    use_repair: bool = True
    max_repair_iterations: int = 50
    use_mrv_ordering: bool = True
    repair_eviction_size: int = 3
    weight_new_jury_pair: float = 3.0
    weight_teacher_load: float = 0.5
    weight_presence_days: float = 1.0
    weight_idle_slots: float = 1.0
    weight_group_breaks: float = 2.0

    def __post_init__(self) -> None:
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise ValueError(f"random_seed doit être un entier, reçu {self.random_seed!r}")
        for name in _FLAG_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, bool):
                raise ValueError(f"{name} doit être un booléen, reçu {value!r}")
        for name in _COUNT_FIELDS:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} doit être un entier >= 0, reçu {value!r}")
        for name in _WEIGHT_FIELDS:
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"{name} doit être un nombre fini >= 0, reçu {value!r}")

    def with_changes(self, **changes: Any) -> GreedyConfig:
        """Retourne une copie de la configuration avec des paramètres modifiés.

        Args:
            **changes: Paramètres à remplacer (noms des attributs).

        Returns:
            Une nouvelle configuration (l'originale n'est pas modifiée).

        Raises:
            TypeError: Si un nom de paramètre est inconnu.
            ValueError: Si une valeur est invalide.
        """
        return replace(self, **changes)

    def as_dict(self) -> dict[str, Any]:
        """Retourne la configuration sous forme de dictionnaire (traçabilité des expériences)."""
        return asdict(self)