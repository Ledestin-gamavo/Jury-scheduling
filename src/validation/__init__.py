"""Module ``validation`` : vérification des contraintes dures du contrat v4.0.

Ce module vérifie qu'une :class:`core.solution.Solution` respecte le contrat de
données version 4.0 pour une :class:`core.instance.Instance` donnée. Il ne
contient **aucune** logique d'optimisation, de résolution ni de calcul de
métriques.

Organisation :

* :mod:`validation.availability_constraints` : disponibilités des enseignants,
  des étudiants et des salles ;
* :mod:`validation.no_overlap_constraints` : absence de chevauchement
  (enseignants, étudiants, salles) ;
* :mod:`validation.capacity_constraints` : plafonds journaliers
  (``max_sessions_per_day``) des enseignants et des salles ;
* :mod:`validation.continuity_constraints` : même président et même
  examinateur entre pré-soutenance et finale ;
* :mod:`validation.role_constraints` : rôles, domaine de l'examinateur,
  personnes distinctes ;
* :mod:`validation.room_constraints` : cohérence phase / salle ;
* :mod:`validation.solution_validator` : orchestration (:class:`SolutionValidator`),
  résultat (:class:`ValidationResult`) et contrôles de couverture, de
  références et de périodes communes.

Convention commune : chaque contrôle est une fonction
``check_xxx(instance, sessions) -> list[str]`` qui retourne la liste des
violations, vide si la contrainte est respectée. Chaque message commence par un
code entre crochets (par exemple ``[AVAIL_TEACHER]``), ce qui permet de
filtrer ou de compter les erreurs par type. Ces fonctions sont publiques :
un solveur peut les appeler seules pour tester une contrainte précise.

Règle de dépendance (voir ``current_progress.md``) : ``validation`` dépend
uniquement de ``core``.

Le validateur officiel ``validator.py`` reste l'arbitre de référence : ce module
en est une implémentation interne, utilisable dans les solveurs, les tests et
le banc d'essai.

Exemple ::

    from parsers import load_instance, load_solution
    from validation import SolutionValidator

    instance = load_instance("data/small_01.json")
    solution = load_solution("mon_planning.json", instance=instance)
    result = SolutionValidator().validate(instance, solution)
    if not result.valid:
        print(result.summary())
"""

from __future__ import annotations
from .availability_constraints import (
    attending_teachers,
    check_availability,
    check_room_availability,
    check_student_availability,
    check_teacher_availability,
    describe_session,
)
from .capacity_constraints import (
    check_capacity,
    check_room_capacity,
    check_teacher_capacity,
)
from .continuity_constraints import (
    check_continuity,
    check_examiner_continuity,
    check_president_continuity,
)
from .no_overlap_constraints import (
    check_no_overlap,
    check_room_no_overlap,
    check_student_no_overlap,
    check_teacher_no_overlap,
)
from .role_constraints import (
    check_distinct_jury,
    check_examiner_domain,
    check_examiner_role,
    check_president_role,
    check_roles,
    check_teacher_references,
)
from .room_constraints import check_room_exists, check_room_presence, check_rooms
from .solution_validator import (
    CONSTRAINT_CHECKS,
    ConstraintCheck,
    SolutionValidator,
    ValidationResult,
    check_coverage,
    check_header,
    check_time_and_period,
    validate_solution,
)

__all__ = [
    # Orchestration
    "SolutionValidator",
    "ValidationResult",
    "validate_solution",
    "CONSTRAINT_CHECKS",
    "ConstraintCheck",
    # Contrôles structurels
    "check_header",
    "check_time_and_period",
    "check_coverage",
    # Disponibilités
    "check_availability",
    "check_teacher_availability",
    "check_student_availability",
    "check_room_availability",
    # Chevauchements
    "check_no_overlap",
    "check_teacher_no_overlap",
    "check_student_no_overlap",
    "check_room_no_overlap",
    # Plafonds journaliers
    "check_capacity",
    "check_teacher_capacity",
    "check_room_capacity",
    # Continuité
    "check_continuity",
    "check_president_continuity",
    "check_examiner_continuity",
    # Rôles
    "check_roles",
    "check_teacher_references",
    "check_president_role",
    "check_examiner_role",
    "check_examiner_domain",
    "check_distinct_jury",
    # Salles
    "check_rooms",
    "check_room_presence",
    "check_room_exists",
    # Utilitaires partagés
    "attending_teachers",
    "describe_session",
]