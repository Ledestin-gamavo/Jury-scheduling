"""Contraintes de rôles et de composition du jury.

Règles du contrat :

* le président doit être habilité au rôle ``president`` ; il n'a aucune
  obligation de correspondance de domaine ;
* l'examinateur doit être habilité au rôle ``examiner`` **et** couvrir le
  domaine de l'étudiant ;
* **personnes distinctes** :

  - pré-soutenance : le président et l'examinateur sont deux personnes
    différentes ;
  - finale : le président, l'examinateur et l'encadrant-rapporteur sont trois
    personnes différentes ;

* l'encadrant n'a besoin d'aucun rôle éligible ni d'aucune qualification de
  domaine.

Ce module signale aussi les identifiants d'enseignant **inconnus** (président
ou examinateur absent de l'instance). Les contrôles de rôle et de domaine
ignorent ensuite ces références pour ne pas produire de messages redondants.

Codes d'erreur : ``ROLE_UNKNOWN_TEACHER``, ``ROLE_PRESIDENT``, ``ROLE_EXAMINER``,
``ROLE_DOMAIN``, ``ROLE_DISTINCT``.
"""

from __future__ import annotations
from collections.abc import Sequence
from core.enums import Phase, Role
from core.instance import Instance
from core.session import Session
from .availability_constraints import describe_session

__all__ = [
    "CODE_UNKNOWN_TEACHER",
    "CODE_PRESIDENT_ROLE",
    "CODE_EXAMINER_ROLE",
    "CODE_EXAMINER_DOMAIN",
    "CODE_DISTINCT_JURY",
    "check_teacher_references",
    "check_president_role",
    "check_examiner_role",
    "check_examiner_domain",
    "check_distinct_jury",
    "check_roles",
]

CODE_UNKNOWN_TEACHER = "ROLE_UNKNOWN_TEACHER"
"""Code d'erreur : le président ou l'examinateur n'existe pas dans l'instance."""
CODE_PRESIDENT_ROLE = "ROLE_PRESIDENT"
"""Code d'erreur : le président n'a pas le rôle ``president``."""
CODE_EXAMINER_ROLE = "ROLE_EXAMINER"
"""Code d'erreur : l'examinateur n'a pas le rôle ``examiner``."""
CODE_EXAMINER_DOMAIN = "ROLE_DOMAIN"
"""Code d'erreur : l'examinateur ne couvre pas le domaine de l'étudiant."""
CODE_DISTINCT_JURY = "ROLE_DISTINCT"
"""Code d'erreur : des membres du jury sont une même personne."""


def check_teacher_references(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que le président et l'examinateur existent dans l'instance.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par référence d'enseignant inconnue.
    """
    errors: list[str] = []
    for session in sessions:
        for label, teacher_id in (
            ("président", session.president_id),
            ("examinateur", session.examiner_id),
        ):
            if not instance.has_teacher(teacher_id):
                errors.append(
                    f"[{CODE_UNKNOWN_TEACHER}] {label.capitalize()} inconnu {teacher_id!r} "
                    f"pour {describe_session(session)}"
                )
    return errors


def check_president_role(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que chaque président possède le rôle ``president``.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance dont le président n'est pas habilité.
    """
    errors: list[str] = []
    for session in sessions:
        if not instance.has_teacher(session.president_id):
            continue
        if not instance.teacher(session.president_id).can_serve_as(Role.PRESIDENT):
            errors.append(
                f"[{CODE_PRESIDENT_ROLE}] {session.president_id!r} n'a pas le rôle "
                f"'president' ({describe_session(session)})"
            )
    return errors


def check_examiner_role(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que chaque examinateur possède le rôle ``examiner``.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance dont l'examinateur n'est pas habilité.
    """
    errors: list[str] = []
    for session in sessions:
        if not instance.has_teacher(session.examiner_id):
            continue
        if not instance.teacher(session.examiner_id).can_serve_as(Role.EXAMINER):
            errors.append(
                f"[{CODE_EXAMINER_ROLE}] {session.examiner_id!r} n'a pas le rôle "
                f"'examiner' ({describe_session(session)})"
            )
    return errors


def check_examiner_domain(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que chaque examinateur couvre le domaine de l'étudiant.

    Seul l'examinateur est soumis à cette règle : le président et l'encadrant
    n'ont aucune obligation de domaine.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance dont l'examinateur ne couvre pas le domaine.
    """
    errors: list[str] = []
    for session in sessions:
        if not instance.has_teacher(session.examiner_id) or not instance.has_student(
            session.student_id
        ):
            continue
        domain = instance.student(session.student_id).domain
        if not instance.teacher(session.examiner_id).covers_domain(domain):
            errors.append(
                f"[{CODE_EXAMINER_DOMAIN}] Examinateur {session.examiner_id!r} ne couvre "
                f"pas le domaine {domain!r} ({describe_session(session)})"
            )
    return errors


def check_distinct_jury(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que les membres du jury sont des personnes distinctes.

    * Pré-soutenance : président et examinateur distincts.
    * Finale : président, examinateur et encadrant-rapporteur tous distincts
      (l'encadrant n'est contrôlé que si l'étudiant est connu).

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par couple de membres identiques dans une séance.
    """
    errors: list[str] = []
    for session in sessions:
        where = describe_session(session)
        if session.president_id == session.examiner_id:
            errors.append(
                f"[{CODE_DISTINCT_JURY}] Président et examinateur identiques "
                f"({session.president_id!r}) pour {where}"
            )
        if session.phase is Phase.FINAL and instance.has_student(session.student_id):
            supervisor_id = instance.student(session.student_id).supervisor_id
            if session.president_id == supervisor_id:
                errors.append(
                    f"[{CODE_DISTINCT_JURY}] Président identique à l'encadrant-rapporteur "
                    f"({supervisor_id!r}) pour {where}"
                )
            if session.examiner_id == supervisor_id:
                errors.append(
                    f"[{CODE_DISTINCT_JURY}] Examinateur identique à l'encadrant-rapporteur "
                    f"({supervisor_id!r}) pour {where}"
                )
    return errors


def check_roles(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie toutes les contraintes de rôles et de composition du jury.

    Regroupe :func:`check_teacher_references`, :func:`check_president_role`,
    :func:`check_examiner_role`, :func:`check_examiner_domain` et
    :func:`check_distinct_jury`.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de rôle.
    """
    return [
        *check_teacher_references(instance, sessions),
        *check_president_role(instance, sessions),
        *check_examiner_role(instance, sessions),
        *check_examiner_domain(instance, sessions),
        *check_distinct_jury(instance, sessions),
    ]