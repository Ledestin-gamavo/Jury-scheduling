"""Contraintes de cohérence entre phase et salle.

Règles du contrat :

* une **pré-soutenance** est en ligne : ``room_id`` doit valoir ``None`` ;
* une **finale** est en salle : ``room_id`` est obligatoire, c'est une chaîne
  non vide, et elle doit référencer une salle existante de l'instance.

Les disponibilités, les chevauchements et les plafonds des salles sont traités
respectivement dans :mod:`validation.availability_constraints`,
:mod:`validation.no_overlap_constraints` et :mod:`validation.capacity_constraints`.

Codes d'erreur : ``ROOM_FORBIDDEN``, ``ROOM_REQUIRED``, ``ROOM_UNKNOWN``.
"""

from __future__ import annotations
from collections.abc import Sequence
from core.enums import Phase
from core.instance import Instance
from core.session import Session
from .availability_constraints import describe_session

__all__ = [
    "CODE_ROOM_FORBIDDEN",
    "CODE_ROOM_REQUIRED",
    "CODE_ROOM_UNKNOWN",
    "check_room_presence",
    "check_room_exists",
    "check_rooms",
]

CODE_ROOM_FORBIDDEN = "ROOM_FORBIDDEN"
"""Code d'erreur : une pré-soutenance en ligne porte une salle."""
CODE_ROOM_REQUIRED = "ROOM_REQUIRED"
"""Code d'erreur : une finale n'a pas de salle valide."""
CODE_ROOM_UNKNOWN = "ROOM_UNKNOWN"
"""Code d'erreur : la salle d'une finale n'existe pas dans l'instance."""


def check_room_presence(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la présence ou l'absence de salle selon la phase.

    * pré-soutenance : ``room_id`` doit être ``None`` ;
    * finale : ``room_id`` doit être une chaîne non vide.

    Args:
        instance: Instance du problème (non utilisée ici ; conservée pour
            l'uniformité de signature des contrôles).
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance dont la salle est incohérente avec la phase.
    """
    errors: list[str] = []
    for session in sessions:
        room_id = session.room_id
        if session.phase is Phase.PREDEFENCE:
            if room_id is not None:
                errors.append(
                    f"[{CODE_ROOM_FORBIDDEN}] Une pré-soutenance en ligne ne doit pas avoir "
                    f"de salle (room_id={room_id!r}) : {describe_session(session)}"
                )
        elif not isinstance(room_id, str) or not room_id.strip():
            errors.append(
                f"[{CODE_ROOM_REQUIRED}] Une finale exige une salle non vide "
                f"(room_id={room_id!r}) : {describe_session(session)}"
            )
    return errors


def check_room_exists(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie que la salle de chaque finale existe dans l'instance.

    Les finales sans salle valide (chaîne vide ou absente) sont signalées par
    :func:`check_room_presence` et ignorées ici.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par finale référençant une salle inconnue.
    """
    errors: list[str] = []
    for session in sessions:
        room_id = session.room_id
        if session.phase is not Phase.FINAL:
            continue
        if isinstance(room_id, str) and room_id.strip() and not instance.has_room(room_id):
            errors.append(
                f"[{CODE_ROOM_UNKNOWN}] Salle inconnue {room_id!r} pour "
                f"{describe_session(session)}"
            )
    return errors


def check_rooms(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie toutes les contraintes de cohérence phase / salle.

    Regroupe :func:`check_room_presence` et :func:`check_room_exists`.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        La liste de toutes les violations de salle.
    """
    return [
        *check_room_presence(instance, sessions),
        *check_room_exists(instance, sessions),
    ]