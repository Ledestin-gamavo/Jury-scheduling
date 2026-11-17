"""Contraintes dures du modèle CP-SAT."""

from __future__ import annotations

from ortools.sat.python import cp_model

from core.enums import Phase
from core.instance import Instance

from .variables import Candidate

__all__ = ["add_constraints"]


def add_constraints(
	model: cp_model.CpModel, instance: Instance, candidates: list[Candidate]
) -> None:
	"""Ajoute couverture, continuité, disponibilités et capacités.

	Les disponibilités et la composition des jurys sont déjà intégrées à la
	génération des candidats; les contraintes ci-dessous relient les choix.
	"""
	by_student_phase: dict[tuple[str, Phase], list[Candidate]] = {}
	by_student_pair_phase: dict[tuple[str, str, str, Phase], list[cp_model.IntVar]] = {}
	for candidate in candidates:
		by_student_phase.setdefault((candidate.student_id, candidate.phase), []).append(
			candidate
		)
		key = (
			candidate.student_id,
			candidate.president_id,
			candidate.examiner_id,
			candidate.phase,
		)
		by_student_pair_phase.setdefault(key, []).append(candidate.variable)

	for student in instance.students:
		for phase in student.required_phases():
			variables = [
				candidate.variable
				for candidate in by_student_phase.get((student.id, phase), [])
			]
			model.Add(sum(variables) == 1)

		if student.eligible_final:
			pairs = {
				(candidate.president_id, candidate.examiner_id)
				for candidate in by_student_phase.get((student.id, Phase.PREDEFENCE), [])
			} | {
				(candidate.president_id, candidate.examiner_id)
				for candidate in by_student_phase.get((student.id, Phase.FINAL), [])
			}
			for president_id, examiner_id in pairs:
				pre_variables = by_student_pair_phase.get(
					(student.id, president_id, examiner_id, Phase.PREDEFENCE), []
				)
				final_variables = by_student_pair_phase.get(
					(student.id, president_id, examiner_id, Phase.FINAL), []
				)
				model.Add(sum(pre_variables) == sum(final_variables))

	teacher_slots: dict[tuple[str, int, int], list[cp_model.IntVar]] = {}
	teacher_days: dict[tuple[str, int], list[cp_model.IntVar]] = {}
	student_slots: dict[tuple[str, int, int], list[cp_model.IntVar]] = {}
	room_slots: dict[tuple[str, int, int], list[cp_model.IntVar]] = {}
	room_days: dict[tuple[str, int], list[cp_model.IntVar]] = {}

	for candidate in candidates:
		attendees = [candidate.president_id, candidate.examiner_id]
		if candidate.phase is Phase.FINAL:
			attendees.append(instance.student(candidate.student_id).supervisor_id)
		for teacher_id in dict.fromkeys(attendees):
			teacher_slots.setdefault(
				(teacher_id, candidate.day, candidate.slot), []
			).append(candidate.variable)
			teacher_days.setdefault((teacher_id, candidate.day), []).append(
				candidate.variable
			)
		student_slots.setdefault(
			(candidate.student_id, candidate.day, candidate.slot), []
		).append(candidate.variable)
		if candidate.room_id is not None:
			room_slots.setdefault(
				(candidate.room_id, candidate.day, candidate.slot), []
			).append(candidate.variable)
			room_days.setdefault((candidate.room_id, candidate.day), []).append(
				candidate.variable
			)

	for variables in (
		*teacher_slots.values(),
		*student_slots.values(),
		*room_slots.values(),
	):
		model.Add(sum(variables) <= 1)
	for (teacher_id, _day), variables in teacher_days.items():
		model.Add(sum(variables) <= instance.teacher(teacher_id).max_sessions_per_day)
	for (room_id, _day), variables in room_days.items():
		model.Add(sum(variables) <= instance.room(room_id).max_sessions_per_day)
