"""Variables de décision clairsemées du modèle CP-SAT."""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from core.enums import Phase
from core.instance import Instance

__all__ = ["Candidate", "create_candidates"]


@dataclass(frozen=True)
class Candidate:
	"""Une affectation légale possible pour une séance."""

	student_id: str
	phase: Phase
	president_id: str
	examiner_id: str
	day: int
	slot: int
	room_id: str | None
	variable: cp_model.IntVar

	@property
	def key(self) -> tuple[str, Phase, str, str, int, int, str | None]:
		return (
			self.student_id,
			self.phase,
			self.president_id,
			self.examiner_id,
			self.day,
			self.slot,
			self.room_id,
		)


def create_candidates(model: cp_model.CpModel, instance: Instance) -> list[Candidate]:
	"""Crée une variable booléenne par affectation métier admissible."""
	candidates: list[Candidate] = []
	presidents = instance.eligible_presidents()

	for student in instance.students:
		examiners = instance.eligible_examiners_for_student(student.id)
		for phase in student.required_phases():
			for president in presidents:
				if phase is Phase.FINAL and president.id == student.supervisor_id:
					continue
				for examiner in examiners:
					if examiner.id == president.id or (
						phase is Phase.FINAL and examiner.id == student.supervisor_id
					):
						continue
					for day in instance.days_for_phase(phase):
						for slot in instance.all_slots:
							if not student.is_available(day, slot):
								continue
							if not president.is_available(day, slot):
								continue
							if not examiner.is_available(day, slot):
								continue

							if phase is Phase.FINAL:
								supervisor = instance.teacher(student.supervisor_id)
								if not supervisor.is_available(day, slot):
									continue
								for room in instance.rooms:
									if not room.is_available(day, slot):
										continue
									variable = model.NewBoolVar(
										f"assign_{student.id}_final_{president.id}_"
										f"{examiner.id}_{room.id}_{day}_{slot}"
									)
									candidates.append(
										Candidate(
											student.id,
											phase,
											president.id,
											examiner.id,
											day,
											slot,
											room.id,
											variable,
										)
									)
							else:
								variable = model.NewBoolVar(
									f"assign_{student.id}_pre_{president.id}_"
									f"{examiner.id}_{day}_{slot}"
								)
								candidates.append(
									Candidate(
										student.id,
										phase,
										president.id,
										examiner.id,
										day,
										slot,
										None,
										variable,
									)
								)
	return candidates
