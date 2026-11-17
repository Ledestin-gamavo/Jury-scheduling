"""Module ``parsers`` : transformation des fichiers JSON en objets du noyau métier.

Ce module est la frontière entre le système de fichiers et le noyau métier
(``core``). Il se limite à trois responsabilités :

1. **Charger** un fichier JSON de façon stricte (clés dupliquées, nombres non
   entiers et constantes non finies refusés, comme l'exige le contrat v4.0) ;
2. **Contrôler** les préconditions minimales de format (clés obligatoires,
   version ``"4.0"``, types, énumérations) ;
3. **Convertir** les données en objets :class:`core.instance.Instance` et
   :class:`core.solution.Solution`.

Il ne reproduit **pas** le validateur officiel (``validator.py``) : il ne vérifie
ni les contraintes de planification, ni la faisabilité, ni les métriques.

Règles de dépendance :

* ``parsers`` dépend de ``core`` ;
* ``core`` ne dépend jamais de ``parsers``.

Hypothèse d'import : le dossier ``src/`` figure dans le chemin d'import Python
(``PYTHONPATH``), de sorte que ``core`` et ``parsers`` sont importables comme
paquets de premier niveau.

Exemple d'utilisation::

    from parsers import load_instance, load_solution

    instance = load_instance("data/small_01.json")
    solution = load_solution("results/small_01/solution.json", instance=instance)
"""

from .instance_loader import instance_from_dict, load_instance
from .schema_checker import (
    JSONFormatError,
    ParserError,
    SchemaError,
    check_instance_data,
    check_solution_data,
    ensure_instance_data,
    ensure_solution_data,
    parse_json_text,
    read_json,
)
from .solution_loader import load_solution, solution_from_dict

__all__ = [
    # Chargeurs
    "load_instance",
    "instance_from_dict",
    "load_solution",
    "solution_from_dict",
    # Exceptions
    "ParserError",
    "JSONFormatError",
    "SchemaError",
    # Contrôles de format
    "check_instance_data",
    "check_solution_data",
    "ensure_instance_data",
    "ensure_solution_data",
    # Lecture JSON stricte
    "read_json",
    "parse_json_text",
]