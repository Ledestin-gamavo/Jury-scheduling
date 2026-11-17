import pytest
pytest.importorskip("ortools", reason="OR-Tools requis pour les tests CP-SAT")

from core.enums import Availability, InstanceSize, Phase, Role
from core.instance import Instance
from core.room import Room
from core.student import Student
from core.teacher import Teacher
from solvers.cpsat.cpsat_solver import CPSATStatus, CPSATSolver


def test_cpsat_finds_and_validates_a_complete_schedule() -> None:
	availability = Availability({0: frozenset({0, 1}), 1: frozenset({0, 1})})
	teachers = (
		Teacher.build("supervisor", {"ai"}, (), 2, availability),
		Teacher.build("president", {"ai"}, {Role.PRESIDENT}, 2, availability),
		Teacher.build("examiner", {"ai"}, {Role.EXAMINER}, 2, availability),
	)
	student = Student("student", "ai", "supervisor", True, availability)
	room = Room("room", 2, Availability({1: frozenset({0, 1})}))
	instance = Instance(
		instance_id="tiny",
		size=InstanceSize.DEMO,
		seed=0,
		days=2,
		slots_per_day=2,
		predefence_days=(0,),
		final_defence_days=(1,),
		domains=("ai",),
		teachers=teachers,
		rooms=(room,),
		students=(student,),
	)

	report = CPSATSolver().solve_with_report(instance)

	assert report.status is CPSATStatus.OPTIMAL
	assert report.valid
	assert len(report.solution) == 2
	assert report.solution.get("student", Phase.PREDEFENCE) is not None
	assert report.solution.get("student", Phase.FINAL) is not None
	assert report.evaluation is not None
	assert report.evaluation.as_vector() == (5, 0, 1, 0, 1)


def test_cpsat_counts_supervisor_group_breaks_across_days() -> None:
	teacher_availability = Availability(
		{day: frozenset({0}) for day in range(4)}
	)
	teachers = (
		Teacher.build("supervisor", {"ai"}, (), 1, teacher_availability),
		Teacher.build("president", {"ai"}, {Role.PRESIDENT}, 1, teacher_availability),
		Teacher.build("examiner", {"ai"}, {Role.EXAMINER}, 1, teacher_availability),
	)
	students = (
		Student("student_a", "ai", "supervisor", True, Availability({0: {0}, 2: {0}})),
		Student("student_b", "ai", "supervisor", True, Availability({1: {0}, 3: {0}})),
	)
	room = Room("room", 1, Availability({2: {0}, 3: {0}}))
	instance = Instance(
		instance_id="separated-days",
		size=InstanceSize.DEMO,
		seed=0,
		days=4,
		slots_per_day=1,
		predefence_days=(0, 1),
		final_defence_days=(2, 3),
		domains=("ai",),
		teachers=teachers,
		rooms=(room,),
		students=students,
	)

	report = CPSATSolver().solve_with_report(instance)

	assert report.status is CPSATStatus.OPTIMAL
	assert report.valid
	assert report.evaluation is not None
	assert report.evaluation.as_vector() == (10, 0, 2, 2, 1)
