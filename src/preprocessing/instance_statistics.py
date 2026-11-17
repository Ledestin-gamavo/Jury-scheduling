"""Statistiques descriptives d'une instance.

Ce module produit, en une passe, les indicateurs utiles aux benchmarks, aux
rapports et au choix des paramètres des solveurs :

* **effectifs** : étudiants, finales, pré-soutenances, enseignants, salles,
  domaines, encadrants ;
* **horizon et créneaux autorisés** : jours, créneaux par jour, nombre de
  créneaux autorisés pour chaque phase ;
* **densités de disponibilité** : proportion de créneaux autorisés où les
  acteurs sont disponibles (moyenne, minimum, maximum) ;
* **indicateurs de capacité** : nombre de présences d'enseignants requises et
  bornes supérieures grossières de la capacité en séances.

Les bornes de capacité sont **grossières** : pour un enseignant, on somme sur
chaque jour autorisé ``min(max_sessions_per_day, nombre de créneaux disponibles
ce jour-là)`` ; pour les salles, même calcul sur les jours de finales. Elles ne
tiennent compte ni des chevauchements, ni des jurys, ni des étudiants. Elles
servent à repérer une instance très tendue, non à prouver une faisabilité.

Présences requises (règles du contrat) : une pré-soutenance mobilise 2
enseignants (président, examinateur) ; une finale en mobilise 3 (président,
examinateur, encadrant-rapporteur).

Ce module ne dépend que de ``core`` et de ``preprocessing``.
"""

from __future__ import annotations
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from core.enums import Phase, Role
from core.instance import Instance
from .availability_matrix import AvailabilityMatrix, group_slots_by_day
from .domain_filters import DomainFilters

__all__ = ["DensityStats", "InstanceStatistics", "compute_instance_statistics"]


@dataclass(frozen=True)
class DensityStats:
    """Moyenne, minimum et maximum de densités (valeurs dans ``[0, 1]``).

    Attributes:
        mean: Densité moyenne.
        minimum: Densité minimale.
        maximum: Densité maximale.
    """

    mean: float
    minimum: float
    maximum: float

    @classmethod
    def from_values(cls, values: Sequence[float]) -> DensityStats | None:
        """Construit les statistiques à partir de valeurs ; ``None`` si la séquence est vide."""
        if not values:
            return None
        return cls(sum(values) / len(values), min(values), max(values))


@dataclass(frozen=True)
class InstanceStatistics:
    """Statistiques descriptives d'une instance (objet immuable).

    Densité d'un acteur pour une phase : nombre de créneaux de la période de la
    phase où il est disponible, divisé par le nombre de créneaux autorisés pour
    la phase (``0.0`` si la phase n'a aucun créneau). Les densités de finale
    des étudiants ne portent que sur les étudiants admissibles.

    Attributes:
        instance_id: Identifiant de l'instance.
        size: Classe de taille (``"small"``, ``"medium"``…).
        seed: Graine de génération.
        num_days: Nombre de jours de l'horizon.
        slots_per_day: Nombre de créneaux par jour.
        horizon_time_slots: ``num_days * slots_per_day``.
        num_predefence_days: Nombre de jours de pré-soutenance.
        num_final_days: Nombre de jours de finale.
        predefence_time_slots: Nombre de créneaux autorisés en pré-soutenance.
        final_time_slots: Nombre de créneaux autorisés en finale.
        authorized_time_slots: Somme des deux (les périodes sont disjointes).
        num_students: Nombre d'étudiants.
        num_final_students: Nombre d'étudiants admissibles (= nombre de finales).
        num_non_final_students: Nombre d'étudiants non admissibles.
        num_predefence_sessions: Nombre de pré-soutenances à planifier.
        num_final_sessions: Nombre de finales à planifier.
        num_sessions: Nombre total de séances à planifier.
        num_teachers: Nombre d'enseignants.
        num_eligible_presidents: Enseignants habilités présidents.
        num_eligible_examiners: Enseignants habilités examinateurs.
        num_rooms: Nombre de salles.
        num_domains: Nombre de domaines.
        num_supervisors: Nombre d'encadrants distincts.
        max_students_per_supervisor: Plus grand nombre d'étudiants d'un encadrant.
        mean_students_per_supervisor: Moyenne d'étudiants par encadrant.
        students_per_domain: Couples ``(domaine, nombre d'étudiants)``.
        domains_without_examiner: Domaines avec étudiants mais sans examinateur possible.
        student_predefence_density: Densités des étudiants en pré-soutenance.
        student_final_density: Densités des étudiants admissibles en finale (``None`` si aucun).
        teacher_predefence_density: Densités des enseignants en pré-soutenance.
        teacher_final_density: Densités des enseignants en finale.
        room_final_density: Densités des salles en finale.
        required_teacher_attendances: Présences d'enseignants requises (2 par
            pré-soutenance, 3 par finale).
        teacher_capacity_upper_bound: Borne supérieure grossière du nombre de
            séances que les enseignants peuvent assurer.
        final_room_capacity_upper_bound: Borne supérieure grossière du nombre
            de finales que les salles peuvent accueillir.
    """

    # Identité
    instance_id: str
    size: str
    seed: int
    # Horizon
    num_days: int
    slots_per_day: int
    horizon_time_slots: int
    num_predefence_days: int
    num_final_days: int
    predefence_time_slots: int
    final_time_slots: int
    authorized_time_slots: int
    # Effectifs
    num_students: int
    num_final_students: int
    num_non_final_students: int
    num_predefence_sessions: int
    num_final_sessions: int
    num_sessions: int
    num_teachers: int
    num_eligible_presidents: int
    num_eligible_examiners: int
    num_rooms: int
    num_domains: int
    num_supervisors: int
    max_students_per_supervisor: int
    mean_students_per_supervisor: float
    students_per_domain: tuple[tuple[str, int], ...]
    domains_without_examiner: tuple[str, ...]
    # Densités
    student_predefence_density: DensityStats | None
    student_final_density: DensityStats | None
    teacher_predefence_density: DensityStats | None
    teacher_final_density: DensityStats | None
    room_final_density: DensityStats | None
    # Capacités
    required_teacher_attendances: int
    teacher_capacity_upper_bound: int
    final_room_capacity_upper_bound: int

    # Indicateurs dérivés
    @property
    def teacher_load_ratio(self) -> float | None:
        """Rapport ``présences requises / capacité enseignants`` (``None`` si capacité nulle).

        Une valeur proche de 1 (ou supérieure) signale une instance très tendue.
        """
        if self.teacher_capacity_upper_bound == 0:
            return None
        return self.required_teacher_attendances / self.teacher_capacity_upper_bound

    @property
    def room_load_ratio(self) -> float | None:
        """Rapport ``finales / capacité des salles`` (``None`` si capacité nulle)."""
        if self.final_room_capacity_upper_bound == 0:
            return None
        return self.num_final_sessions / self.final_room_capacity_upper_bound

    # Représentations
    def as_dict(self) -> dict[str, Any]:
        """Retourne les statistiques sous forme de dictionnaire plat.

        Les valeurs sont des types simples (``int``, ``float``, ``str``,
        ``None``, ``list``, ``dict``), pratiques pour une ligne de benchmark ou
        un rapport. Chaque densité est aplatie en ``<nom>_mean``, ``<nom>_min``
        et ``<nom>_max`` (``None`` si la densité n'existe pas).
        """
        result: dict[str, Any] = {
            "instance_id": self.instance_id,
            "size": self.size,
            "seed": self.seed,
            "num_days": self.num_days,
            "slots_per_day": self.slots_per_day,
            "horizon_time_slots": self.horizon_time_slots,
            "num_predefence_days": self.num_predefence_days,
            "num_final_days": self.num_final_days,
            "predefence_time_slots": self.predefence_time_slots,
            "final_time_slots": self.final_time_slots,
            "authorized_time_slots": self.authorized_time_slots,
            "num_students": self.num_students,
            "num_final_students": self.num_final_students,
            "num_non_final_students": self.num_non_final_students,
            "num_predefence_sessions": self.num_predefence_sessions,
            "num_final_sessions": self.num_final_sessions,
            "num_sessions": self.num_sessions,
            "num_teachers": self.num_teachers,
            "num_eligible_presidents": self.num_eligible_presidents,
            "num_eligible_examiners": self.num_eligible_examiners,
            "num_rooms": self.num_rooms,
            "num_domains": self.num_domains,
            "num_supervisors": self.num_supervisors,
            "max_students_per_supervisor": self.max_students_per_supervisor,
            "mean_students_per_supervisor": self.mean_students_per_supervisor,
            "students_per_domain": dict(self.students_per_domain),
            "domains_without_examiner": list(self.domains_without_examiner),
            "required_teacher_attendances": self.required_teacher_attendances,
            "teacher_capacity_upper_bound": self.teacher_capacity_upper_bound,
            "final_room_capacity_upper_bound": self.final_room_capacity_upper_bound,
            "teacher_load_ratio": self.teacher_load_ratio,
            "room_load_ratio": self.room_load_ratio,
        }
        densities = {
            "student_predefence_density": self.student_predefence_density,
            "student_final_density": self.student_final_density,
            "teacher_predefence_density": self.teacher_predefence_density,
            "teacher_final_density": self.teacher_final_density,
            "room_final_density": self.room_final_density,
        }
        for name, stats in densities.items():
            result[f"{name}_mean"] = stats.mean if stats else None
            result[f"{name}_min"] = stats.minimum if stats else None
            result[f"{name}_max"] = stats.maximum if stats else None
        return result

    def to_text(self) -> str:
        """Retourne un rapport texte lisible (en français) des statistiques."""

        def density(label: str, stats: DensityStats | None) -> str:
            if stats is None:
                return f"  {label} : sans objet"
            return (
                f"  {label} : moyenne {stats.mean:.1%}, "
                f"min {stats.minimum:.1%}, max {stats.maximum:.1%}"
            )

        def ratio(value: float | None) -> str:
            return "sans objet" if value is None else f"{value:.2f}"

        lines = [
            f"Instance {self.instance_id} (taille : {self.size}, graine : {self.seed})",
            "Horizon et créneaux autorisés :",
            f"  jours : {self.num_days} (pré-soutenance : {self.num_predefence_days}, "
            f"finale : {self.num_final_days}), créneaux par jour : {self.slots_per_day}",
            f"  créneaux autorisés : pré-soutenance {self.predefence_time_slots}, "
            f"finale {self.final_time_slots}, total {self.authorized_time_slots} "
            f"(horizon : {self.horizon_time_slots})",
            "Effectifs :",
            f"  étudiants : {self.num_students} (admissibles : {self.num_final_students}, "
            f"non admissibles : {self.num_non_final_students})",
            f"  séances à planifier : {self.num_sessions} (pré-soutenances : "
            f"{self.num_predefence_sessions}, finales : {self.num_final_sessions})",
            f"  enseignants : {self.num_teachers} (présidents : {self.num_eligible_presidents}, "
            f"examinateurs : {self.num_eligible_examiners}), salles : {self.num_rooms}",
            f"  domaines : {self.num_domains}, encadrants : {self.num_supervisors} "
            f"(max {self.max_students_per_supervisor} étudiants, "
            f"moyenne {self.mean_students_per_supervisor:.2f})",
            "Densités de disponibilité :",
            density("étudiants, pré-soutenance", self.student_predefence_density),
            density("étudiants, finale", self.student_final_density),
            density("enseignants, pré-soutenance", self.teacher_predefence_density),
            density("enseignants, finale", self.teacher_final_density),
            density("salles, finale", self.room_final_density),
            "Capacités (bornes grossières) :",
            f"  présences d'enseignants requises : {self.required_teacher_attendances} "
            f"pour une capacité de {self.teacher_capacity_upper_bound} "
            f"(rapport : {ratio(self.teacher_load_ratio)})",
            f"  finales : {self.num_final_sessions} pour une capacité de salles de "
            f"{self.final_room_capacity_upper_bound} (rapport : {ratio(self.room_load_ratio)})",
        ]
        if self.domains_without_examiner:
            lines.append(
                "Alerte : domaines sans examinateur possible : "
                + ", ".join(self.domains_without_examiner)
            )
        return "\n".join(lines)


def _daily_capacity(slots: Sequence[tuple[int, int]], daily_cap: int) -> int:
    """Somme, sur les jours, de ``min(plafond, nombre de créneaux disponibles)``."""
    return sum(min(daily_cap, len(day_slots)) for day_slots in group_slots_by_day(slots).values())


def compute_instance_statistics(
    instance: Instance,
    *,
    availability: AvailabilityMatrix | None = None,
    domain_filters: DomainFilters | None = None,
) -> InstanceStatistics:
    """Calcule les statistiques descriptives d'une instance.

    Args:
        instance: Instance à analyser.
        availability: Matrice de disponibilités déjà construite (réutilisée).
            Construite si absente.
        domain_filters: Filtres de domaine déjà construits (réutilisés).
            Construits si absents.

    Returns:
        Les statistiques de l'instance.
    """
    matrix = availability if availability is not None else AvailabilityMatrix(instance)
    filters = domain_filters if domain_filters is not None else DomainFilters(instance)

    predefence_total = len(matrix.phase_time_slots(Phase.PREDEFENCE))
    final_total = len(matrix.phase_time_slots(Phase.FINAL))

    def density(counts: Sequence[int], total: int) -> DensityStats | None:
        if total == 0:
            return DensityStats.from_values([0.0] * len(counts))
        return DensityStats.from_values([count / total for count in counts])

    final_students = instance.final_students()
    student_predefence = density(
        [len(matrix.student_slots(s.id, Phase.PREDEFENCE)) for s in instance.students],
        predefence_total,
    )
    student_final = density(
        [len(matrix.student_slots(s.id, Phase.FINAL)) for s in final_students], final_total
    )
    teacher_predefence = density(
        [len(matrix.teacher_slots(t.id, Phase.PREDEFENCE)) for t in instance.teachers],
        predefence_total,
    )
    teacher_final = density(
        [len(matrix.teacher_slots(t.id, Phase.FINAL)) for t in instance.teachers], final_total
    )
    room_final = density([len(matrix.room_slots(r.id)) for r in instance.rooms], final_total)

    teacher_capacity = sum(
        _daily_capacity(matrix.teacher_slots(t.id, phase), t.max_sessions_per_day)
        for t in instance.teachers
        for phase in Phase
    )
    room_capacity = sum(
        _daily_capacity(matrix.room_slots(r.id), r.max_sessions_per_day) for r in instance.rooms
    )

    num_students = instance.num_students
    num_final = len(final_students)
    supervisor_counts = Counter(s.supervisor_id for s in instance.students)
    num_supervisors = len(supervisor_counts)

    return InstanceStatistics(
        instance_id=instance.instance_id,
        size=instance.size.value,
        seed=instance.seed,
        num_days=instance.days,
        slots_per_day=instance.slots_per_day,
        horizon_time_slots=matrix.horizon_size,
        num_predefence_days=len(set(instance.predefence_days)),
        num_final_days=len(set(instance.final_defence_days)),
        predefence_time_slots=predefence_total,
        final_time_slots=final_total,
        authorized_time_slots=predefence_total + final_total,
        num_students=num_students,
        num_final_students=num_final,
        num_non_final_students=num_students - num_final,
        num_predefence_sessions=num_students,
        num_final_sessions=num_final,
        num_sessions=num_students + num_final,
        num_teachers=instance.num_teachers,
        num_eligible_presidents=len(instance.teachers_with_role(Role.PRESIDENT)),
        num_eligible_examiners=len(instance.teachers_with_role(Role.EXAMINER)),
        num_rooms=instance.num_rooms,
        num_domains=len(instance.domains),
        num_supervisors=num_supervisors,
        max_students_per_supervisor=max(supervisor_counts.values(), default=0),
        mean_students_per_supervisor=(num_students / num_supervisors if num_supervisors else 0.0),
        students_per_domain=tuple(
            (stats.domain, stats.num_students) for stats in filters.all_statistics()
        ),
        domains_without_examiner=filters.domains_without_examiner(),
        student_predefence_density=student_predefence,
        student_final_density=student_final,
        teacher_predefence_density=teacher_predefence,
        teacher_final_density=teacher_final,
        room_final_density=room_final,
        required_teacher_attendances=2 * num_students + 3 * num_final,
        teacher_capacity_upper_bound=teacher_capacity,
        final_room_capacity_upper_bound=room_capacity,
    )