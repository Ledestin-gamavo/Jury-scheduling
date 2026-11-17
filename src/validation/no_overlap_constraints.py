"""Contraintes d'absence de chevauchement.

Chaque séance occupe exactement un créneau ``[slot, slot + 1)``. Deux séances
se chevauchent donc si et seulement si elles ont le **même jour et le même
créneau**. Règles du contrat :

* un enseignant ne peut pas participer à deux séances simultanées, y compris
  en ligne ; l'encadrant compte comme participant aux finales de ses étudiants ;
* un étudiant ne peut pas participer à deux séances simultanées ;
* une salle ne peut pas accueillir deux finales simultanées.

Des pré-soutenances en ligne dont les participants sont disjoints peuvent, elles,
se tenir en parallèle sans limite liée au nombre de salles : ce module n'impose
donc aucune contrainte sur les salles pour les pré-soutenances.

Une même personne n'est comptée qu'une fois dans une séance, même si elle y
cumule plusieurs rôles (voir :func:`validation.availability_constraints.attending_teachers`).
Les références inconnues sont ignorées (signalées ailleurs).

Codes d'erreur : ``OVERLAP_TEACHER``, ``OVERLAP_STUDENT``, ``OVERLAP_ROOM``.
"""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Sequence
from core.enums import Phase
from core.instance import Instance
from core.session import Session
from .availability_constraints import attending_teachers

__all__ = [
    "CODE_TEACHER_OVERLAP",
    "CODE_STUDENT_OVERLAP",
    "CODE_ROOM_OVERLAP",
    "check_teacher_no_overlap",
    "check_student_no_overlap",
    "check_room_no_overlap",
    "check_no_overlap",
]

CODE_TEACHER_OVERLAP = "OVERLAP_TEACHER"
"""Code d'erreur : un enseignant est présent dans deux séances simultanées."""
CODE_STUDENT_OVERLAP = "OVERLAP_STUDENT"
"""Code d'erreur : un étudiant est présent dans deux séances simultanées."""
CODE_ROOM_OVERLAP = "OVERLAP_ROOM"
"""Code d'erreur : une salle accueille deux finales simultanées."""


def _members(group: Sequence[Session]) -> str:
    """Décrit les séances en conflit sous la forme ``S01/final, S02/predefence``."""
    return ", ".join(sorted(f"{s.student_id}/{s.phase.value}" for s in group))


def check_teacher_no_overlap(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie qu'aucun enseignant n'est présent dans deux séances simultanées.

    Tous les rôles sont considérés (président, examinateur, encadrant en finale)
    et les deux phases.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (enseignant, jour, créneau) en conflit.
    """
    occupied: dict[tuple[str, int, int], list[Session]] = defaultdict(list)
    for session in sessions:
        for teacher_id in attending_teachers(instance, session):
            occupied[(teacher_id, session.day, session.slot)].append(session)
    errors: list[str] = []
    for teacher_id, day, slot in sorted(occupied):
        group = occupied[(teacher_id, day, slot)]
        if len(group) > 1:
            errors.append(
                f"[{CODE_TEACHER_OVERLAP}] Enseignant {teacher_id!r} présent dans "
                f"{len(group)} séances simultanées (jour {day}, créneau {slot}) : "
                f"{_members(group)}"
            )
    return errors


def check_student_no_overlap(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie qu'aucun étudiant n'est présent dans deux séances simultanées.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (étudiant, jour, créneau) en conflit.
    """
    occupied: dict[tuple[str, int, int], list[Session]] = defaultdict(list)
    for session in sessions:
        if instance.has_student(session.student_id):
            occupied[(session.student_id, session.day, session.slot)].append(session)
    errors: list[str] = []
    for student_id, day, slot in sorted(occupied):
        group = occupied[(student_id, day, slot)]
        if len(group) > 1:
            errors.append(
                f"[{CODE_STUDENT_OVERLAP}] Étudiant {student_id!r} présent dans "
                f"{len(group)} séances simultanées (jour {day}, créneau {slot}) : "
                f"{_members(group)}"
            )
    return errors


def check_room_no_overlap(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie qu'aucune salle n'accueille deux finales simultanées.

    Seules les finales affectées à une salle connue sont considérées.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (salle, jour, créneau) en conflit.
    """
    occupied: dict[tuple[str, int, int], list[Session]] = defaultdict(list)
    for session in sessions:
        room_id = session.room_id
        if (
            session.phase is Phase.FINAL
            and isinstance(room_id, str)
            and instance.has_room(room_id)
        ):
            occupied[(room_id, session.day, session.slot)].append(session)
    errors: list[str] = []
    for room_id, day, slot in sorted(occupied):
        group = occupied[(room_id, day, slot)]
        if len(group) > 1:
            errors.append(
                f"[{CODE_ROOM_OVERLAP}] Salle {room_id!r} utilisée par {len(group)} "
                f"finales simultanées (jour {day}, créneau {slot}) : {_members(group)}"
            )
    return errors


def check_no_overlap(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie toutes les contraintes d'absence de chevauchement.

    Regroupe :func:`check_teacher_no_overlap`, :func:`check_student_no_overlap`
    et :func:`check_room_no_overlap`.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de chevauchement.
    """
    return [
        *check_teacher_no_overlap(instance, sessions),
        *check_student_no_overlap(instance, sessions),
        *check_room_no_overlap(instance, sessions),
    ]