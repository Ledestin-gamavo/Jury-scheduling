"""Contraintes de plafonds journaliers.

Règles du contrat :

* le plafond ``max_sessions_per_day`` d'un **enseignant** compte les séances
  auxquelles il participe, **toutes phases confondues** (pré-soutenance et
  finale), quel que soit son rôle (président, examinateur, encadrant en
  finale) ;
* le plafond ``max_sessions_per_day`` d'une **salle** ne compte que les
  **finales** qui s'y tiennent.

Une personne n'est comptée qu'une fois par séance, même si elle y cumule
plusieurs rôles. Les références inconnues sont ignorées (signalées ailleurs).

Codes d'erreur : ``CAPACITY_TEACHER``, ``CAPACITY_ROOM``.
"""

from __future__ import annotations
from collections import Counter
from collections.abc import Sequence
from core.enums import Phase
from core.instance import Instance
from core.session import Session
from .availability_constraints import attending_teachers

__all__ = [
    "CODE_TEACHER_CAPACITY",
    "CODE_ROOM_CAPACITY",
    "check_teacher_capacity",
    "check_room_capacity",
    "check_capacity",
]

CODE_TEACHER_CAPACITY = "CAPACITY_TEACHER"
"""Code d'erreur : plafond journalier d'un enseignant dépassé."""
CODE_ROOM_CAPACITY = "CAPACITY_ROOM"
"""Code d'erreur : plafond journalier d'une salle dépassé."""


def check_teacher_capacity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie le plafond journalier de séances de chaque enseignant.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (enseignant, jour) dépassant son plafond.
    """
    counts: Counter[tuple[str, int]] = Counter()
    for session in sessions:
        for teacher_id in attending_teachers(instance, session):
            counts[(teacher_id, session.day)] += 1
    errors: list[str] = []
    for teacher_id, day in sorted(counts):
        count = counts[(teacher_id, day)]
        limit = instance.teacher(teacher_id).max_sessions_per_day
        if count > limit:
            errors.append(
                f"[{CODE_TEACHER_CAPACITY}] Enseignant {teacher_id!r} : {count} séances "
                f"le jour {day} pour un plafond de {limit}"
            )
    return errors


def check_room_capacity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie le plafond journalier de finales de chaque salle.

    Seules les finales affectées à une salle connue sont comptées : les
    pré-soutenances en ligne ne comptent pas dans le plafond d'une salle.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (salle, jour) dépassant son plafond.
    """
    counts: Counter[tuple[str, int]] = Counter()
    for session in sessions:
        room_id = session.room_id
        if (
            session.phase is Phase.FINAL
            and isinstance(room_id, str)
            and instance.has_room(room_id)
        ):
            counts[(room_id, session.day)] += 1
    errors: list[str] = []
    for room_id, day in sorted(counts):
        count = counts[(room_id, day)]
        limit = instance.room(room_id).max_sessions_per_day
        if count > limit:
            errors.append(
                f"[{CODE_ROOM_CAPACITY}] Salle {room_id!r} : {count} finales le jour "
                f"{day} pour un plafond de {limit}"
            )
    return errors


def check_capacity(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie tous les plafonds journaliers (enseignants et salles).

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de plafond.
    """
    return [
        *check_teacher_capacity(instance, sessions),
        *check_room_capacity(instance, sessions),
    ]