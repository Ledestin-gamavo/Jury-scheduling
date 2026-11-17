"""Métrique 2 : ``teacher_idle_slots``.

Définition (contrat v4.0) : pour chaque enseignant et chaque jour, nombre de
créneaux vides entre sa première et sa dernière séance du jour, soit
``dernier_créneau - premier_créneau + 1 - nombre_de_séances``. Les valeurs sont
additionnées sur tous les enseignants et tous les jours.

Exemple : un enseignant présent aux créneaux 1, 3 et 4 le même jour a
``4 - 1 + 1 - 3 = 1`` créneau creux (le créneau 2).

Hypothèses retenues :

* **H1.** Aucun trou « de nuit » : chaque jour est évalué indépendamment. Rien
  n'est compté entre le dernier créneau d'un jour et le premier du suivant.
* **H2.** Les deux phases comptent : les séances de pré-soutenance (en ligne) et
  de finale entrent dans le même calcul. Comme les périodes des phases sont
  disjointes, elles ne se partagent jamais le même jour.
* **H3.** L'encadrant compte comme présent aux finales de ses étudiants,
  conformément à la métrique 1.
* **H4.** Un enseignant n'ayant qu'une séance un jour, ou aucune, contribue
  pour 0.
* **H5.** Le nombre de séances d'un enseignant un jour est le nombre de créneaux
  **distincts** qu'il occupe. Dans une solution valide, un enseignant ne
  participe jamais à deux séances simultanées : c'est identique à la formule du
  contrat, mais le résultat reste positif ou nul même si la précondition de
  validité n'est pas respectée.

Dépend uniquement de ``core`` et de :mod:`metrics.teacher_presence_days`.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence

from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .teacher_presence_days import teacher_attendance

__all__ = ["teacher_idle_slots"]


def teacher_idle_slots(
    instance: Instance,
    solution: Solution | Sequence[Session],
    *,
    attendance: Mapping[str, Sequence[Session]] | None = None,
) -> int:
    """Calcule le nombre total de créneaux creux des enseignants.

    Pour chaque enseignant et chaque jour où il a au moins une séance, on
    additionne les créneaux libres compris entre sa première et sa dernière
    séance du jour.

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
    table = attendance if attendance is not None else teacher_attendance(instance, solution)
    total = 0
    for sessions in table.values():
        slots_by_day: dict[int, set[int]] = {}
        for session in sessions:
            slots_by_day.setdefault(session.day, set()).add(session.slot)
        for slots in slots_by_day.values():
            total += max(slots) - min(slots) + 1 - len(slots)
    return total