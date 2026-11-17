"""Traduction des contraintes dures dans le modèle CP-SAT."""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

from core.enums import Phase
from core.instance import Instance
from ortools.sat.python import cp_model

from .variables import CPSATVariables


def add_hard_constraints(
    model: cp_model.CpModel,
    instance: Instance,
    variables: CPSATVariables,
) -> None:
    """Ajoute les contraintes d'affectation, de ressources et de continuité.

    Les règles métier sont traduites depuis le contrat v4.0. La validation
    officielle reste exclusivement confiée à ``SolutionValidator``.
    """
    candidates = variables.candidates
    assignments = variables.assignments

    # C2-C4 : exactement une affectation pour chaque phase requise.
    for key in instance.required_sessions():
        model.Add(sum(variables.by_student_phase[key]) == 1)

    # C17 : le binôme président/examinateur est identique entre les phases.
    for student in instance.students:
        if not student.eligible_final:
            continue
        pairs = {
            (c.president_id, c.examiner_id)
            for c in candidates if c.student_id == student.id
        }
        for president_id, examiner_id in pairs:
            pre = [assignments[c.key] for c in candidates
                   if c.student_id == student.id and c.phase is Phase.PREDEFENCE
                   and c.president_id == president_id and c.examiner_id == examiner_id]
            final = [assignments[c.key] for c in candidates
                     if c.student_id == student.id and c.phase is Phase.FINAL
                     and c.president_id == president_id and c.examiner_id == examiner_id]
            model.Add(sum(pre) == sum(final))

    # C10-C11 et C21 : ressources non chevauchantes.
    teacher_slot: DefaultDict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    student_slot: DefaultDict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    room_slot: DefaultDict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    teacher_day: DefaultDict[tuple[str, int], list[cp_model.IntVar]] = defaultdict(list)
    room_day: DefaultDict[tuple[str, int], list[cp_model.IntVar]] = defaultdict(list)

    for candidate in candidates:
        variable = assignments[candidate.key]
        student_slot[(candidate.student_id, candidate.day, candidate.slot)].append(variable)
        attending = (candidate.president_id, candidate.examiner_id)
        if candidate.phase is Phase.FINAL:
            attending += (candidate.supervisor_id,)
        for teacher_id in attending:
            teacher_slot[(teacher_id, candidate.day, candidate.slot)].append(variable)
            teacher_day[(teacher_id, candidate.day)].append(variable)
        if candidate.room_id is not None:
            room_slot[(candidate.room_id, candidate.day, candidate.slot)].append(variable)
            room_day[(candidate.room_id, candidate.day)].append(variable)

    for values in teacher_slot.values():
        model.Add(sum(values) <= 1)
    for values in student_slot.values():
        model.Add(sum(values) <= 1)
    for values in room_slot.values():
        model.Add(sum(values) <= 1)

    # C22-C23 : plafonds journaliers, toutes phases pour les enseignants.
    for teacher in instance.teachers:
        for day in instance.all_days:
            model.Add(sum(teacher_day[(teacher.id, day)]) <= teacher.max_sessions_per_day)
    for room in instance.rooms:
        for day in instance.all_days:
            model.Add(sum(room_day[(room.id, day)]) <= room.max_sessions_per_day)
