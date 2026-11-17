# État d'Avancement du Projet

## Objectif du document

Ce document sert de référence officielle pour toute l'équipe.

Avant de développer une fonctionnalité, chaque membre doit consulter ce document afin de connaître :

- l'état réel du projet ;
- les modules terminés ;
- les modules en cours ;
- les contraintes d'architecture ;
- les dépendances autorisées ;
- l'ordre officiel des développements.

---

# Jalon global

## ✅ Documentation terminée

Fichiers :

```text
README.md

docs/
├── project_overview.md
├── repository_structure.md
├── architecture.md
├── development_guide.md
└── current_progress.md
```

---

## ✅ Core terminé

```text
src/core/

✅ enums.py
✅ teacher.py
✅ student.py
✅ room.py
✅ session.py
✅ solution.py
✅ instance.py
```

### Responsabilités

Le module `core` contient :

- toutes les entités métier ;
- les énumérations ;
- les disponibilités ;
- les structures de planning ;
- les index métier ;
- les contrôles structurels d'instance.

Aucun accès JSON.

Aucune logique de résolution.

Aucune métrique.

---

## ✅ Parsers terminés

```text
src/parsers/

✅ __init__.py
✅ schema_checker.py
✅ instance_loader.py
✅ solution_loader.py
```

### Responsabilités

Transformation :

```text
JSON
  ↓
Objets métiers
```

Fonctions principales :

```python
load_instance(...)
load_solution(...)
```

### Garanties

- lecture JSON stricte ;
- validation de format ;
- vérification des schémas ;
- conversion vers les objets du module core.

---

## ✅ Preprocessing terminé

```text
src/preprocessing/

✅ __init__.py
✅ availability_matrix.py
✅ domain_filters.py
✅ jury_candidates.py
✅ instance_statistics.py
```

### Responsabilités

Pré-calcul des structures utilisées par les solveurs.

---

### availability_matrix.py

Fournit :

```python
AvailabilityMatrix
```

Fonctionnalités :

- accès temps constant aux disponibilités ;
- créneaux autorisés par phase ;
- créneaux candidats ;
- intersections de disponibilités ;
- index temporels utilisables dans CP-SAT.

---

### domain_filters.py

Fournit :

```python
DomainFilters
```

Fonctionnalités :

- enseignants couvrant un domaine ;
- examinateurs possibles ;
- présidents possibles ;
- diagnostics d'instance ;
- statistiques par domaine.

---

### jury_candidates.py

Fournit :

```python
JuryCandidates
```

Fonctionnalités :

- présidents candidats ;
- examinateurs candidats ;
- binômes candidats ;
- partage des calculs entre étudiants similaires ;
- support CP-SAT futur.

---

### instance_statistics.py

Fournit :

```python
InstanceStatistics
```

Fonctionnalités :

- statistiques globales ;
- densités ;
- capacités ;
- diagnostics ;
- rapports benchmark.

---

## ✅ Validation terminée

```text
src/validation/

✅ __init__.py
✅ availability_constraints.py
✅ no_overlap_constraints.py
✅ capacity_constraints.py
✅ continuity_constraints.py
✅ role_constraints.py
✅ room_constraints.py
✅ solution_validator.py
```

### Responsabilités

Validation complète d'une solution.

Aucune optimisation.

Aucune métrique.

---

### Contrôles implémentés

#### Disponibilités

```text
availability_constraints.py
```

Vérifie :

- disponibilité étudiants ;
- disponibilité enseignants ;
- disponibilité salles.

---

#### Non-chevauchements

```text
no_overlap_constraints.py
```

Vérifie :

- conflits enseignants ;
- conflits étudiants ;
- conflits salles.

---

#### Capacités

```text
capacity_constraints.py
```

Vérifie :

- max_sessions_per_day enseignants ;
- max_sessions_per_day salles.

---

#### Continuité

```text
continuity_constraints.py
```

Vérifie :

- même président ;
- même examinateur ;
- cohérence pré-soutenance → finale.

---

#### Rôles

```text
role_constraints.py
```

Vérifie :

- rôle président ;
- rôle examinateur ;
- couverture des domaines ;
- distinction des membres du jury.

---

#### Salles

```text
room_constraints.py
```

Vérifie :

- salle obligatoire en finale ;
- salle interdite en pré-soutenance ;
- existence de la salle.

---

#### Validateur principal

```python
SolutionValidator
ValidationResult
```

Fonction principale :

```python
validator.validate(instance, solution)
```

Retour :

```python
ValidationResult
```

avec :

```python
valid
errors
warnings
```

---

## Architecture disponible aujourd'hui

Le pipeline complet actuellement fonctionnel est :

```text
JSON
  ↓
Parsers
  ↓
Core
  ↓
Preprocessing
  ↓
Validation
```

---

# Modules restant à développer

## ⏳ Metrics

Prochaine étape.

```text
src/metrics/

teacher_presence_days.py
teacher_idle_slots.py
teacher_load_range.py
supervisor_group_breaks.py
distinct_jury_pairs.py
evaluate.py
```

Responsabilité :

Calcul du score d'une solution.

---

## ⬜ Solvers

```text
src/solvers/

greedy/
cpsat/
local_search/
hybrid/
```

Responsabilité :

Génération des solutions.

---

## ⬜ Exporters

```text
src/exporters/
```

Responsabilité :

Export JSON et CSV.

---

## ⬜ Benchmarking

```text
src/benchmarking/
```

Responsabilité :

Mesure et comparaison des solveurs.

---

## ⬜ Visualization

```text
src/visualization/
```

Responsabilité :

Rapports visuels et tableaux de bord.

---

# Règles d'architecture

## Interdiction

```text
core -> parsers
core -> preprocessing
core -> validation
core -> metrics
core -> solvers
```

---

## Autorisé

```text
parsers -> core

preprocessing -> core

validation -> core

metrics -> core

solvers -> core
solvers -> preprocessing
solvers -> validation
solvers -> metrics

benchmarking -> parsers
benchmarking -> solvers
benchmarking -> validation
benchmarking -> metrics
```

---

# État réel du projet

```text
✅ Documentation

✅ Core

✅ Parsers

✅ Preprocessing

✅ Validation

⏳ Metrics

⬜ Greedy Solver

⬜ CPSAT Solver

⬜ Local Search

⬜ Hybrid Solver

⬜ Exporters

⬜ Benchmarking

⬜ Visualization
```

---

# Prochaine étape officielle

```text
src/metrics/
```

Objectif :

Transformer une solution valide en score d'optimisation afin de comparer :

- GreedySolver ;
- CPSATSolver ;
- HybridSolver.