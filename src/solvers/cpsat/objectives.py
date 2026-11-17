"""Construction exacte des cinq objectifs définis par Metrics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import DefaultDict

from core.enums import Phase
from core.instance import Instance
from ortools.sat.python import cp_model

from metrics.evaluate import DEFAULT_WEIGHTS, METRIC_NAMES
from .variables import CPSATVariables


def _or_equivalence(
    model: cp_model.CpModel,
    target: cp_model.IntVar,
    literals: list[cp_model.IntVar],
) -> None:
    """Impose target = OR(literals), y compris lorsque la liste est vide."""
    if not literals:
        model.Add(target == 0)
        return
    for literal in literals:
        model.Add(target >= literal)
    model.Add(target <= sum(literals))


def _and_not_previous(
    model: cp_model.CpModel,
    target: cp_model.IntVar,
    current: cp_model.IntVar,
    previous: list[cp_model.IntVar],
) -> None:
    """Impose target = current AND NOT(any(previous))."""
    model.Add(target <= current)
    for literal in previous:
        model.Add(target + literal <= 1)
    model.Add(target >= current - sum(previous))


def add_objective(
    model: cp_model.CpModel,
    instance: Instance,
    variables: CPSATVariables,
    weights: Mapping[str, int] | None = None,
) -> dict[str, cp_model.IntVar]:
    """Ajoute la scalarisation pondérée des cinq métriques du projet.

    Les formulations reproduisent les définitions de ``metrics_definition.md``
    et du contrat v4.0 : présences par enseignant/jour, intervalles intra-journée,
    étendue des charges, groupes par phase/superviseur et paires ordonnées.
    """
    selected_weights = dict(DEFAULT_WEIGHTS)
    if weights is not None:
        selected_weights.update(weights)
    assignments = variables.assignments
    candidates = variables.candidates

    teacher_slot: DefaultDict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    teacher_day: DefaultDict[tuple[str, int], list[cp_model.IntVar]] = defaultdict(list)
    for candidate in candidates:
        variable = assignments[candidate.key]
        teacher_ids = (candidate.president_id, candidate.examiner_id)
        if candidate.phase is Phase.FINAL:
            teacher_ids += (candidate.supervisor_id,)
        for teacher_id in teacher_ids:
            teacher_slot[(teacher_id, candidate.day, candidate.slot)].append(variable)
            teacher_day[(teacher_id, candidate.day)].append(variable)

    # f1 : somme des jours de présence de chaque enseignant.
    presence_terms: list[cp_model.IntVar] = []
    # f2 : last_slot - first_slot + 1 - nombre de séances, par enseignant/jour.
    idle_terms: list[cp_model.IntVar] = []
    load_counts: list[cp_model.IntVar] = []
    for teacher in instance.teachers:
        total_count = model.NewIntVar(0, instance.num_required_sessions, f"load_{teacher.id}")
        all_teacher_vars = [v for (tid, _day), values in teacher_day.items()
                            if tid == teacher.id for v in values]
        model.Add(total_count == sum(all_teacher_vars))
        load_counts.append(total_count)
        for day in instance.all_days:
            occupied: list[cp_model.IntVar] = []
            for slot in instance.all_slots:
                occ = model.NewBoolVar(f"teacher_{teacher.id}_{day}_{slot}_present")
                values = teacher_slot[(teacher.id, day, slot)]
                model.Add(sum(values) == occ)
                occupied.append(occ)
            active = model.NewBoolVar(f"teacher_{teacher.id}_{day}_active")
            model.Add(sum(occupied) >= active)
            model.Add(sum(occupied) <= instance.slots_per_day * active)
            presence_terms.append(active)
            first_flags: list[cp_model.IntVar] = []
            last_flags: list[cp_model.IntVar] = []
            for slot, occ in enumerate(occupied):
                first = model.NewBoolVar(f"first_{teacher.id}_{day}_{slot}")
                last = model.NewBoolVar(f"last_{teacher.id}_{day}_{slot}")
                _and_not_previous(model, first, occ, occupied[:slot])
                _and_not_previous(model, last, occ, occupied[slot + 1:])
                first_flags.append(first)
                last_flags.append(last)
            first_slot = model.NewIntVar(0, instance.slots_per_day - 1,
                                         f"first_slot_{teacher.id}_{day}")
            last_slot = model.NewIntVar(0, instance.slots_per_day - 1,
                                        f"last_slot_{teacher.id}_{day}")
            model.Add(first_slot == sum(i * flag for i, flag in enumerate(first_flags)))
            model.Add(last_slot == sum(i * flag for i, flag in enumerate(last_flags)))
            span = model.NewIntVar(0, instance.slots_per_day, f"span_{teacher.id}_{day}")
            model.Add(span == last_slot - first_slot + active)
            idle = model.NewIntVar(0, instance.slots_per_day, f"idle_{teacher.id}_{day}")
            model.Add(idle == span - sum(occupied))
            idle_terms.append(idle)

    f1 = model.NewIntVar(0, instance.num_teachers * instance.days, "metric_teacher_presence_days")
    model.Add(f1 == sum(presence_terms))
    f2 = model.NewIntVar(0, instance.num_teachers * instance.days * instance.slots_per_day,
                         "metric_teacher_idle_slots")
    model.Add(f2 == sum(idle_terms))

    # f3 : max(load_t) - min(load_t), y compris les enseignants inutilisés.
    max_load = model.NewIntVar(0, instance.num_required_sessions, "maximum_teacher_load")
    min_load = model.NewIntVar(0, instance.num_required_sessions, "minimum_teacher_load")
    model.AddMaxEquality(max_load, load_counts)
    model.AddMinEquality(min_load, load_counts)
    f3 = model.NewIntVar(0, instance.num_required_sessions, "metric_teacher_load_range")
    model.Add(f3 == max_load - min_load)

    # f4a : groupes de pré-soutenance par superviseur et par jour.
    online_by_supervisor_slot: DefaultDict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    for candidate in candidates:
        if candidate.phase is Phase.PREDEFENCE:
            online_by_supervisor_slot[(candidate.supervisor_id, candidate.day,
                                       candidate.slot)].append(assignments[candidate.key])
    online_break_terms: list[cp_model.IntVar] = []
    supervisors = tuple(dict.fromkeys(s.supervisor_id for s in instance.students))
    for supervisor_id in supervisors:
        group_starts: list[cp_model.IntVar] = []
        for day in instance.days_for_phase(Phase.PREDEFENCE):
            occupied: list[cp_model.IntVar] = []
            for slot in instance.all_slots:
                occ = model.NewBoolVar(f"online_{supervisor_id}_{day}_{slot}")
                _or_equivalence(model, occ, online_by_supervisor_slot[(supervisor_id, day, slot)])
                occupied.append(occ)
            for slot, occ in enumerate(occupied):
                start = model.NewBoolVar(f"online_group_start_{supervisor_id}_{day}_{slot}")
                _and_not_previous(model, start, occ, occupied[max(0, slot - 1):slot])
                group_starts.append(start)
        group_count = model.NewIntVar(0, instance.num_students, f"online_groups_{supervisor_id}")
        model.Add(group_count == sum(group_starts))
        breaks = model.NewIntVar(0, instance.num_students, f"online_breaks_{supervisor_id}")
        model.AddMaxEquality(breaks, [group_count - 1, 0])
        online_break_terms.append(breaks)

    # f4b : groupes de finales par superviseur, jour et salle.
    final_by_supervisor_room_slot: DefaultDict[tuple[str, int, str, int], list[cp_model.IntVar]] = defaultdict(list)
    for candidate in candidates:
        if candidate.phase is Phase.FINAL and candidate.room_id is not None:
            final_by_supervisor_room_slot[(candidate.supervisor_id, candidate.day,
                                           candidate.room_id, candidate.slot)].append(
                                               assignments[candidate.key])
    final_break_terms: list[cp_model.IntVar] = []
    for supervisor_id in supervisors:
        group_starts = []
        for day in instance.days_for_phase(Phase.FINAL):
            for room in instance.rooms:
                occupied_by_supervisor: list[cp_model.IntVar] = []
                for slot in instance.all_slots:
                    occ = model.NewBoolVar(
                        f"final_{supervisor_id}_{day}_{room.id}_{slot}"
                    )
                    _or_equivalence(
                        model, occ,
                        final_by_supervisor_room_slot[(supervisor_id, day, room.id, slot)],
                    )
                    occupied_by_supervisor.append(occ)
                for slot, occ in enumerate(occupied_by_supervisor):
                    start = model.NewBoolVar(
                        f"final_group_start_{supervisor_id}_{day}_{room.id}_{slot}"
                    )
                    previous_same = occupied_by_supervisor[slot - 1:slot]
                    _and_not_previous(model, start, occ, previous_same)
                    group_starts.append(start)
        group_count = model.NewIntVar(0, instance.num_students, f"final_groups_{supervisor_id}")
        model.Add(group_count == sum(group_starts))
        breaks = model.NewIntVar(0, instance.num_students, f"final_breaks_{supervisor_id}")
        model.AddMaxEquality(breaks, [group_count - 1, 0])
        final_break_terms.append(breaks)

    f4 = model.NewIntVar(0, 2 * instance.num_students, "metric_supervisor_group_breaks")
    model.Add(f4 == sum(online_break_terms) + sum(final_break_terms))

    # f5 : nombre de couples ordonnés distincts employés en pré-soutenance.
    pairs = tuple(sorted({(c.president_id, c.examiner_id) for c in candidates
                          if c.phase is Phase.PREDEFENCE}))
    pair_used: list[cp_model.IntVar] = []
    for index, pair in enumerate(pairs):
        pair_vars = [assignments[c.key] for c in candidates
                     if c.phase is Phase.PREDEFENCE
                     and (c.president_id, c.examiner_id) == pair]
        used = model.NewBoolVar(f"jury_pair_used_{index}")
        _or_equivalence(model, used, pair_vars)
        pair_used.append(used)
    f5 = model.NewIntVar(0, max(1, len(pairs)), "metric_distinct_jury_pairs")
    model.Add(f5 == sum(pair_used))

    metrics = dict(zip(METRIC_NAMES, (f1, f2, f3, f4, f5)))
    model.Minimize(sum(selected_weights[name] * metrics[name] for name in METRIC_NAMES))
    return metrics
