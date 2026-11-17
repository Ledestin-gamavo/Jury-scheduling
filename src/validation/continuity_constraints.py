"""Contraintes de continuité du jury entre les deux phases.

Règle du contrat : le binôme président/examinateur choisi pour la
pré-soutenance d'un étudiant reste **identique** à sa finale. La continuité est
une contrainte dure pour les étudiants admissibles à la finale.

Une comparaison n'est possible que si l'étudiant possède **exactement une**
pré-soutenance et **exactement une** finale. Les cas de séance manquante, en
double ou interdite sont signalés par
:func:`validation.solution_validator.check_coverage` ; ils sont ignorés ici
pour éviter des messages redondants ou ambigus. Les étudiants non admissibles
et les étudiants inconnus sont également ignorés.

Codes d'erreur : ``CONTINUITY_PRESIDENT``, ``CONTINUITY_EXAMINER``.
"""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Sequence
from core.enums import Phase
from core.instance import Instance
from core.session import Session

__all__ = [
    "CODE_PRESIDENT_CONTINUITY",
    "CODE_EXAMINER_CONTINUITY",
    "check_president_continuity",
    "check_examiner_continuity",
    "check_continuity",
]

CODE_PRESIDENT_CONTINUITY = "CONTINUITY_PRESIDENT"
"""Code d'erreur : le président diffère entre pré-soutenance et finale."""
CODE_EXAMINER_CONTINUITY = "CONTINUITY_EXAMINER"
"""Code d'erreur : l'examinateur diffère entre pré-soutenance et finale."""


def _paired_sessions(
    instance: Instance, sessions: Sequence[Session]
) -> list[tuple[str, Session, Session]]:
    """Retourne les couples (pré-soutenance, finale) comparables.

    Un étudiant est retenu s'il est connu, admissible à la finale, et possède
    exactement une séance par phase.

    Args:
        instance: Instance du problème.
        sessions: Séances à analyser.

    Returns:
        Triplets ``(student_id, pré-soutenance, finale)``, dans l'ordre des
        étudiants de l'instance.
    """
    by_phase: dict[Phase, dict[str, list[Session]]] = {
        Phase.PREDEFENCE: defaultdict(list),
        Phase.FINAL: defaultdict(list),
    }
    for session in sessions:
        by_phase[session.phase][session.student_id].append(session)

    pairs: list[tuple[str, Session, Session]] = []
    for student in instance.students:
        if not student.eligible_final:
            continue
        predefences = by_phase[Phase.PREDEFENCE].get(student.id, [])
        finals = by_phase[Phase.FINAL].get(student.id, [])
        if len(predefences) == 1 and len(finals) == 1:
            pairs.append((student.id, predefences[0], finals[0]))
    return pairs


def check_president_continuity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que le président est le même en pré-soutenance et en finale.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par étudiant dont le président change entre les phases.
    """
    return [
        f"[{CODE_PRESIDENT_CONTINUITY}] Étudiant {student_id!r} : président "
        f"{predefence.president_id!r} en pré-soutenance mais {final.president_id!r} en finale"
        for student_id, predefence, final in _paired_sessions(instance, sessions)
        if predefence.president_id != final.president_id
    ]


def check_examiner_continuity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que l'examinateur est le même en pré-soutenance et en finale.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par étudiant dont l'examinateur change entre les phases.
    """
    return [
        f"[{CODE_EXAMINER_CONTINUITY}] Étudiant {student_id!r} : examinateur "
        f"{predefence.examiner_id!r} en pré-soutenance mais {final.examiner_id!r} en finale"
        for student_id, predefence, final in _paired_sessions(instance, sessions)
        if predefence.examiner_id != final.examiner_id
    ]


def check_continuity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la continuité complète du binôme président/examinateur.

    Regroupe :func:`check_president_continuity` et :func:`check_examiner_continuity`.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de continuité.
    """
    return [
        *check_president_continuity(instance, sessions),
        *check_examiner_continuity(instance, sessions),
    ]