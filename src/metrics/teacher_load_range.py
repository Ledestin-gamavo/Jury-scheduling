"""Métrique 3 : ``teacher_load_range``.

Définition (contrat v4.0) : charge maximale moins charge minimale des
enseignants, où la **charge** d'un enseignant est le nombre de séances
auxquelles il participe. L'objectif est d'équilibrer la charge.

Hypothèses retenues :

* **H1.** La charge compte les séances des **deux phases** (pré-soutenance et
  finale), quel que soit le rôle (président, examinateur, encadrant-rapporteur
  en finale). Chaque séance compte pour 1 par personne (une personne n'est pas
  comptée plusieurs fois dans une même séance).
* **H2.** Le minimum et le maximum portent sur **tous** les enseignants listés
  dans l'instance, y compris ceux qui n'ont aucune séance (charge 0). Laisser un
  enseignant inutilisé fait donc monter l'écart.
* **H3.** Les comptes par enseignant sont exposés par
  :func:`teacher_session_counts`, pour la transparence demandée par le contrat.
* **H4.** Une instance sans enseignant donnerait 0 (cas dégénéré, interdit par
  le contrat qui impose une liste non vide).

Dépend uniquement de ``core`` et de :mod:`metrics.teacher_presence_days`.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence

from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .teacher_presence_days import teacher_attendance

__all__ = ["teacher_session_counts", "teacher_load_range"]


def teacher_session_counts(
    instance: Instance,
    solution: Solution | Sequence[Session],
    *,
    attendance: Mapping[str, Sequence[Session]] | None = None,
) -> dict[str, int]:
    """Retourne le nombre de séances de chaque enseignant.

    Le dictionnaire contient **tous** les enseignants de l'instance, dans son
    ordre, avec 0 pour ceux qui n'ont aucune séance.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).
        attendance: Résultat déjà calculé de
            :func:`metrics.teacher_presence_days.teacher_attendance` (facultatif).

    Returns:
        Table ``identifiant d'enseignant -> nombre de séances``.

    Raises:
        MetricsInputError: Si une séance référence un enseignant ou un étudiant inconnu.
    """
    table = attendance if attendance is not None else teacher_attendance(instance, solution)
    return {teacher_id: len(sessions) for teacher_id, sessions in table.items()}


def teacher_load_range(
    instance: Instance,
    solution: Solution | Sequence[Session],
    *,
    attendance: Mapping[str, Sequence[Session]] | None = None,
) -> int:
    """Calcule l'écart entre la charge maximale et la charge minimale.

    Exemple : charges ``{T1: 5, T2: 2, T3: 0}`` donnent ``5 - 0 = 5`` (T3 est
    comptée même si elle n'est pas utilisée).

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).
        attendance: Résultat déjà calculé de
            :func:`metrics.teacher_presence_days.teacher_attendance` (facultatif).

    Returns:
        Le score (entier >= 0, à minimiser).

    Raises:
        MetricsInputError: Si une séance référence un enseignant ou un étudiant inconnu.
    """
    counts = teacher_session_counts(instance, solution, attendance=attendance)
    if not counts:
        return 0
    values = counts.values()
    return max(values) - min(values)