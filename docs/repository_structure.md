# Structure du Dépôt (Repository Structure)

Ce document détaille l'organisation de l'arborescence officielle du projet. Cette structure est strictement figée et ne doit subir aucune modification de nommage ou d'ajout de dossiers non répertoriés.

## Arborescence Complète

```text
Jury-scheduling/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── data/
│   ├── raw/
│   │   ├── instances_originales/
│   │   ├── manifest.csv
│   │   └── manifest.json
│   ├── processed/
│   │   └── instances_v4/
│   ├── solutions/
│   │   ├── greedy/
│   │   ├── cpsat/
│   │   └── hybrid/
│   └── benchmarks/
│       └── benchmark_results.csv
├── docs/
│   ├── project_overview.md
│   ├── repository_structure.md
│   ├── architecture.md
│   ... (autres fichiers de documentation)
├── scripts/
│   ├── migrate_instances.py
│   ├── validate_solution.py
│   ├── benchmark_all.py
│   └── generate_report.py
├── notebooks/
│   ├── 01_instance_analysis.ipynb
│   ├── 02_constraints_analysis.ipynb
│   ├── 03_metrics_analysis.ipynb
│   ├── 04_solver_comparison.ipynb
│   └── 05_final_results.ipynb
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── teacher.py
│   │   ├── student.py
│   │   ├── room.py
│   │   ├── session.py
│   │   ├── solution.py
│   │   ├── instance.py
│   │   └── enums.py
│   ├── parsers/
│   ├── preprocessing/
│   ├── validation/
│   ├── metrics/
│   ├── solvers/
│   │   ├── greedy/
│   │   ├── cpsat/
│   │   ├── local_search/
│   │   └── hybrid/
│   ├── benchmarking/
│   ├── exporters/
│   ├── visualization/
│   └── utils/
├── tests/
├── results/
└── references/