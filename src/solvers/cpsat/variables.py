"""Création et indexation des variables de décision CP-SAT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.enums import Phase, Role
from core.instance import Instance
from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class AssignmentCandidate:
    """Affectation admissible d'un étudiant à une phase et un créneau."""

    student_id: str
    phase: Phase
    president_id: str
    examiner_id: str
    room_id: str | None
    day: int
    slot: int
    supervisor_id: str

    @property
    def key(self) -> tuple[str, Phase, str, str, str | None, int, int]:
        """Clé déterministe identifiant entièrement l'affectation."""
        return (
            self.student_id,
            self.phase,
            self.president_id,
            self.examiner_id,
            self.room_id,
            self.day,
            self.slot,
        )


@dataclass
class CPSATVariables:
    """Registre des variables d'affectation et de leurs candidats."""

    candidates: tuple[AssignmentCandidate, ...]
    assignments: dict[tuple[str, Phase, str, str, str | None, int, int], cp_model.IntVar]
    by_student_phase: dict[tuple[str, Phase], list[cp_model.IntVar]]


def generate_candidates(instance: Instance) -> tuple[AssignmentCandidate, ...]:
    """Énumère uniquement les affectations compatibles avec les données statiques.

    Les conflits entre séances et les capacités globales restent des contraintes
    du modèle. Les filtres ici ne font que retirer les affectations impossibles
    individuellement (rôle, domaine, disponibilité, période et composition).
    """
    candidates: list[AssignmentCandidate] = []
    presidents = tuple(t for t in instance.teachers if t.can_serve_as(Role.PRESIDENT))
    examiners = tuple(t for t in instance.teachers if t.can_serve_as(Role.EXAMINER))
    for student in instance.students:
        supervisor = instance.teacher(student.supervisor_id)
        for phase in student.required_phases():
            days = instance.days_for_phase(phase)
            for president in presidents:
                if president.id == supervisor.id and phase is Phase.FINAL:
                    continue
                for examiner in examiners:
                    if examiner.id == president.id or not examiner.covers_domain(student.domain):
                        continue
                    if phase is Phase.FINAL and examiner.id == supervisor.id:
                        continue
                    for day in days:
                        for slot in instance.all_slots:
                            if not student.is_available(day, slot):
                                continue
                            if not president.is_available(day, slot) or not examiner.is_available(day, slot):
                                continue
                            if phase is Phase.PREDEFENCE:
                                candidates.append(AssignmentCandidate(
                                    student.id, phase, president.id, examiner.id, None,
                                    day, slot, supervisor.id,
                                ))
                                continue
                            if not supervisor.is_available(day, slot):
                                continue
                            for room in instance.rooms:
                                if room.is_available(day, slot):
                                    candidates.append(AssignmentCandidate(
                                        student.id, phase, president.id, examiner.id, room.id,
                                        day, slot, supervisor.id,
                                    ))
    return tuple(candidates)


def create_variables(
    model: cp_model.CpModel,
    instance: Instance,
) -> CPSATVariables:
    """Crée une variable booléenne par affectation admissible.

    Args:
        model: Modèle CP-SAT à enrichir.
        instance: Instance métier immuable.

    Returns:
        Registre des candidats, variables et index par étudiant/phase.
    """
    candidates = generate_candidates(instance)
    assignments: dict[tuple[str, Phase, str, str, str | None, int, int], cp_model.IntVar] = {}
    by_student_phase: dict[tuple[str, Phase], list[cp_model.IntVar]] = {
        key: [] for key in instance.required_sessions()
    }
    for index, candidate in enumerate(candidates):
        variable = model.NewBoolVar(f"assign_{index}")
        assignments[candidate.key] = variable
        by_student_phase[(candidate.student_id, candidate.phase)].append(variable)
    return CPSATVariables(candidates, assignments, by_student_phase)
