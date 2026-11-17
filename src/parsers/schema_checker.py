"""Contrôle de format minimal et lecture JSON stricte.

Ce module centralise **toutes les erreurs de format** du module ``parsers``. Il
fournit :

* la hiérarchie d'exceptions :class:`ParserError`, :class:`JSONFormatError`,
  :class:`SchemaError` ;
* la lecture JSON stricte (:func:`read_json`, :func:`parse_json_text`) qui
  applique les règles lexicales du contrat v4.0 :

  - clés d'objet dupliquées refusées ;
  - nombres non entiers refusés (``3.0`` et ``3e0`` sont rejetés) ;
  - constantes non finies (``NaN``, ``Infinity``) refusées ;
  - fichier lu en UTF-8 ;

* les contrôles de structure :func:`check_instance_data` et
  :func:`check_solution_data`, qui retournent la **liste complète** des
  erreurs de format (et non la première seulement), ainsi que les variantes
  :func:`ensure_instance_data` et :func:`ensure_solution_data`, qui lèvent
  :class:`SchemaError`.

Périmètre volontairement limité. Les contrôles portent sur la **forme** : clés
obligatoires et inconnues, version ``"4.0"``, types, énumérations, entiers dans
l'intervalle représentable, unicité là où une conversion perdrait de
l'information, cohérence ``phase``/``room_id``. Tout ce qui est de la cohérence
inter-objets (références, bornes de jours et de créneaux, périodes communes)
ou de la planification reste à la charge de
:meth:`core.instance.Instance.structural_errors` et du validateur officiel
(``validator.py``), qui fait foi.
"""

from __future__ import annotations
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from core.enums import SCHEMA_VERSION, InstanceSize, Phase, Role

__all__ = [
    "MAX_SAFE_INTEGER",
    "ParserError",
    "JSONFormatError",
    "SchemaError",
    "read_json",
    "parse_json_text",
    "check_instance_data",
    "check_solution_data",
    "ensure_instance_data",
    "ensure_solution_data",
]

MAX_SAFE_INTEGER: int = 9007199254740991
"""Plus grand entier exactement représentable en Python et en JavaScript (contrat v4.0)."""

# Clés exactes attendues (toutes obligatoires, aucune clé inconnue tolérée).
INSTANCE_KEYS: tuple[str, ...] = (
    "schema_version",
    "instance_id",
    "size",
    "seed",
    "days",
    "slots_per_day",
    "predefence_days",
    "final_defence_days",
    "domains",
    "teachers",
    "rooms",
    "students",
)
TEACHER_KEYS: tuple[str, ...] = (
    "id",
    "domains",
    "eligible_roles",
    "max_sessions_per_day",
    "availability",
)
ROOM_KEYS: tuple[str, ...] = ("id", "max_sessions_per_day", "availability")
STUDENT_KEYS: tuple[str, ...] = (
    "id",
    "domain",
    "supervisor_id",
    "eligible_final",
    "availability",
)
AVAILABILITY_KEYS: tuple[str, ...] = ("day", "slots")
SOLUTION_KEYS: tuple[str, ...] = ("schema_version", "instance_id", "sessions")
SESSION_KEYS: tuple[str, ...] = (
    "student_id",
    "phase",
    "day",
    "slot",
    "room_id",
    "president_id",
    "examiner_id",
)


# Exceptions
class ParserError(Exception):
    """Exception de base de tout le module ``parsers``.

    Permet à un appelant d'intercepter toutes les erreurs de chargement avec
    un seul ``except ParserError``.
    """


class JSONFormatError(ParserError):
    """Erreur de lecture ou de syntaxe JSON.

    Levée lorsque le fichier est introuvable, illisible, mal encodé, syntaxiquement
    invalide, ou lorsqu'il viole une règle lexicale du contrat (clé dupliquée,
    nombre non entier, constante non finie).

    Attributes:
        message: Description de l'erreur, sans la source.
        source: Chemin du fichier concerné, ou ``None`` si inconnu.
    """

    def __init__(self, message: str, source: str | None = None) -> None:
        self.message = message
        self.source = source
        super().__init__(f"{source} : {message}" if source else message)


class SchemaError(ParserError):
    """Erreur(s) de structure : le JSON est valide mais ne respecte pas le format.

    Contient **toutes** les erreurs détectées, pas seulement la première.

    Attributes:
        errors: Messages d'erreur, un par violation détectée.
        source: Chemin du fichier concerné, ou ``None`` si inconnu.
    """

    MAX_DISPLAYED: int = 20
    """Nombre maximal de messages repris dans le texte de l'exception."""

    def __init__(self, errors: Sequence[str], source: str | None = None) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        self.source = source
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Construit le message lisible (tronqué à :attr:`MAX_DISPLAYED` lignes)."""
        where = f" dans {self.source}" if self.source else ""
        total = len(self.errors)
        lines = [f"{total} erreur(s) de format{where} :"]
        lines.extend(f"  - {error}" for error in self.errors[: self.MAX_DISPLAYED])
        if total > self.MAX_DISPLAYED:
            lines.append(f"  ... et {total - self.MAX_DISPLAYED} autre(s)")
        return "\n".join(lines)


# Lecture JSON stricte
class _StrictJSONViolation(Exception):
    """Violation lexicale détectée par un crochet de ``json`` (usage interne)."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Crochet ``object_pairs_hook`` : refuse les clés d'objet dupliquées."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _StrictJSONViolation(f"clé JSON dupliquée : {key!r}")
        result[key] = value
    return result


def _reject_float(token: str) -> Any:
    """Crochet ``parse_float`` : tout nombre à virgule ou exposant est refusé."""
    raise _StrictJSONViolation(
        f"nombre non entier interdit : {token} (écrire un entier JSON, sans "
        "point décimal ni exposant)"
    )


def _reject_constant(name: str) -> Any:
    """Crochet ``parse_constant`` : refuse ``NaN``, ``Infinity`` et ``-Infinity``."""
    raise _StrictJSONViolation(f"constante JSON non finie interdite : {name}")


def parse_json_text(text: str, source: str | None = None) -> Any:
    """Analyse un texte JSON selon les règles lexicales strictes du contrat.

    Args:
        text: Contenu JSON.
        source: Nom du fichier d'origine, utilisé dans les messages d'erreur.

    Returns:
        L'objet Python décodé (``dict``, ``list``, ``str``, ``int``, ``bool``,
        ``None``). Aucun ``float`` ne peut être retourné.

    Raises:
        JSONFormatError: Si le JSON est invalide ou viole une règle lexicale.
    """
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise JSONFormatError(
            f"JSON invalide (ligne {exc.lineno}, colonne {exc.colno}) : {exc.msg}", source
        ) from exc
    except _StrictJSONViolation as exc:
        raise JSONFormatError(str(exc), source) from exc
    except RecursionError as exc:
        raise JSONFormatError("imbrication JSON excessive", source) from exc
    except ValueError as exc:  # par exemple : entier démesuré
        raise JSONFormatError(f"valeur JSON non lisible : {exc}", source) from exc


def read_json(path: str | Path) -> Any:
    """Lit un fichier JSON UTF-8 avec les règles lexicales strictes du contrat.

    Args:
        path: Chemin du fichier.

    Returns:
        L'objet Python décodé.

    Raises:
        JSONFormatError: Si le fichier est introuvable, illisible, mal encodé,
            ou si son contenu n'est pas un JSON conforme au contrat.
    """
    source = str(path)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise JSONFormatError("fichier introuvable", source) from None
    except IsADirectoryError:
        raise JSONFormatError("le chemin désigne un dossier, pas un fichier", source) from None
    except UnicodeDecodeError as exc:
        raise JSONFormatError(f"encodage UTF-8 invalide : {exc.reason}", source) from exc
    except OSError as exc:
        raise JSONFormatError(f"lecture impossible : {exc.strerror or exc}", source) from exc
    return parse_json_text(text, source)


# Primitives de contrôle (privées)
def _describe(value: Any) -> str:
    """Décrit brièvement une valeur (type et représentation tronquée)."""
    text = repr(value)
    if len(text) > 40:
        text = text[:37] + "..."
    return f"{type(value).__name__} {text}"


def _is_int(value: Any) -> bool:
    """Vrai pour un entier Python authentique (les booléens sont exclus)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _check_keys(
    obj: Any, path: str, keys: Sequence[str], errors: list[str]
) -> bool:
    """Contrôle qu'un objet est un dictionnaire avec exactement les clés attendues.

    Signale chaque clé manquante et chaque clé inconnue.

    Returns:
        ``True`` si ``obj`` est un dictionnaire (même avec des clés manquantes ou
        inconnues, déjà signalées), ``False`` sinon.
    """
    if not isinstance(obj, Mapping):
        errors.append(f"{path} : objet JSON attendu, reçu {_describe(obj)}")
        return False
    for key in keys:
        if key not in obj:
            errors.append(f"{path} : clé obligatoire manquante : {key!r}")
    for key in obj:
        if key not in keys:
            errors.append(f"{path} : clé inconnue : {key!r}")
    return True


def _check_int(
    value: Any, path: str, errors: list[str], *, minimum: int = 0
) -> bool:
    """Contrôle un entier JSON dans ``[minimum, MAX_SAFE_INTEGER]``."""
    if not _is_int(value):
        errors.append(f"{path} : entier attendu, reçu {_describe(value)}")
        return False
    if value < minimum or value > MAX_SAFE_INTEGER:
        errors.append(
            f"{path} : doit être compris entre {minimum} et {MAX_SAFE_INTEGER}, reçu {value}"
        )
        return False
    return True


def _check_str(value: Any, path: str, errors: list[str]) -> bool:
    """Contrôle une chaîne non vide et non blanche."""
    if not isinstance(value, str):
        errors.append(f"{path} : chaîne attendue, reçu {_describe(value)}")
        return False
    if not value.strip():
        errors.append(f"{path} : chaîne non vide attendue")
        return False
    return True


def _check_bool(value: Any, path: str, errors: list[str]) -> bool:
    """Contrôle un booléen JSON."""
    if not isinstance(value, bool):
        errors.append(f"{path} : booléen attendu, reçu {_describe(value)}")
        return False
    return True


def _check_list(value: Any, path: str, errors: list[str]) -> bool:
    """Contrôle qu'une valeur est un tableau JSON."""
    if not isinstance(value, list):
        errors.append(f"{path} : tableau attendu, reçu {_describe(value)}")
        return False
    return True


def _check_enum(value: Any, path: str, errors: list[str], enum_values: Sequence[str]) -> bool:
    """Contrôle qu'une valeur est l'une des chaînes d'une énumération."""
    if not isinstance(value, str) or value not in enum_values:
        allowed = ", ".join(repr(v) for v in enum_values)
        errors.append(f"{path} : valeur parmi {allowed} attendue, reçu {_describe(value)}")
        return False
    return True


def _check_int_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    unique: bool = False,
    nonempty: bool = False,
) -> bool:
    """Contrôle un tableau d'entiers JSON (unicité et non-vacuité optionnelles)."""
    if not _check_list(value, path, errors):
        return False
    ok = True
    if nonempty and not value:
        errors.append(f"{path} : tableau non vide attendu")
        ok = False
    valid_items: list[int] = []
    for index, item in enumerate(value):
        if _check_int(item, f"{path}[{index}]", errors):
            valid_items.append(item)
        else:
            ok = False
    if unique and len(set(valid_items)) != len(valid_items):
        errors.append(f"{path} : valeurs dupliquées")
        ok = False
    return ok


def _check_str_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    unique: bool = False,
    allowed: Sequence[str] | None = None,
) -> bool:
    """Contrôle un tableau de chaînes (unicité et énumération optionnelles)."""
    if not _check_list(value, path, errors):
        return False
    ok = True
    valid_items: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        item_ok = (
            _check_enum(item, item_path, errors, allowed)
            if allowed is not None
            else _check_str(item, item_path, errors)
        )
        if item_ok:
            valid_items.append(item)
        else:
            ok = False
    if unique and len(set(valid_items)) != len(valid_items):
        errors.append(f"{path} : valeurs dupliquées")
        ok = False
    return ok


def _check_availability(value: Any, path: str, errors: list[str]) -> None:
    """Contrôle un tableau de disponibilités ``[{"day": int, "slots": [int, ...]}, ...]``.

    Un jour ne doit apparaître qu'une fois ; ``slots`` est non vide et sans
    doublon. Les bornes (``days``, ``slots_per_day``) sont contrôlées plus tard
    par :meth:`core.instance.Instance.structural_errors`.
    """
    if not _check_list(value, path, errors):
        return
    seen_days: set[int] = set()
    for index, entry in enumerate(value):
        entry_path = f"{path}[{index}]"
        if not _check_keys(entry, entry_path, AVAILABILITY_KEYS, errors):
            continue
        if "day" in entry and _check_int(entry["day"], f"{entry_path}.day", errors):
            if entry["day"] in seen_days:
                errors.append(f"{entry_path}.day : jour {entry['day']} déjà présent")
            seen_days.add(entry["day"])
        if "slots" in entry:
            _check_int_list(
                entry["slots"], f"{entry_path}.slots", errors, unique=True, nonempty=True
            )


def _check_items(
    value: Any,
    path: str,
    errors: list[str],
    check_item: Callable[[Any, str, list[str]], None],
) -> None:
    """Applique ``check_item`` à chaque élément d'un tableau d'objets."""
    if not _check_list(value, path, errors):
        return
    for index, item in enumerate(value):
        check_item(item, f"{path}[{index}]", errors)


# Contrôles d'éléments d'instance
def _check_teacher(item: Any, path: str, errors: list[str]) -> None:
    """Contrôle la structure d'un enseignant."""
    if not _check_keys(item, path, TEACHER_KEYS, errors):
        return
    if "id" in item:
        _check_str(item["id"], f"{path}.id", errors)
    if "domains" in item:
        _check_str_list(item["domains"], f"{path}.domains", errors, unique=True)
    if "eligible_roles" in item:
        _check_str_list(
            item["eligible_roles"],
            f"{path}.eligible_roles",
            errors,
            unique=True,
            allowed=[role.value for role in Role],
        )
    if "max_sessions_per_day" in item:
        _check_int(item["max_sessions_per_day"], f"{path}.max_sessions_per_day", errors, minimum=1)
    if "availability" in item:
        _check_availability(item["availability"], f"{path}.availability", errors)


def _check_room(item: Any, path: str, errors: list[str]) -> None:
    """Contrôle la structure d'une salle."""
    if not _check_keys(item, path, ROOM_KEYS, errors):
        return
    if "id" in item:
        _check_str(item["id"], f"{path}.id", errors)
    if "max_sessions_per_day" in item:
        _check_int(item["max_sessions_per_day"], f"{path}.max_sessions_per_day", errors, minimum=1)
    if "availability" in item:
        _check_availability(item["availability"], f"{path}.availability", errors)


def _check_student(item: Any, path: str, errors: list[str]) -> None:
    """Contrôle la structure d'un étudiant."""
    if not _check_keys(item, path, STUDENT_KEYS, errors):
        return
    for key in ("id", "domain", "supervisor_id"):
        if key in item:
            _check_str(item[key], f"{path}.{key}", errors)
    if "eligible_final" in item:
        _check_bool(item["eligible_final"], f"{path}.eligible_final", errors)
    if "availability" in item:
        _check_availability(item["availability"], f"{path}.availability", errors)


def _check_session(item: Any, path: str, errors: list[str]) -> None:
    """Contrôle la structure d'une séance de solution.

    Contrôle aussi la cohérence ``phase``/``room_id`` imposée par
    ``solution.schema.json`` : ``null`` en pré-soutenance, chaîne non vide en finale.
    """
    if not _check_keys(item, path, SESSION_KEYS, errors):
        return
    for key in ("student_id", "president_id", "examiner_id"):
        if key in item:
            _check_str(item[key], f"{path}.{key}", errors)
    phase_ok = "phase" in item and _check_enum(
        item["phase"], f"{path}.phase", errors, [phase.value for phase in Phase]
    )
    for key in ("day", "slot"):
        if key in item:
            _check_int(item[key], f"{path}.{key}", errors)
    if "room_id" in item:
        room_id = item["room_id"]
        if room_id is not None and not isinstance(room_id, str):
            errors.append(f"{path}.room_id : null ou chaîne attendus, reçu {_describe(room_id)}")
        elif phase_ok:
            if item["phase"] == Phase.PREDEFENCE.value and room_id is not None:
                errors.append(f"{path}.room_id : doit valoir null pour une pré-soutenance")
            elif item["phase"] == Phase.FINAL.value and not (
                isinstance(room_id, str) and room_id.strip()
            ):
                errors.append(f"{path}.room_id : identifiant de salle requis pour une finale")


def _check_version(value: Any, path: str, errors: list[str]) -> None:
    """Contrôle que la version du contrat vaut exactement ``"4.0"``."""
    if value != SCHEMA_VERSION or not isinstance(value, str):
        errors.append(
            f"{path} : version non supportée, attendu {SCHEMA_VERSION!r}, reçu {_describe(value)}"
        )


# API publique
def check_instance_data(data: Any) -> list[str]:
    """Contrôle la structure minimale d'une instance décodée depuis le JSON.

    Vérifie les clés obligatoires et inconnues, la version ``"4.0"``, les types
    et les énumérations. Ne vérifie ni les références, ni les bornes de jours et
    créneaux, ni les périodes communes (voir
    :meth:`core.instance.Instance.structural_errors` et ``validator.py``).

    Args:
        data: Objet décodé (normalement un ``dict``).

    Returns:
        Liste de tous les messages d'erreur de format ; vide si la structure est correcte.
    """
    errors: list[str] = []
    if not _check_keys(data, "<instance>", INSTANCE_KEYS, errors):
        return errors

    if "schema_version" in data:
        _check_version(data["schema_version"], "schema_version", errors)
    if "instance_id" in data:
        _check_str(data["instance_id"], "instance_id", errors)
    if "size" in data:
        _check_enum(data["size"], "size", errors, [size.value for size in InstanceSize])
    if "seed" in data:
        _check_int(data["seed"], "seed", errors, minimum=0)
    if "days" in data:
        _check_int(data["days"], "days", errors, minimum=1)
    if "slots_per_day" in data:
        _check_int(data["slots_per_day"], "slots_per_day", errors, minimum=1)
    for key in ("predefence_days", "final_defence_days"):
        if key in data:
            _check_int_list(data[key], key, errors, unique=True)
    if "domains" in data:
        _check_str_list(data["domains"], "domains", errors)
    if "teachers" in data:
        _check_items(data["teachers"], "teachers", errors, _check_teacher)
    if "rooms" in data:
        _check_items(data["rooms"], "rooms", errors, _check_room)
    if "students" in data:
        _check_items(data["students"], "students", errors, _check_student)
    return errors


def check_solution_data(data: Any) -> list[str]:
    """Contrôle la structure minimale d'une solution décodée depuis le JSON.

    Vérifie les clés obligatoires et inconnues, la version ``"4.0"``, les types,
    l'énumération ``phase`` et la cohérence ``phase``/``room_id``. Ne vérifie
    aucune contrainte de planification (voir ``validator.py``).

    Args:
        data: Objet décodé (normalement un ``dict``).

    Returns:
        Liste de tous les messages d'erreur de format ; vide si la structure est correcte.
    """
    errors: list[str] = []
    if not _check_keys(data, "<solution>", SOLUTION_KEYS, errors):
        return errors

    if "schema_version" in data:
        _check_version(data["schema_version"], "schema_version", errors)
    if "instance_id" in data:
        _check_str(data["instance_id"], "instance_id", errors)
    if "sessions" in data:
        _check_items(data["sessions"], "sessions", errors, _check_session)
    return errors


def ensure_instance_data(data: Any, source: str | None = None) -> None:
    """Comme :func:`check_instance_data`, mais lève une exception en cas d'erreur.

    Args:
        data: Objet décodé.
        source: Nom du fichier d'origine, pour les messages.

    Raises:
        SchemaError: Si au moins une erreur de format est détectée.
    """
    errors = check_instance_data(data)
    if errors:
        raise SchemaError(errors, source)


def ensure_solution_data(data: Any, source: str | None = None) -> None:
    """Comme :func:`check_solution_data`, mais lève une exception en cas d'erreur.

    Args:
        data: Objet décodé.
        source: Nom du fichier d'origine, pour les messages.

    Raises:
        SchemaError: Si au moins une erreur de format est détectée.
    """
    errors = check_solution_data(data)
    if errors:
        raise SchemaError(errors, source)