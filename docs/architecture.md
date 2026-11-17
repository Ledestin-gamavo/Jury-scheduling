# Architecture

## Objectif du projet

Le projet vise à résoudre automatiquement le problème de planification des soutenances académiques sous contraintes.

Le système doit :

- générer des solutions valides ;
- respecter toutes les contraintes du contrat ;
- optimiser plusieurs critères de qualité ;
- permettre la comparaison de différentes approches d'optimisation.

---

# Architecture générale

Instance JSON
        ↓
Parsers
        ↓
Core Domain
        ↓
Preprocessing
        ↓
Validation
        ↓
Metrics
        ↓
Greedy Solver
        ↓
Local Search
        ↓
CP-SAT Solver
        ↓
Hybrid Solver
        ↓
Benchmarking
        ↓
Visualization

---

# Philosophies d'architecture

## Séparation stricte des responsabilités

Chaque couche possède une responsabilité unique.

### Core

Représentation métier.

Ne contient :

- aucun algorithme
- aucun parsing
- aucune optimisation

### Parsers

Chargement des données.

Transforme :

JSON → objets Core

### Preprocessing

Accélère les solveurs.

Pré-calcule :

- disponibilités
- candidats jury
- filtres domaine

### Validation

Vérifie :

- contraintes dures
- cohérence des solutions

### Metrics

Évalue :

- qualité des solutions

### Solvers

Produisent ou améliorent des solutions.

---

# Dépendances autorisées

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

---

# Dépendances interdites

core -> anything

metrics -> validation

preprocessing -> solvers

validation -> solvers

---

# Pipeline d'optimisation

GreedySolver

Responsabilité :

- produire rapidement une solution valide

↓

LocalSearchSolver

Responsabilité :

- améliorer la solution

↓

CPSATSolver

Responsabilité :

- optimisation exacte

↓

HybridSolver

Responsabilité :

- combiner toutes les approches

---

# Principe fondamental

La validation est toujours la source officielle de vérité.

Une solution n'est considérée valide que si :

SolutionValidator.validate()

retourne :

valid=True