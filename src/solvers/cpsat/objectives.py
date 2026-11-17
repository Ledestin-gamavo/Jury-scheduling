"""Fonctions objectifs correspondant aux métriques du contrat."""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

from core.enums import Phase
from core.instance import Instance

from .variables import Candidate

__all__ = ["build_objective_terms"]


def _or_variable(
	model: cp_model.CpModel, variables: list[cp_model.IntVar], name: str
) -> cp_model.IntVar:
	result = model.NewBoolVar(name)
	if variables:
		model.AddMaxEquality(result, variables)
	else:
		model.Add(result == 0)
	return result


def _group_starts(
	model: cp_model.CpModel, occupied: list[cp_model.IntVar], prefix: str
) -> list[cp_model.IntVar]:
	starts: list[cp_model.IntVar] = []
	for slot, active in enumerate(occupied):
		start = model.NewBoolVar(f"{prefix}_{slot}")
		model.Add(start <= active)
		if slot == 0:
			model.Add(start == active)
		else:
			model.Add(start + occupied[slot - 1] <= 1)
			model.Add(start >= active - occupied[slot - 1])
		starts.append(start)
	return starts


def build_objective_terms(
	model: cp_model.CpModel, instance: Instance, candidates: list[Candidate]
) -> tuple[Any, Any, Any, Any, Any]:
	"""Construit les expressions des cinq métriques, dans l'ordre du contrat."""
	by_teacher_slot: dict[tuple[str, int, int], list[cp_model.IntVar]] = {}
	by_teacher: dict[str, list[cp_model.IntVar]] = {
		teacher.id: [] for teacher in instance.teachers
	}
	by_jury_pair: dict[tuple[str, str], list[cp_model.IntVar]] = {}
	online_slots: dict[tuple[str, int, int], list[cp_model.IntVar]] = {}
	final_slots: dict[tuple[str, int, str, int], list[cp_model.IntVar]] = {}
	final_by_supervisor: dict[str, list[cp_model.IntVar]] = {}

	for candidate in candidates:
		student = instance.student(candidate.student_id)
		attendees = [candidate.president_id, candidate.examiner_id]
		if candidate.phase is Phase.FINAL:
			attendees.append(student.supervisor_id)
			final_slots.setdefault(
				(student.supervisor_id, candidate.day, candidate.room_id or "", candidate.slot),
				[],
			).append(candidate.variable)
			final_by_supervisor.setdefault(student.supervisor_id, []).append(
				candidate.variable
			)
		else:
			online_slots.setdefault(
				(student.supervisor_id, candidate.day, candidate.slot), []
			).append(candidate.variable)
			by_jury_pair.setdefault(
				(candidate.president_id, candidate.examiner_id), []
			).append(candidate.variable)

		for teacher_id in dict.fromkeys(attendees):
			by_teacher.setdefault(teacher_id, []).append(candidate.variable)
			by_teacher_slot.setdefault(
				(teacher_id, candidate.day, candidate.slot), []
			).append(candidate.variable)

	teacher_occupancy: dict[tuple[str, int, int], cp_model.IntVar] = {}
	for teacher in instance.teachers:
		for day in instance.all_days:
			for slot in instance.all_slots:
				key = (teacher.id, day, slot)
				teacher_occupancy[key] = _or_variable(
					model,
					by_teacher_slot.get(key, []),
					f"teacher_{teacher.id}_{day}_{slot}_present",
				)

	presence_terms: list[cp_model.IntVar] = []
	idle_terms: list[cp_model.IntVar] = []
	for teacher in instance.teachers:
		for day in instance.all_days:
			occupied = [
				teacher_occupancy[(teacher.id, day, slot)]
				for slot in instance.all_slots
			]
			active = _or_variable(model, occupied, f"teacher_{teacher.id}_{day}_active")
			presence_terms.append(active)

			first = model.NewIntVar(0, instance.slots_per_day, f"first_{teacher.id}_{day}")
			last = model.NewIntVar(
				-instance.slots_per_day,
				instance.slots_per_day,
				f"last_{teacher.id}_{day}",
			)
			model.AddMinEquality(
				first,
				[
					slot + instance.slots_per_day * (1 - occupied[slot])
					for slot in instance.all_slots
				],
			)
			model.AddMaxEquality(
				last,
				[
					slot - instance.slots_per_day * (1 - occupied[slot])
					for slot in instance.all_slots
				],
			)
			idle = model.NewIntVar(
				0,
				max(0, instance.slots_per_day - 1),
				f"idle_{teacher.id}_{day}",
			)
			model.Add(idle == last - first + 1 - sum(occupied)).OnlyEnforceIf(active)
			model.Add(idle == 0).OnlyEnforceIf(active.Not())
			idle_terms.append(idle)

	loads = [sum(by_teacher[teacher.id]) for teacher in instance.teachers]
	minimum = model.NewIntVar(0, instance.num_required_sessions, "minimum_teacher_load")
	maximum = model.NewIntVar(0, instance.num_required_sessions, "maximum_teacher_load")
	model.AddMinEquality(minimum, loads)
	model.AddMaxEquality(maximum, loads)
	load_range = maximum - minimum

	jury_terms = [
		_or_variable(model, variables, f"jury_pair_{index}")
		for index, variables in enumerate(by_jury_pair.values())
	]
	group_break_terms: list[Any] = []
	for supervisor in instance.teachers:
		all_online_slots: list[cp_model.IntVar] = []
		for day in instance.days_for_phase(Phase.PREDEFENCE):
			occupied = [
				_or_variable(
					model,
					online_slots.get((supervisor.id, day, slot), []),
					f"online_{supervisor.id}_{day}_{slot}",
				)
				for slot in instance.all_slots
			]
			group_break_terms.extend(
				_group_starts(model, occupied, f"online_start_{supervisor.id}_{day}")
			)
			all_online_slots.extend(occupied)
		if all_online_slots:
			group_break_terms.append(
				-_or_variable(model, all_online_slots, f"online_active_{supervisor.id}")
			)

		for day in instance.days_for_phase(Phase.FINAL):
			for room in instance.rooms:
				occupied = [
					_or_variable(
						model,
						final_slots.get((supervisor.id, day, room.id, slot), []),
						f"final_{supervisor.id}_{day}_{room.id}_{slot}",
					)
					for slot in instance.all_slots
				]
				group_break_terms.extend(
					_group_starts(
						model,
						occupied,
						f"final_start_{supervisor.id}_{day}_{room.id}",
					)
				)
		if final_by_supervisor.get(supervisor.id):
			group_break_terms.append(
				-_or_variable(
					model,
					final_by_supervisor[supervisor.id],
					f"final_active_{supervisor.id}",
				)
			)

	return (
		sum(presence_terms),
		sum(idle_terms),
		load_range,
		sum(group_break_terms),
		sum(jury_terms),
	)
