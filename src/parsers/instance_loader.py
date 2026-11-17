"""Chargement d'une instance JSON vers un objet :class:`core.instance.Instance`.

Utilisation::

    from parsers.instance_loader import load_instance

    instance = load_instance("data/small_01.json")

Étapes réalisées par :func:`load_instance` :

1. lecture JSON stricte (:func:`parsers.schema_checker.read_json`) ;
2. contrôle de format (:func:`parsers.schema_checker.ensure_instance_data`) ;
3. conversion en objets ``core`` (``Teacher``, ``Room``, ``Student``, ``Instance``) ;
4. contrôle de cohérence structurelle, en réutilisant
   :meth:`core.instance.Instance.structural_errors` sans dupliquer sa logique.

Ce module ne fait aucune validation de planification et ne cherche pas à
remplacer le validateur officiel (``validator.py``).
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from core.enums import Availability, InstanceSize
from core.instance import Instance
from core.room import Room
from core.student import Student
from core.teacher import Teacher
from .schema_checker import ParserError, SchemaError, ensure_instance_data, read_json

__all__ = ["load_instance", "instance_from_dict"]

def _build_availability(entries: Sequence[Mapping[str, Any]]) -> Availability:
    """Convertit une liste JSON de disponibilités en :class:`Availability`.

    Args:
        entries: Liste d'objets ``{"day": int, "slots": [int, ...]}`` déjà contrôlés.

    Returns:
        La disponibilité normalisée.
    """
    return Availability.from_entries((entry["day"], entry["slots"]) for entry in entries)


def _build_teacher(item: Mapping[str, Any]) -> Teacher:
    """Convertit un enseignant JSON (déjà contrôlé) en :class:`Teacher`."""
    return Teacher.build(
        id=item["id"],
        domains=item["domains"],
        eligible_roles=item["eligible_roles"],
        max_sessions_per_day=item["max_sessions_per_day"],
        availability=_build_availability(item["availability"]),
    )


def _build_room(item: Mapping[str, Any]) -> Room:
    """Convertit une salle JSON (déjà contrôlée) en :class:`Room`."""
    return Room(
        id=item["id"],
        max_sessions_per_day=item["max_sessions_per_day"],
        availability=_build_availability(item["availability"]),
    )


def _build_student(item: Mapping[str, Any]) -> Student:
    """Convertit un étudiant JSON (déjà contrôlé) en :class:`Student`."""
    return Student(
        id=item["id"],
        domain=item["domain"],
        supervisor_id=item["supervisor_id"],
        eligible_final=item["eligible_final"],
        availability=_build_availability(item["availability"]),
    )


def instance_from_dict(
    data: Mapping[str, Any],
    *,
    source: str | None = None,
    check_structure: bool = True,
) -> Instance:
    """Construit une :class:`Instance` à partir d'un dictionnaire déjà décodé.

    Utile pour les tests ou lorsque le JSON provient d'une autre source qu'un
    fichier.

    Args:
        data: Dictionnaire issu d'un JSON d'instance.
        source: Nom d'origine (fichier), utilisé dans les messages d'erreur.
        check_structure: Si vrai (défaut), exécute
            :meth:`core.instance.Instance.structural_errors` après construction
            et lève :class:`SchemaError` si une incohérence est détectée. Mettre
            ``False`` pour charger volontairement une instance incohérente (par
            exemple pour tester le validateur).

    Returns:
        L'instance construite.

    Raises:
        SchemaError: Si le format est incorrect, ou si ``check_structure`` est
            vrai et que l'instance est structurellement incohérente.
        ParserError: Si la conversion échoue de façon inattendue.
    """
    ensure_instance_data(data, source)

    try:
        instance = Instance(
            instance_id=data["instance_id"],
            size=InstanceSize(data["size"]),
            seed=data["seed"],
            days=data["days"],
            slots_per_day=data["slots_per_day"],
            predefence_days=tuple(data["predefence_days"]),
            final_defence_days=tuple(data["final_defence_days"]),
            domains=tuple(data["domains"]),
            teachers=tuple(_build_teacher(item) for item in data["teachers"]),
            rooms=tuple(_build_room(item) for item in data["rooms"]),
            students=tuple(_build_student(item) for item in data["students"]),
            schema_version=data["schema_version"],
        )
    except (ValueError, TypeError, KeyError) as exc:
        where = f" ({source})" if source else ""
        raise ParserError(f"conversion de l'instance impossible{where} : {exc}") from exc

    if check_structure:
        errors = instance.structural_errors()
        if errors:
            raise SchemaError(errors, source)
    return instance


def load_instance(path: str | Path, *, check_structure: bool = True) -> Instance:
    """Charge un fichier JSON d'instance et retourne un objet :class:`Instance`.

    Args:
        path: Chemin du fichier d'instance (par exemple ``data/small_01.json``).
        check_structure: Voir :func:`instance_from_dict`.

    Returns:
        L'instance chargée, immuable et prête pour les solveurs, la validation
        et les métriques.

    Raises:
        JSONFormatError: Si le fichier est introuvable, illisible ou non conforme
            aux règles lexicales JSON du contrat.
        SchemaError: Si la structure est incorrecte ou l'instance incohérente.
        ParserError: Pour toute autre erreur de conversion.
    """
    source = str(path)
    data = read_json(path)
    return instance_from_dict(data, source=source, check_structure=check_structure)