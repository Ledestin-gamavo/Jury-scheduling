"""Orchestration de la validation d'une solution.

Ce module fournit :

* :class:`ValidationResult` : résultat immuable (``valid``, ``errors``,
  ``warnings``) ;
* :class:`SolutionValidator` : applique tous les contrôles de contrainte dure
  du contrat v4.0 et construit le résultat ;
* les contrôles **structurels** qui ne relèvent d'aucun des modules de
  contrainte : :func:`check_header` (version et identifiant d'instance),
  :func:`check_time_and_period` (bornes de l'horizon et périodes communes
  des phases) et :func:`check_coverage` (exactement une pré-soutenance par
  étudiant ; une finale pour chaque étudiant admissible, aucune pour les
  autres ; références d'étudiant) ;
* :data:`CONSTRAINT_CHECKS` : la liste ordonnée des contrôles, qui permet
  d'ajouter facilement un nouveau contrôle ;
* :func:`validate_solution` : raccourci fonctionnel.

Le validateur ne calcule aucune métrique et n'effectue aucune optimisation. Il
rapporte **toutes** les violations détectées (pas seulement la première), sauf
si ``max_errors`` est fixé.

Le validateur officiel ``validator.py`` reste l'arbitre de référence. Ce module
sert à contrôler les solutions dans les solveurs, les tests et le banc d'essai.

Codes d'erreur propres à ce module : ``INSTANCE``, ``HEADER``, ``REF_STUDENT``,
``TIME_BOUNDS``, ``PERIOD``, ``COVERAGE``.
"""

from __future__ import annotations
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from core.enums import SCHEMA_VERSION, Phase
from core.instance import Instance
from core.session import Session
from core.solution import Solution

from .availability_constraints import check_availability, describe_session
from .capacity_constraints import check_capacity
from .continuity_constraints import check_continuity
from .no_overlap_constraints import check_no_overlap
from .role_constraints import check_roles
from .room_constraints import check_rooms

__all__ = [
    "CODE_INSTANCE",
    "CODE_HEADER",
    "CODE_UNKNOWN_STUDENT",
    "CODE_TIME_BOUNDS",
    "CODE_PERIOD",
    "CODE_COVERAGE",
    "ConstraintCheck",
    "CONSTRAINT_CHECKS",
    "ValidationResult",
    "SolutionValidator",
    "check_header",
    "check_time_and_period",
    "check_coverage",
    "validate_solution",
]

CODE_INSTANCE = "INSTANCE"
"""Code d'erreur : incohérence structurelle de l'instance."""
CODE_HEADER = "HEADER"
"""Code d'erreur : version du contrat ou identifiant d'instance incorrect."""
CODE_UNKNOWN_STUDENT = "REF_STUDENT"
"""Code d'erreur : étudiant inconnu."""
CODE_TIME_BOUNDS = "TIME_BOUNDS"
"""Code d'erreur : jour ou créneau hors de l'horizon."""
CODE_PERIOD = "PERIOD"
"""Code d'erreur : séance hors de la période commune de sa phase."""
CODE_COVERAGE = "COVERAGE"
"""Code d'erreur : séance manquante, en double ou interdite."""

ConstraintCheck = Callable[[Instance, Sequence[Session]], list[str]]
"""Signature d'un contrôle : ``(instance, séances) -> liste d'erreurs``."""


# Contrôles structurels
def check_header(instance: Instance, solution: Solution) -> list[str]:
    """Vérifie la version du contrat et l'identifiant d'instance de la solution.

    Args:
        instance: Instance du problème.
        solution: Solution à contrôler.

    Returns:
        Les erreurs d'en-tête (vide si tout est correct).
    """
    errors: list[str] = []
    if solution.schema_version != SCHEMA_VERSION:
        errors.append(
            f"[{CODE_HEADER}] schema_version de la solution : attendu {SCHEMA_VERSION!r}, "
            f"reçu {solution.schema_version!r}"
        )
    if solution.instance_id != instance.instance_id:
        errors.append(
            f"[{CODE_HEADER}] instance_id de la solution ({solution.instance_id!r}) "
            f"différent de celui de l'instance ({instance.instance_id!r})"
        )
    return errors


def check_time_and_period(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie les bornes de l'horizon et les périodes communes des phases.

    Règles du contrat : ``0 <= day < days`` et ``0 <= slot < slots_per_day`` ;
    toute pré-soutenance se place un jour de ``predefence_days`` ; toute finale
    un jour de ``final_defence_days``. Les jours situés hors de ces deux
    ensembles ne peuvent accueillir aucune séance.

    Une séance hors de l'horizon n'est pas contrôlée une seconde fois pour sa
    période.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Une erreur par séance hors horizon ou hors période.
    """
    errors: list[str] = []
    for session in sessions:
        in_horizon = True
        if not 0 <= session.day < instance.days:
            errors.append(
                f"[{CODE_TIME_BOUNDS}] Jour {session.day} hors de l'horizon "
                f"(0..{instance.days - 1}) pour {session.student_id!r}/{session.phase.value}"
            )
            in_horizon = False
        if not 0 <= session.slot < instance.slots_per_day:
            errors.append(
                f"[{CODE_TIME_BOUNDS}] Créneau {session.slot} hors des bornes "
                f"(0..{instance.slots_per_day - 1}) pour "
                f"{session.student_id!r}/{session.phase.value}"
            )
            in_horizon = False
        if in_horizon and session.day not in instance.days_for_phase(session.phase):
            errors.append(
                f"[{CODE_PERIOD}] Le jour {session.day} n'appartient pas à la période "
                f"commune de la phase {session.phase.value!r} : {describe_session(session)}"
            )
    return errors


def check_coverage(instance: Instance, sessions: Sequence[Session]) -> list[str]:
    """Vérifie la couverture : une séance par étudiant et par phase requise.

    Règles du contrat :

    * exactement une pré-soutenance par étudiant ;
    * exactement une finale par étudiant admissible (``eligible_final``) ;
    * aucune finale pour un étudiant non admissible ;
    * toute séance référence un étudiant existant.

    Args:
        instance: Instance du problème.
        sessions: Séances à contrôler.

    Returns:
        Les erreurs de couverture et de référence d'étudiant.
    """
    errors: list[str] = []
    for session in sessions:
        if not instance.has_student(session.student_id):
            errors.append(
                f"[{CODE_UNKNOWN_STUDENT}] Étudiant inconnu {session.student_id!r} "
                f"pour {describe_session(session)}"
            )

    counts = Counter(s.key for s in sessions if instance.has_student(s.student_id))
    for student in instance.students:
        for phase in Phase:
            found = counts.get((student.id, phase), 0)
            expected = 1 if student.requires_phase(phase) else 0
            if found == expected:
                continue
            if expected == 1 and found == 0:
                errors.append(
                    f"[{CODE_COVERAGE}] Étudiant {student.id!r} : aucune séance "
                    f"{phase.value!r} alors qu'une est exigée"
                )
            elif expected == 1:
                errors.append(
                    f"[{CODE_COVERAGE}] Étudiant {student.id!r} : {found} séances "
                    f"{phase.value!r} alors qu'une seule est exigée"
                )
            else:
                errors.append(
                    f"[{CODE_COVERAGE}] Étudiant {student.id!r} non admissible à la finale : "
                    f"{found} séance(s) {phase.value!r} interdite(s)"
                )
    return errors


CONSTRAINT_CHECKS: tuple[tuple[str, ConstraintCheck], ...] = (
    ("période et horizon", check_time_and_period),
    ("couverture", check_coverage),
    ("salles", check_rooms),
    ("rôles et jury", check_roles),
    ("disponibilités", check_availability),
    ("chevauchements", check_no_overlap),
    ("plafonds journaliers", check_capacity),
    ("continuité du jury", check_continuity),
)
"""Contrôles de contrainte appliqués dans l'ordre par :class:`SolutionValidator`.

Chaque entrée associe un nom lisible à une fonction ``(instance, séances) ->
liste d'erreurs``. Pour ajouter une contrainte, il suffit d'ajouter un couple à
cette liste ou de la passer via le paramètre ``checks`` de
:class:`SolutionValidator`.
"""


# Résultat
def _code_of(message: str) -> str:
    """Extrait le code ``[CODE]`` en tête d'un message, ou ``"UNKNOWN"``."""
    if message.startswith("["):
        end = message.find("]")
        if end > 1:
            return message[1:end]
    return "UNKNOWN"


@dataclass(frozen=True)
class ValidationResult:
    """Résultat immuable de la validation d'une solution.

    Un résultat est valide si et seulement si la liste d'erreurs est vide. Les
    avertissements n'affectent jamais la validité : ils signalent une
    information utile (par exemple une liste d'erreurs tronquée).

    L'instance se convertit en booléen : ``bool(result)`` vaut ``result.valid``.

    Attributes:
        valid: ``True`` si aucune contrainte dure n'est violée.
        errors: Violations détectées, une chaîne par violation, préfixée par un
            code entre crochets.
        warnings: Informations non bloquantes.
        instance_id: Identifiant de l'instance validée.
        num_sessions: Nombre de séances contrôlées.

    Raises:
        ValueError: Si ``valid`` est incohérent avec ``errors``.
    """

    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    instance_id: str | None = None
    num_sessions: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.valid != (not self.errors):
            raise ValueError("valid doit valoir True exactement lorsque errors est vide")

    @classmethod
    def from_messages(
        cls,
        errors: Sequence[str],
        warnings: Sequence[str] = (),
        *,
        instance_id: str | None = None,
        num_sessions: int = 0,
    ) -> ValidationResult:
        """Construit un résultat en déduisant ``valid`` des erreurs.

        Args:
            errors: Messages d'erreur.
            warnings: Messages d'avertissement.
            instance_id: Identifiant de l'instance validée.
            num_sessions: Nombre de séances contrôlées.

        Returns:
            Le résultat construit.
        """
        return cls(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
            instance_id=instance_id,
            num_sessions=num_sessions,
        )

    def __bool__(self) -> bool:
        return self.valid

    @property
    def error_count(self) -> int:
        """Nombre d'erreurs rapportées."""
        return len(self.errors)

    def error_codes(self) -> dict[str, int]:
        """Retourne le nombre d'erreurs par code (par exemple ``{"OVERLAP_ROOM": 2}``).

        Les codes sont triés par ordre alphabétique.
        """
        counts = Counter(_code_of(message) for message in self.errors)
        return dict(sorted(counts.items()))

    def errors_with_code(self, code: str) -> tuple[str, ...]:
        """Retourne les erreurs portant un code donné.

        Args:
            code: Code recherché, sans crochets (par exemple ``"AVAIL_TEACHER"``).
        """
        return tuple(message for message in self.errors if _code_of(message) == code)

    def summary(self, max_lines: int = 10) -> str:
        """Retourne un résumé lisible (en français) du résultat.

        Args:
            max_lines: Nombre maximal d'erreurs détaillées dans le résumé.

        Returns:
            Un texte multiligne.
        """
        label = self.instance_id or "?"
        if self.valid:
            head = f"Solution valide pour l'instance {label} ({self.num_sessions} séances)."
        else:
            head = (
                f"Solution INVALIDE pour l'instance {label} : {self.error_count} erreur(s) "
                f"sur {self.num_sessions} séances."
            )
        lines = [head]
        if self.errors:
            lines.append("Erreurs par code : " + ", ".join(
                f"{code}={count}" for code, count in self.error_codes().items()
            ))
            lines.extend(f"  - {message}" for message in self.errors[:max_lines])
            if self.error_count > max_lines:
                lines.append(f"  ... et {self.error_count - max_lines} autre(s)")
        lines.extend(f"Avertissement : {message}" for message in self.warnings)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Retourne le résultat sous forme de dictionnaire de types simples."""
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "instance_id": self.instance_id,
            "num_sessions": self.num_sessions,
            "error_codes": self.error_codes(),
        }


# Validateur
class SolutionValidator:
    """Valide une solution par rapport au contrat v4.0.

    Le validateur est sans état : une même instance peut être réutilisée pour
    plusieurs validations, y compris depuis plusieurs solveurs.

    Ordre des contrôles : en-tête, cohérence structurelle de l'instance
    (facultative), puis les contrôles de :data:`CONSTRAINT_CHECKS`.

    Une solution incomplète ou invalide est acceptée en entrée : tous les
    problèmes sont rapportés dans le résultat, sans exception. Les références
    inconnues sont signalées une seule fois par le module concerné.

    Exemple ::

        validator = SolutionValidator()
        result = validator.validate(instance, solution)
        if not result.valid:
            print(result.summary())

    Args:
        check_instance: Si vrai (défaut), ajoute les erreurs de
            :meth:`core.instance.Instance.structural_errors` (code ``INSTANCE``).
            Une instance incohérente rend la validation peu fiable.
        max_errors: Nombre maximal d'erreurs conservées (``None`` : aucune
            limite). Si la liste est tronquée, la solution reste invalide et un
            avertissement l'indique.
        checks: Contrôles à appliquer à la place de :data:`CONSTRAINT_CHECKS`
            (couples ``(nom, fonction)``). Permet d'ajouter ou de retirer un
            contrôle.

    Raises:
        ValueError: Si ``max_errors`` est inférieur à 1.
    """

    def __init__(
        self,
        *,
        check_instance: bool = True,
        max_errors: int | None = None,
        checks: Sequence[tuple[str, ConstraintCheck]] | None = None,
    ) -> None:
        if max_errors is not None and max_errors < 1:
            raise ValueError(f"max_errors doit être >= 1 ou None, reçu {max_errors}")
        self._check_instance = check_instance
        self._max_errors = max_errors
        self._checks: tuple[tuple[str, ConstraintCheck], ...] = tuple(
            checks if checks is not None else CONSTRAINT_CHECKS
        )

    @property
    def checks(self) -> tuple[tuple[str, ConstraintCheck], ...]:
        """Contrôles de contrainte appliqués par ce validateur, dans l'ordre."""
        return self._checks

    def validate(self, instance: Instance, solution: Solution) -> ValidationResult:
        """Valide une solution pour une instance.

        Args:
            instance: Instance du problème.
            solution: Solution à contrôler.

        Returns:
            Le résultat de validation, avec toutes les erreurs détectées.
        """
        sessions = solution.sessions
        errors: list[str] = list(check_header(instance, solution))
        if self._check_instance:
            errors.extend(f"[{CODE_INSTANCE}] {message}" for message in instance.structural_errors())
        for _name, check in self._checks:
            errors.extend(check(instance, sessions))

        warnings: list[str] = []
        if self._max_errors is not None and len(errors) > self._max_errors:
            omitted = len(errors) - self._max_errors
            errors = errors[: self._max_errors]
            warnings.append(
                f"{omitted} erreur(s) supplémentaire(s) omise(s) (max_errors={self._max_errors}) ; "
                "la solution reste invalide"
            )
        return ValidationResult.from_messages(
            errors,
            warnings,
            instance_id=instance.instance_id,
            num_sessions=len(sessions),
        )

    def is_valid(self, instance: Instance, solution: Solution) -> bool:
        """Retourne uniquement le booléen de validité.

        Args:
            instance: Instance du problème.
            solution: Solution à contrôler.
        """
        return self.validate(instance, solution).valid


def validate_solution(
    instance: Instance, solution: Solution, **options: Any
) -> ValidationResult:
    """Raccourci : valide une solution avec un :class:`SolutionValidator` temporaire.

    Args:
        instance: Instance du problème.
        solution: Solution à contrôler.
        **options: Options transmises à :class:`SolutionValidator`
            (``check_instance``, ``max_errors``, ``checks``).

    Returns:
        Le résultat de validation.
    """
    return SolutionValidator(**options).validate(instance, solution)