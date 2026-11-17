"""Métrique 1 : ``teacher_presence_days``.

Définition (contrat v4.0) : somme, sur tous les enseignants, du nombre de jours
où l'enseignant participe à au moins une séance.

Participants considérés pour un enseignant :

* président et examinateur, à la pré-soutenance **et** à la finale ;
* encadrant-rapporteur de l'étudiant, **à la finale seulement** (le contrat ne
  l'impose pas à la pré-soutenance en ligne, et la métrique ne le compte donc
  pas à cette phase).

Hypothèses retenues :

* **H1.** Une personne est comptée une seule fois par séance, même si elle y
  cumule plusieurs rôles (le contrat interdit de compter les rôles comme des
  personnes séparées). Dans une solution valide, les trois membres d'une
  finale sont de toute façon distincts.
* **H2.** Les deux phases comptent : un enseignant présent le jour 1
  (pré-soutenance) et le jour 7 (finale) totalise 2 jours. Les périodes des
  phases étant disjointes, aucun jour n'est partagé entre les deux phases.
* **H3.** Un enseignant sans aucune séance contribue pour 0.

Ce module héberge aussi l'utilitaire partagé :func:`teacher_attendance`,
utilisé par les trois métriques liées aux enseignants, ainsi que
l'exception :class:`MetricsInputError`.

Dépend uniquement de ``core``.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence

from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution

__all__ = [
    "MetricsInputError",
    "as_session_sequence",
    "teacher_attendance",
    "teacher_presence_days",
]


class MetricsInputError(ValueError):
    """Entrée inexploitable pour le calcul d'une métrique.

    Levée lorsqu'une séance référence un enseignant ou un étudiant absent de
    l'instance : cela signale une solution invalide, pour laquelle le contrat
    ne définit pas de métriques.
    """


def as_session_sequence(solution: Solution | Sequence[Session]) -> Sequence[Session]:
    """Retourne la séquence de séances d'une solution ou d'une liste de séances.

    Permet d'évaluer une :class:`~core.solution.Solution` ou directement une
    liste de séances (par exemple un planning partiel pendant une résolution).
    La séquence retournée n'est jamais modifiée.

    Args:
        solution: Solution ou séquence de séances.

    Returns:
        Les séances, dans leur ordre d'origine.
    """
    if isinstance(solution, Solution):
        return solution.sessions
    return solution


def teacher_attendance(
    instance: Instance, solution: Solution | Sequence[Session]
) -> dict[str, tuple[Session, ...]]:
    """Retourne, pour chaque enseignant, les séances auxquelles il participe.

    Le dictionnaire contient **tous** les enseignants de l'instance, dans son
    ordre, y compris ceux sans aucune séance (tuple vide) : c'est nécessaire à
    :func:`teacher_load_range.teacher_load_range`, qui considère les enseignants
    non utilisés.

    Participants d'une séance : président, examinateur et, pour une finale,
    l'encadrant de l'étudiant. Chaque personne n'apparaît qu'une fois par
    séance (hypothèse H1).

    Args:
        instance: Instance du problème.
        solution: Solution (ou séquence de séances) à analyser.

    Returns:
        Table ``identifiant d'enseignant -> séances attendues`` (ordre d'apparition
        dans la solution).

    Raises:
        MetricsInputError: Si une séance référence un enseignant ou un étudiant
            inconnu.
    """
    attendance: dict[str, list[Session]] = {tid: [] for tid in instance.teacher_ids}
    for session in as_session_sequence(solution):
        ids = [session.president_id, session.examiner_id]
        if session.phase is Phase.FINAL:
            if not instance.has_student(session.student_id):
                raise MetricsInputError(
                    f"Étudiant inconnu {session.student_id!r} dans une finale : "
                    "les métriques exigent une solution valide"
                )
            ids.append(instance.student(session.student_id).supervisor_id)
        for teacher_id in dict.fromkeys(ids):
            if teacher_id not in attendance:
                raise MetricsInputError(
                    f"Enseignant inconnu {teacher_id!r} (étudiant {session.student_id!r}, "
                    f"phase {session.phase.value}) : les métriques exigent une solution valide"
                )
            attendance[teacher_id].append(session)
    return {tid: tuple(sessions) for tid, sessions in attendance.items()}


def teacher_presence_days(
    instance: Instance,
    solution: Solution | Sequence[Session],
    *,
    attendance: Mapping[str, Sequence[Session]] | None = None,
) -> int:
    """Calcule le nombre total de jours de présence des enseignants.

    Pour chaque enseignant, on compte les jours **distincts** où il participe à
    au moins une séance, puis on additionne sur tous les enseignants. Plus un
    enseignant est convoqué sur de nombreux jours, plus le score augmente.

    Exemple : T1 présent les jours 0, 0 et 3 (2 jours) et T2 le jour 3
    (1 jour) donnent un score de 3.

    Args:
        instance: Instance du problème.
        solution: Solution **valide** (ou séquence de séances).
        attendance: Résultat déjà calculé de :func:`teacher_attendance`
            (facultatif ; évite un recalcul lorsque plusieurs métriques sont
            évaluées).

    Returns:
        Le score (entier >= 0, à minimiser).

    Raises:
        MetricsInputError: Si une séance référence un enseignant ou un étudiant inconnu.
    """
    table = attendance if attendance is not None else teacher_attendance(instance, solution)
    return sum(len({session.day for session in sessions}) for sessions in table.values())