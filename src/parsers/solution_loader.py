"""Chargement d'une solution JSON vers un objet :class:`core.solution.Solution`.

Utilisation::

    from parsers.solution_loader import load_solution

    solution = load_solution("mon_planning.json")

Étapes réalisées par :func:`load_solution` :

1. lecture JSON stricte (:func:`parsers.schema_checker.read_json`) ;
2. contrôle de format (:func:`parsers.schema_checker.ensure_solution_data`) ;
3. conversion en objets ``core`` (``Session``, ``Solution``) ;
4. optionnellement, vérification que la solution porte le même ``instance_id``
   que l'instance fournie.

Ce module ne vérifie ni les références (étudiants, salles, enseignants), ni les
contraintes de planification, ni les métriques : une solution incomplète ou
invalide est chargée sans erreur dès lors que son format est correct. Ces
contrôles relèvent du module ``validation`` et du validateur officiel
(``validator.py``).
"""

from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from core.enums import Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution
from .schema_checker import ParserError, SchemaError, ensure_solution_data, read_json

__all__ = ["load_solution", "solution_from_dict"]

def _build_session(item: Mapping[str, Any]) -> Session:
    """Convertit une séance JSON (déjà contrôlée) en :class:`Session`."""
    return Session(
        student_id=item["student_id"],
        phase=Phase(item["phase"]),
        day=item["day"],
        slot=item["slot"],
        room_id=item["room_id"],
        president_id=item["president_id"],
        examiner_id=item["examiner_id"],
    )


def solution_from_dict(
    data: Mapping[str, Any],
    *,
    source: str | None = None,
    instance: Instance | None = None,
) -> Solution:
    """Construit une :class:`Solution` à partir d'un dictionnaire déjà décodé.

    L'ordre des séances du JSON est conservé.

    Args:
        data: Dictionnaire issu d'un JSON de solution.
        source: Nom d'origine (fichier), utilisé dans les messages d'erreur.
        instance: Instance attendue (facultatif). Si fournie, ``instance_id`` de
            la solution doit lui être identique.

    Returns:
        La solution construite.

    Raises:
        SchemaError: Si le format est incorrect, ou si ``instance`` est fournie
            et que les identifiants d'instance diffèrent.
        ParserError: Si la conversion échoue de façon inattendue.
    """
    ensure_solution_data(data, source)

    if instance is not None and data["instance_id"] != instance.instance_id:
        raise SchemaError(
            [
                f"instance_id de la solution ({data['instance_id']!r}) différent de "
                f"celui de l'instance ({instance.instance_id!r})"
            ],
            source,
        )

    try:
        sessions = [_build_session(item) for item in data["sessions"]]
        return Solution(
            instance_id=data["instance_id"],
            sessions=sessions,
            schema_version=data["schema_version"],
        )
    except (ValueError, TypeError, KeyError) as exc:
        where = f" ({source})" if source else ""
        raise ParserError(f"conversion de la solution impossible{where} : {exc}") from exc


def load_solution(path: str | Path, *, instance: Instance | None = None) -> Solution:
    """Charge un fichier JSON de solution et retourne un objet :class:`Solution`.

    Args:
        path: Chemin du fichier de solution.
        instance: Instance attendue (facultatif). Si fournie, vérifie la
            correspondance des ``instance_id``.

    Returns:
        La solution chargée (mutable, séances immuables).

    Raises:
        JSONFormatError: Si le fichier est introuvable, illisible ou non conforme
            aux règles lexicales JSON du contrat.
        SchemaError: Si la structure est incorrecte ou si l'identifiant
            d'instance ne correspond pas.
        ParserError: Pour toute autre erreur de conversion.
    """
    source = str(path)
    data = read_json(path)
    return solution_from_dict(data, source=source, instance=instance)