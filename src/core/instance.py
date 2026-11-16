"""Modèle métier d'une instance du problème de planification."""

from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from .enums import SCHEMA_VERSION, Availability, InstanceSize, Phase, Role
from .room import Room
from .session import Session
from .student import Student
from .teacher import Teacher

__all__ = ["Instance"]

@dataclass(frozen=True)
class Instance:
    """Données complètes d'un problème de planification de soutenances.

    L'instance est **immuable** : ses collections sont converties en tuples à la
    construction. Elle peut donc être partagée sans risque entre solveurs,
    processus et tests. Elle fournit des index et des requêtes d'accès
    (précalculés à la demande) utiles à un solveur glouton, à la construction
    d'un modèle CP-SAT ou à la validation. Elle n'effectue aucune optimisation.

    Les règles de période (contrat v4.0) : les jours de pré-soutenance et de
    finale sont deux ensembles non vides, disjoints, avec
    ``max(predefence_days) < min(final_defence_days)``. Ils peuvent être non
    triés et non contigus ; les jours hors de ces périodes n'accueillent aucune
    séance.

    Le constructeur ne contrôle que ce qui est nécessaire à la cohérence des
    objets. Les contrôles inter-objets (références, bornes, périodes) sont
    regroupés dans :meth:`structural_errors`, qui retourne une liste de
    messages sans lever d'exception. Le validateur officiel du projet reste
    l'arbitre.

    Attributes:
        instance_id: Identifiant de l'instance.
        size: Classe de taille.
        seed: Graine de génération (entier >= 0).
        days: Nombre de jours de l'horizon (indices ``0..days-1``).
        slots_per_day: Nombre de créneaux par jour (indices ``0..slots_per_day-1``).
        predefence_days: Jours autorisés aux pré-soutenances.
        final_defence_days: Jours autorisés aux soutenances finales.
        domains: Identifiants des domaines scientifiques.
        teachers: Enseignants.
        rooms: Salles (utilisées uniquement par les finales).
        students: Étudiants.
        schema_version: Version du contrat de données.
    """

    instance_id: str
    size: InstanceSize
    seed: int
    days: int
    slots_per_day: int
    predefence_days: tuple[int, ...]
    final_defence_days: tuple[int, ...]
    domains: tuple[str, ...]
    teachers: tuple[Teacher, ...]
    rooms: tuple[Room, ...]
    students: tuple[Student, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        # Normalisation : accepte listes ou tuples, conserve l'immuabilité.
        object.__setattr__(self, "size", InstanceSize(self.size))
        for name in (
            "predefence_days",
            "final_defence_days",
            "domains",
            "teachers",
            "rooms",
            "students",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    # Index internes (calculés une fois, à la demande)
    @cached_property
    def _teachers_by_id(self) -> dict[str, Teacher]:
        return {t.id: t for t in self.teachers}

    @cached_property
    def _students_by_id(self) -> dict[str, Student]:
        return {s.id: s for s in self.students}

    @cached_property
    def _rooms_by_id(self) -> dict[str, Room]:
        return {r.id: r for r in self.rooms}

    @cached_property
    def _teachers_by_role(self) -> dict[Role, tuple[Teacher, ...]]:
        return {
            role: tuple(t for t in self.teachers if t.can_serve_as(role)) for role in Role
        }

    @cached_property
    def _students_by_supervisor(self) -> dict[str, tuple[Student, ...]]:
        grouped: dict[str, list[Student]] = {}
        for student in self.students:
            grouped.setdefault(student.supervisor_id, []).append(student)
        return {sup: tuple(group) for sup, group in grouped.items()}

    # Accès par identifiant
    def teacher(self, teacher_id: str) -> Teacher:
        """Retourne l'enseignant ``teacher_id``.

        Raises:
            KeyError: Si l'identifiant est inconnu.
        """
        try:
            return self._teachers_by_id[teacher_id]
        except KeyError:
            raise KeyError(f"Enseignant inconnu : {teacher_id!r}") from None

    def student(self, student_id: str) -> Student:
        """Retourne l'étudiant ``student_id``.

        Raises:
            KeyError: Si l'identifiant est inconnu.
        """
        try:
            return self._students_by_id[student_id]
        except KeyError:
            raise KeyError(f"Étudiant inconnu : {student_id!r}") from None

    def room(self, room_id: str) -> Room:
        """Retourne la salle ``room_id``.

        Raises:
            KeyError: Si l'identifiant est inconnu.
        """
        try:
            return self._rooms_by_id[room_id]
        except KeyError:
            raise KeyError(f"Salle inconnue : {room_id!r}") from None

    def has_teacher(self, teacher_id: str) -> bool:
        """Indique si l'enseignant existe."""
        return teacher_id in self._teachers_by_id

    def has_student(self, student_id: str) -> bool:
        """Indique si l'étudiant existe."""
        return student_id in self._students_by_id

    def has_room(self, room_id: str) -> bool:
        """Indique si la salle existe."""
        return room_id in self._rooms_by_id

    # Identifiants et dimensions (indices stables, utiles pour CP-SAT)
    @property
    def teacher_ids(self) -> tuple[str, ...]:
        """Identifiants des enseignants, dans l'ordre de l'instance."""
        return tuple(t.id for t in self.teachers)

    @property
    def student_ids(self) -> tuple[str, ...]:
        """Identifiants des étudiants, dans l'ordre de l'instance."""
        return tuple(s.id for s in self.students)

    @property
    def room_ids(self) -> tuple[str, ...]:
        """Identifiants des salles, dans l'ordre de l'instance."""
        return tuple(r.id for r in self.rooms)

    @property
    def num_teachers(self) -> int:
        """Nombre d'enseignants."""
        return len(self.teachers)

    @property
    def num_students(self) -> int:
        """Nombre d'étudiants."""
        return len(self.students)

    @property
    def num_rooms(self) -> int:
        """Nombre de salles."""
        return len(self.rooms)

    # Temps : jours, créneaux, périodes
    @property
    def all_days(self) -> range:
        """Tous les jours de l'horizon (``0..days-1``)."""
        return range(self.days)

    @property
    def all_slots(self) -> range:
        """Tous les créneaux d'une journée (``0..slots_per_day-1``)."""
        return range(self.slots_per_day)

    def days_for_phase(self, phase: Phase) -> tuple[int, ...]:
        """Retourne les jours autorisés pour ``phase``, triés par ordre croissant."""
        period = self.predefence_days if phase is Phase.PREDEFENCE else self.final_defence_days
        return tuple(sorted(period))

    def phase_of_day(self, day: int) -> Phase | None:
        """Retourne la phase autorisée un jour donné, ou ``None`` si aucune."""
        if day in self.predefence_days:
            return Phase.PREDEFENCE
        if day in self.final_defence_days:
            return Phase.FINAL
        return None

    def time_slots_for_phase(self, phase: Phase) -> tuple[tuple[int, int], ...]:
        """Retourne tous les couples ``(jour, créneau)`` autorisés pour ``phase``."""
        return tuple(
            (day, slot) for day in self.days_for_phase(phase) for slot in self.all_slots
        )

    # Besoins de planification
    def required_sessions(self) -> tuple[tuple[str, Phase], ...]:
        """Liste les séances à planifier, une par couple ``(étudiant, phase)``.

        Chaque étudiant a une pré-soutenance ; seuls les étudiants admissibles
        ont aussi une finale.
        """
        return tuple(
            (student.id, phase)
            for student in self.students
            for phase in student.required_phases()
        )

    @property
    def num_required_sessions(self) -> int:
        """Nombre total de séances à planifier."""
        return len(self.required_sessions())

    def final_students(self) -> tuple[Student, ...]:
        """Retourne les étudiants admissibles à la finale."""
        return tuple(s for s in self.students if s.eligible_final)

    def students_supervised_by(self, teacher_id: str) -> tuple[Student, ...]:
        """Retourne les étudiants encadrés par ``teacher_id``."""
        return self._students_by_supervisor.get(teacher_id, ())

    # Éligibilité du jury
    def teachers_with_role(self, role: Role) -> tuple[Teacher, ...]:
        """Retourne les enseignants habilités pour ``role``."""
        return self._teachers_by_role[role]

    def eligible_presidents(self) -> tuple[Teacher, ...]:
        """Retourne les enseignants habilités comme présidents."""
        return self._teachers_by_role[Role.PRESIDENT]

    def eligible_examiners(self, domain: str) -> tuple[Teacher, ...]:
        """Retourne les enseignants pouvant examiner le domaine ``domain``."""
        return tuple(t for t in self._teachers_by_role[Role.EXAMINER] if t.covers_domain(domain))

    def eligible_examiners_for_student(self, student_id: str) -> tuple[Teacher, ...]:
        """Retourne les examinateurs possibles pour le domaine d'un étudiant."""
        return self.eligible_examiners(self.student(student_id).domain)

    def attending_teacher_ids(self, session: Session) -> tuple[str, ...]:
        """Retourne les enseignants présents physiquement ou en ligne à une séance.

        Ordre : président, examinateur, puis encadrant (finale uniquement).
        Les identifiants sont dédoublonnés : une même personne n'est jamais
        comptée comme plusieurs participants. La vérification que le jury est
        composé de personnes distinctes relève de la validation.

        Raises:
            KeyError: Si l'étudiant de la séance est inconnu (cas d'une finale).
        """
        ids = [session.president_id, session.examiner_id]
        if session.phase is Phase.FINAL:
            ids.append(self.student(session.student_id).supervisor_id)
        return tuple(dict.fromkeys(ids))

    # Cohérence structurelle (sans exception, sans solveur)
    def structural_errors(self) -> list[str]:
        """Retourne les violations de cohérence structurelle de l'instance.

        Contrôle les règles du contrat v4.0 portant sur l'instance : version,
        bornes, périodes communes, unicité des identifiants, références
        (domaines, encadrants) et disponibilités. Ne vérifie **pas** l'existence
        d'une solution réalisable. Ne remplace pas le validateur officiel.

        Returns:
            Liste de messages d'erreur ; vide si l'instance est cohérente.
        """
        errors: list[str] = []
        if self.schema_version != SCHEMA_VERSION:
            errors.append(
                f"schema_version doit valoir {SCHEMA_VERSION!r}, reçu {self.schema_version!r}"
            )
        if not self.instance_id.strip():
            errors.append("instance_id est vide")
        if self.seed < 0:
            errors.append(f"seed doit être >= 0, reçu {self.seed}")
        if self.days < 1:
            errors.append(f"days doit être >= 1, reçu {self.days}")
        if self.slots_per_day < 1:
            errors.append(f"slots_per_day doit être >= 1, reçu {self.slots_per_day}")

        errors.extend(self._period_errors())
        errors.extend(self._reference_errors())
        errors.extend(self._availability_errors())
        return errors

    def _period_errors(self) -> list[str]:
        """Contrôle les deux périodes communes de phase."""
        errors: list[str] = []
        periods = (
            ("predefence_days", self.predefence_days),
            ("final_defence_days", self.final_defence_days),
        )
        for label, period in periods:
            if not period:
                errors.append(f"{label} est vide")
            if len(set(period)) != len(period):
                errors.append(f"{label} contient des doublons")
            out_of_range = sorted(d for d in set(period) if not 0 <= d < self.days)
            if out_of_range:
                errors.append(f"{label} contient des jours hors horizon : {out_of_range}")

        if self.predefence_days and self.final_defence_days:
            common = sorted(set(self.predefence_days) & set(self.final_defence_days))
            if common:
                errors.append(f"Les périodes ne sont pas disjointes (jours communs : {common})")
            if max(self.predefence_days) >= min(self.final_defence_days):
                errors.append("max(predefence_days) doit être < min(final_defence_days)")
        return errors

    def _reference_errors(self) -> list[str]:
        """Contrôle l'unicité des identifiants et les références croisées."""
        errors: list[str] = []
        if not self.domains:
            errors.append("domains est vide")
        if len(set(self.domains)) != len(self.domains):
            errors.append("domains contient des doublons")
        if any(not d.strip() for d in self.domains):
            errors.append("domains contient un identifiant vide")

        for label, items in (
            ("teachers", self.teachers),
            ("rooms", self.rooms),
            ("students", self.students),
        ):
            if not items:
                errors.append(f"{label} est vide")
            duplicates = _duplicates(item.id for item in items)
            if duplicates:
                errors.append(f"{label} : identifiants dupliqués {duplicates}")

        known_domains = set(self.domains)
        teacher_ids = {t.id for t in self.teachers}
        for teacher in self.teachers:
            if not teacher.domains:
                errors.append(f"Enseignant {teacher.id!r} : domains est vide")
            unknown = sorted(teacher.domains - known_domains)
            if unknown:
                errors.append(f"Enseignant {teacher.id!r} : domaines inconnus {unknown}")
        for student in self.students:
            if student.domain not in known_domains:
                errors.append(f"Étudiant {student.id!r} : domaine inconnu {student.domain!r}")
            if student.supervisor_id not in teacher_ids:
                errors.append(
                    f"Étudiant {student.id!r} : encadrant inconnu {student.supervisor_id!r}"
                )
        return errors

    def _availability_errors(self) -> list[str]:
        """Contrôle les bornes des disponibilités de toutes les entités."""
        errors: list[str] = []
        owners: list[tuple[str, Availability]] = [
            (f"Enseignant {t.id!r}", t.availability) for t in self.teachers
        ]
        owners += [(f"Salle {r.id!r}", r.availability) for r in self.rooms]
        owners += [(f"Étudiant {s.id!r}", s.availability) for s in self.students]
        for label, availability in owners:
            for day in sorted(availability.slots_by_day):
                slots = availability.slots_by_day[day]
                if not 0 <= day < self.days:
                    errors.append(f"{label} : jour de disponibilité hors horizon ({day})")
                if not slots:
                    errors.append(f"{label} : jour {day} sans créneau")
                bad_slots = sorted(s for s in slots if not 0 <= s < self.slots_per_day)
                if bad_slots:
                    errors.append(f"{label} : jour {day}, créneaux hors bornes {bad_slots}")
        return errors


def _duplicates(values: Iterable[str]) -> list[str]:
    """Retourne, triées, les valeurs apparaissant plusieurs fois."""
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)