# Current Progress

## Project Status

### Phase 1 - Core Domain

✅ core/

- enums.py
- teacher.py
- student.py
- room.py
- session.py
- solution.py
- instance.py

Status:

- terminé
- stable

---

### Phase 2 - Parsing

✅ parsers/

- json_loader.py
- validation_parser.py
- parser_utils.py

Status:

- terminé
- stable

---

### Phase 3 - Preprocessing

✅ preprocessing/

- availability_matrix.py
- jury_candidates.py
- domain_filters.py
- preprocessing_context.py
- preprocessing_builder.py

Status:

- terminé
- stable

---

### Phase 4 - Validation

✅ validation/

- validation_result.py
- validator.py
- constraint_checks.py
- validation_utils.py

Status:

- terminé
- stable

---

### Phase 5 - Metrics

✅ metrics/

- teacher_presence_days.py
- teacher_idle_slots.py
- teacher_load_range.py
- supervisor_group_breaks.py
- distinct_jury_pairs.py
- evaluate.py

Status:

- terminé
- stable

Contract metrics implemented:

✅ teacher_presence_days

✅ teacher_idle_slots

✅ teacher_load_range

✅ supervisor_group_breaks

✅ distinct_jury_pairs

---

### Phase 6 - Greedy Solver

✅ solvers/greedy/

- greedy_config.py
- candidate_ranking.py
- session_builder.py
- repair.py
- greedy_solver.py

Status:

- terminé
- à tester

Features:

✅ MRV ordering

✅ Jury ranking

✅ Slot ranking

✅ Room ranking

✅ Repair operator

✅ Validation integration

✅ Metrics-driven construction

---

### Phase 7 - Local Search

✅ solvers/local_search/

- local_search_config.py
- neighborhood.py
- move_operator.py
- acceptance.py
- statistics.py
- local_search_solver.py

Status:

- terminé
- à tester

Neighborhoods:

✅ Change Slot

✅ Change Room

✅ Change Jury

✅ Swap Sessions

✅ Move Supervisor Block

Strategies:

✅ First Improvement

✅ Best Improvement

Metrics integration:

✅ SolutionEvaluator

Validation:

✅ SolutionValidator

Statistics:

✅ SearchStatistics

---

# Architecture Rules

Dependencies:

core
    ↑
parsers

core
    ↑
preprocessing

core
    ↑
validation

core
    ↑
metrics

core
preprocessing
validation
metrics
    ↑
solvers

Allowed:

solvers -> core

solvers -> preprocessing

solvers -> validation

solvers -> metrics

local_search -> greedy

Forbidden:

core -> preprocessing

core -> validation

core -> metrics

core -> solvers

metrics -> validation

preprocessing -> solvers

validation -> solvers

---

# Remaining Work

## Phase 8

⬜ documentation finalisation

- architecture.md
- module_reference.md
- solver_workflow.md
- metrics_reference.md
- contribution_guide.md

---

## Phase 9

⬜ CP-SAT Solver

Planned:

solvers/cpsat/

- cpsat_config.py
- model_builder.py
- variable_factory.py
- constraints.py
- objective.py
- warm_start.py
- cpsat_solver.py

---

## Phase 10

⬜ Hybrid Solver

Pipeline:

Greedy
    →
Local Search
    →
CP-SAT
    →
Hybrid Result

---

## Phase 11

⬜ Benchmarking

benchmark/

- benchmark_runner.py
- benchmark_report.py
- experiment_config.py

---

## Phase 12

⬜ Visualization

visualization/

- gantt.py
- metrics_dashboard.py
- export_tools.py

---

# Important Notes

Current implementation has not yet been fully validated on:

- demo_instance.json
- small_01.json
- medium instances
- large instances

Required before CP-SAT:

✅ unit testing

✅ integration testing

✅ validator.py verification

✅ metrics verification

✅ greedy verification

✅ local search verification