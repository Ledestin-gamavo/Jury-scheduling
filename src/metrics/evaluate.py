"""Évaluation globale d'une solution : vecteur des cinq critères.

Ce module fournit :

* :class:`EvaluationResult` : résultat immuable (les cinq critères, le détail
  par enseignant, le détail du critère 4 par phase et le ``total_score``) ;
* :class:`SolutionEvaluator` : calcule l'ensemble des critères en partageant le
  calcul de présence des enseignants entre les trois métriques qui en dépendent ;
* :func:`evaluate_solution` : raccourci fonctionnel.

Les cinq critères, tous à minimiser et rapportés dans l'ordre du contrat, sont
listés dans :data:`METRIC_NAMES`.

**Précondition.** Les métriques ne sont définies que pour des solutions
**valides** (contrat v4.0). Ce module ne valide pas : l'appelant doit avoir
vérifié la solution avec le module ``validation`` (la règle de dépendance
``metrics -> core`` interdit d'importer ``validation`` ici). Un solveur ou le
banc d'essai procède ainsi : valider, puis évaluer seulement si la solution est
valide.

**À propos du ``total_score``.** Le contrat n'impose aucune pondération : les
résultats doivent être rapportés comme un **vecteur**, et la stratégie de
scalarisation (ou l'approche Pareto) doit être justifiée par l'équipe. Le
``total_score`` est une scalarisation de **convenance** : somme pondérée des
cinq critères, avec des poids égaux à 1 par défaut (somme simple). Les critères
n'ayant pas la même échelle ni la même unité, cette somme n'a pas de
signification institutionnelle. Elle sert à comparer rapidement des candidats
(par exemple dans une recherche locale). Pour comparer des solutions de façon
plus rigoureuse, utiliser :meth:`EvaluationResult.as_vector` et
:meth:`EvaluationResult.dominates`.

Les évaluations ne modifient jamais l'instance ni la solution.

Dépend uniquement de ``core`` et des autres modules de ``metrics``.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .distinct_jury_pairs import distinct_jury_pairs
from .supervisor_group_breaks import supervisor_group_breaks_by_phase
from .teacher_idle_slots import teacher_idle_slots
from .teacher_load_range import teacher_load_range, teacher_session_counts
from .teacher_presence_days import teacher_attendance, teacher_presence_days

__all__ = [
    "METRIC_NAMES",
    "DEFAULT_WEIGHTS",
    "EvaluationResult",
    "SolutionEvaluator",
    "evaluate_solution",
]

METRIC_NAMES: tuple[str, ...] = (
    "teacher_presence_days",
    "teacher_idle_slots",
    "teacher_load_range",
    "supervisor_group_breaks",
    "distinct_jury_pairs",
)
"""Noms des cinq critères, dans l'ordre du contrat."""

DEFAULT_WEIGHTS: Mapping[str, int] = {name: 1 for name in METRIC_NAMES}
"""Poids par défaut du ``total_score`` : somme simple (tous égaux à 1)."""


@dataclass(frozen=True)
class EvaluationResult:
    """Résultat immuable de l'évaluation d'une solution valide.

    Attributes:
        instance_id: Identifiant de l'instance évaluée.
        teacher_presence_days: Critère 1.
        teacher_idle_slots: Critère 2.
        teacher_load_range: Critère 3.
        supervisor_group_breaks: Critère 4 (somme des deux phases).
        distinct_jury_pairs: Critère 5.
        total_score: Somme pondérée des cinq critères (voir la documentation du
            module : scalarisation de convenance).
        teacher_session_counts: Charge de chaque enseignant, sous forme de couples
            ``(identifiant, nombre de séances)`` dans l'ordre de l'instance
            (transparence du critère 3).
        supervisor_group_breaks_online: Contribution des pré-soutenances au critère 4.
        supervisor_group_breaks_final: Contribution des finales au critère 4.
        weights: Poids utilisés pour ``total_score``, sous forme de couples
            ``(nom du critère, poids)`` dans l'ordre du contrat.
    """

    instance_id: str
    teacher_presence_days: int
    teacher_idle_slots: int
    teacher_load_range: int
    supervisor_group_breaks: int
    distinct_jury_pairs: int
    total_score: int | float
    teacher_session_counts: tuple[tuple[str, int], ...] = ()
    supervisor_group_breaks_online: int = 0
    supervisor_group_breaks_final: int = 0
    weights: tuple[tuple[str, int | float], ...] = tuple(DEFAULT_WEIGHTS.items())

    def as_vector(self) -> tuple[int, int, int, int, int]:
        """Retourne les cinq critères dans l'ordre du contrat.

        C'est la forme de référence pour rapporter un résultat et pour comparer
        des solutions (tous les critères sont à minimiser).
        """
        return (
            self.teacher_presence_days,
            self.teacher_idle_slots,
            self.teacher_load_range,
            self.supervisor_group_breaks,
            self.distinct_jury_pairs,
        )

    def session_counts_dict(self) -> dict[str, int]:
        """Retourne la charge par enseignant sous forme de dictionnaire."""
        return dict(self.teacher_session_counts)

    def dominates(self, other: EvaluationResult) -> bool:
        """Indique si ce résultat domine ``other`` au sens de Pareto.

        Un résultat domine un autre s'il est **au moins aussi bon** sur les cinq
        critères et **strictement meilleur** sur au moins un (minimisation).

        Args:
            other: Résultat à comparer.
        """
        mine, theirs = self.as_vector(), other.as_vector()
        return all(a <= b for a, b in zip(mine, theirs)) and any(
            a < b for a, b in zip(mine, theirs)
        )

    def as_dict(self) -> dict[str, Any]:
        """Retourne le résultat sous forme de dictionnaire de types simples.

        Utile pour une ligne de benchmark, un export JSON ou un rapport. Les
        clés sont les noms de :data:`METRIC_NAMES`, suivis de ``total_score``
        et des détails.
        """
        return {
            "instance_id": self.instance_id,
            **dict(zip(METRIC_NAMES, self.as_vector())),
            "total_score": self.total_score,
            "teacher_session_counts": self.session_counts_dict(),
            "supervisor_group_breaks_online": self.supervisor_group_breaks_online,
            "supervisor_group_breaks_final": self.supervisor_group_breaks_final,
            "weights": dict(self.weights),
        }

    def to_text(self) -> str:
        """Retourne un rapport texte lisible (en français) du résultat."""
        lines = [f"Évaluation de l'instance {self.instance_id} (tous les critères sont à minimiser) :"]
        for name, value in zip(METRIC_NAMES, self.as_vector()):
            lines.append(f"  {name} : {value}")
        lines.append(
            f"  (détail supervisor_group_breaks : pré-soutenances "
            f"{self.supervisor_group_breaks_online}, finales {self.supervisor_group_breaks_final})"
        )
        lines.append(f"  total_score (somme pondérée de convenance) : {self.total_score}")
        return "\n".join(lines)


def _normalize_weights(weights: Mapping[str, int | float] | None) -> dict[str, int | float]:
    """Valide et complète les poids du ``total_score``.

    Les critères absents de ``weights`` reçoivent le poids par défaut (1).

    Raises:
        ValueError: Si une clé est inconnue ou si un poids n'est pas un nombre
            réel fini positif ou nul.
    """
    normalized: dict[str, int | float] = dict(DEFAULT_WEIGHTS)
    if weights is None:
        return normalized
    for name, weight in weights.items():
        if name not in DEFAULT_WEIGHTS:
            raise ValueError(
                f"Critère inconnu dans les poids : {name!r} (attendus : {', '.join(METRIC_NAMES)})"
            )
        if isinstance(weight, bool) or not isinstance(weight, Real):
            raise ValueError(f"Poids de {name!r} : nombre attendu, reçu {weight!r}")
        if not weight >= 0 or weight == float("inf"):
            raise ValueError(f"Poids de {name!r} : doit être fini et >= 0, reçu {weight!r}")
        normalized[name] = weight
    return normalized


class SolutionEvaluator:
    """Calcule le vecteur des cinq critères d'une solution valide.

    L'évaluateur est sans état (hors poids) : une même instance peut être
    réutilisée pour de nombreuses évaluations, y compris depuis plusieurs
    solveurs. Il ne modifie jamais l'instance ni la solution.

    La solution doit être **valide** (voir la documentation du module).

    Exemple ::

        evaluator = SolutionEvaluator()
        result = evaluator.evaluate(instance, solution)
        result.as_vector()
        result.total_score

        # Poids personnalisés pour la scalarisation
        evaluator = SolutionEvaluator(weights={"teacher_load_range": 5})

    Args:
        weights: Poids du ``total_score`` par critère (facultatif). Les critères
            absents gardent le poids 1.

    Raises:
        ValueError: Si un nom de critère est inconnu ou un poids invalide.
    """

    def __init__(self, weights: Mapping[str, int | float] | None = None) -> None:
        self._weights: dict[str, int | float] = _normalize_weights(weights)

    @property
    def weights(self) -> dict[str, int | float]:
        """Poids utilisés pour le ``total_score`` (copie)."""
        return dict(self._weights)

    def total_score(self, vector: Sequence[int | float]) -> int | float:
        """Calcule la somme pondérée d'un vecteur de cinq critères.

        Args:
            vector: Valeurs des cinq critères, dans l'ordre de :data:`METRIC_NAMES`.

        Returns:
            La somme pondérée.

        Raises:
            ValueError: Si le vecteur n'a pas cinq composantes.
        """
        if len(vector) != len(METRIC_NAMES):
            raise ValueError(
                f"Vecteur de {len(METRIC_NAMES)} critères attendu, reçu {len(vector)}"
            )
        return sum(self._weights[name] * value for name, value in zip(METRIC_NAMES, vector))

    def evaluate(
        self, instance: Instance, solution: Solution | Sequence[Session]
    ) -> EvaluationResult:
        """Évalue une solution valide.

        Args:
            instance: Instance du problème.
            solution: Solution **valide** (ou séquence de séances).

        Returns:
            Le résultat d'évaluation.

        Raises:
            MetricsInputError: Si une séance référence un enseignant ou un
                étudiant inconnu (solution invalide).
        """
        attendance = teacher_attendance(instance, solution)
        by_phase = supervisor_group_breaks_by_phase(instance, solution)
        online = by_phase[Phase.PREDEFENCE]
        final = by_phase[Phase.FINAL]

        vector = (
            teacher_presence_days(instance, solution, attendance=attendance),
            teacher_idle_slots(instance, solution, attendance=attendance),
            teacher_load_range(instance, solution, attendance=attendance),
            online + final,
            distinct_jury_pairs(instance, solution),
        )
        counts = teacher_session_counts(instance, solution, attendance=attendance)
        return EvaluationResult(
            instance_id=instance.instance_id,
            teacher_presence_days=vector[0],
            teacher_idle_slots=vector[1],
            teacher_load_range=vector[2],
            supervisor_group_breaks=vector[3],
            distinct_jury_pairs=vector[4],
            total_score=self.total_score(vector),
            teacher_session_counts=tuple(counts.items()),
            supervisor_group_breaks_online=online,
            supervisor_group_breaks_final=final,
            weights=tuple((name, self._weights[name]) for name in METRIC_NAMES),
        )


def evaluate_solution(
    instance: Instance,
    solution: Solution | Sequence[Session],
    *,
    weights: Mapping[str, int | float] | None = None,
) -> EvaluationResult:
    """Raccourci : évalue une solution avec un :class:`SolutionEvaluator` temporaire.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).
        weights: Poids du ``total_score`` (facultatif).

    Returns:
        Le résultat d'évaluation.
    """
    return SolutionEvaluator(weights).evaluate(instance, solution)