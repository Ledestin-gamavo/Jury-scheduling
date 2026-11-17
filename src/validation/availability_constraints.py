"""Contraintes de disponibilité.

Règle du contrat : le créneau occupé par une séance doit figurer dans les
disponibilités de **chaque participant** :

* l'étudiant ;
* le président et l'examinateur (pré-soutenance et finale) ;
* l'encadrant-rapporteur (finale uniquement) ;
* la salle (finale uniquement : aucune disponibilité de salle ne s'applique
  aux pré-soutenances en ligne).

Une disponibilité absente signifie une indisponibilité.

Ce module définit aussi deux utilitaires partagés par les autres modules de
validation : :func:`attending_teachers` et :func:`describe_session`.

Les références inconnues (étudiant, enseignant, salle absents de l'instance)
sont **ignorées silencieusement** ici : elles sont signalées par
:mod:`validation.role_constraints`, :mod:`validation.room_constraints` et
:mod:`validation.solution_validator`, ce qui évite les doublons de messages.

Codes d'erreur : ``AVAIL_TEACHER``, ``AVAIL_STUDENT``, ``AVAIL_ROOM``.
"""

from __future__ import annotations
from collections.abc import Sequence
from core.enums import Phase
from core.instance import Instance
from core.session import Session

__all__ = [
    "CODE_TEACHER_UNAVAILABLE",
    "CODE_STUDENT_UNAVAILABLE",
    "CODE_ROOM_UNAVAILABLE",
    "describe_session",
    "attending_teachers",
    "check_teacher_availability",
    "check_student_availability",
    "check_room_availability",
    "check_availability",
]

CODE_TEACHER_UNAVAILABLE = "AVAIL_TEACHER"
"""Code d'erreur : un enseignant participant est indisponible."""
CODE_STUDENT_UNAVAILABLE = "AVAIL_STUDENT"
"""Code d'erreur : l'étudiant est indisponible."""
CODE_ROOM_UNAVAILABLE = "AVAIL_ROOM"
"""Code d'erreur : la salle est indisponible."""


def describe_session(session: Session) -> str:
    """Décrit une séance en une chaîne lisible pour les messages d'erreur.

    Args:
        session: Séance à décrire.

    Returns:
        Une chaîne de la forme ``S01/final (jour 8, créneau 2)``.
    """
    return (
        f"{session.student_id}/{session.phase.value} "
        f"(jour {session.day}, créneau {session.slot})"
    )


def attending_teachers(instance: Instance, session: Session) -> tuple[str, ...]:
    """Retourne les enseignants **connus** participant à une séance.

    Participants : président, examinateur, et pour une finale l'encadrant de
    l'étudiant (rapporteur). Les identifiants sont dédoublonnés : une même
    personne n'est jamais comptée comme plusieurs participants. Les
    identifiants absents de l'instance sont écartés.

    Cette fonction réutilise :meth:`core.instance.Instance.attending_teacher_ids`
    et ne lève jamais d'exception pour une référence inconnue.

    Args:
        instance: Instance du problème.
        session: Séance considérée.

    Returns:
        Identifiants d'enseignants, dans l'ordre président, examinateur, encadrant.
    """
    if session.phase is Phase.FINAL and not instance.has_student(session.student_id):
        ids: tuple[str, ...] = tuple(dict.fromkeys((session.president_id, session.examiner_id)))
    else:
        ids = instance.attending_teacher_ids(session)
    return tuple(tid for tid in ids if instance.has_teacher(tid))


def _role_label(instance: Instance, session: Session, teacher_id: str) -> str:
    """Retourne le ou les rôles tenus par un enseignant dans une séance."""
    roles: list[str] = []
    if teacher_id == session.president_id:
        roles.append("président")
    if teacher_id == session.examiner_id:
        roles.append("examinateur")
    if (
        session.phase is Phase.FINAL
        and instance.has_student(session.student_id)
        and instance.student(session.student_id).supervisor_id == teacher_id
    ):
        roles.append("encadrant-rapporteur")
    return "/".join(roles)


def check_teacher_availability(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la disponibilité de tous les enseignants participants.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple (séance, enseignant indisponible).
    """
    errors: list[str] = []
    for session in sessions:
        for teacher_id in attending_teachers(instance, session):
            if not instance.teacher(teacher_id).is_available(session.day, session.slot):
                role = _role_label(instance, session, teacher_id)
                errors.append(
                    f"[{CODE_TEACHER_UNAVAILABLE}] Enseignant {teacher_id!r} ({role}) "
                    f"indisponible pour {describe_session(session)}"
                )
    return errors


def check_student_availability(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la disponibilité de l'étudiant de chaque séance.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance dont l'étudiant est indisponible.
    """
    errors: list[str] = []
    for session in sessions:
        if not instance.has_student(session.student_id):
            continue
        if not instance.student(session.student_id).is_available(session.day, session.slot):
            errors.append(
                f"[{CODE_STUDENT_UNAVAILABLE}] Étudiant {session.student_id!r} "
                f"indisponible pour {describe_session(session)}"
            )
    return errors


def check_room_availability(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la disponibilité des salles, pour les finales uniquement.

    Les pré-soutenances en ligne n'ont aucune contrainte de disponibilité de
    salle. Les salles inconnues ou absentes sont ignorées ici (voir
    :mod:`validation.room_constraints`).

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par finale placée dans une salle indisponible.
    """
    errors: list[str] = []
    for session in sessions:
        if session.phase is not Phase.FINAL:
            continue
        room_id = session.room_id
        if not isinstance(room_id, str) or not instance.has_room(room_id):
            continue
        if not instance.room(room_id).is_available(session.day, session.slot):
            errors.append(
                f"[{CODE_ROOM_UNAVAILABLE}] Salle {room_id!r} indisponible pour "
                f"{describe_session(session)}"
            )
    return errors


def check_availability(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie toutes les contraintes de disponibilité.

    Regroupe :func:`check_teacher_availability`, :func:`check_student_availability`
    et :func:`check_room_availability`.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de disponibilité.
    """
    return [
        *check_teacher_availability(instance, sessions),
        *check_student_availability(instance, sessions),
        *check_room_availability(instance, sessions),
    ]