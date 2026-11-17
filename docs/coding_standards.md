# Standards de Développement

## Objectif

Ce document définit les règles de développement du projet **Jury Scheduling**.

Les objectifs sont :

- maintenir un code lisible ;
- faciliter la maintenance ;
- simplifier l'intégration de nouveaux contributeurs ;
- garantir la cohérence de l'architecture ;
- limiter la dette technique.

Tous les contributeurs doivent respecter ces règles.

---

# Version Python

Version cible :

```text
Python 3.10+
```

Tout le code doit rester compatible avec Python 3.10.

---

# Politique de Typage

Le typage est obligatoire.

Exemple :

```python
def validate(
    instance: Instance
) -> ValidationResult:
    ...
```

À éviter :

```python
def validate(instance):
    ...
```

---

# Type Hints

Toutes les fonctions publiques doivent préciser :

- les types des paramètres ;
- le type de retour.

Exemple :

```python
def teacher_load_range(
    instance: Instance,
    solution: Solution,
) -> int:
    ...
```

---

# Utilisation des Dataclasses

Préférer :

```python
@dataclass(frozen=True)
```

pour :

- les modèles métier ;
- les objets résultat ;
- les objets de configuration.

Exemples :

```python
Teacher
Student
Room
Session
ValidationResult
EvaluationResult
GreedyConfig
LocalSearchConfig
```

Les dataclasses mutables doivent rester exceptionnelles.

---

# Documentation

Toute fonction publique doit posséder une docstring.

Sont concernées :

- les classes ;
- les méthodes ;
- les fonctions.

Exemple :

```python
def evaluate(
    instance: Instance,
    solution: Solution,
) -> EvaluationResult:
    """
    Évalue une solution valide.

    Args:
        instance: Instance du problème.
        solution: Solution valide.

    Returns:
        Résultat de l'évaluation.
    """
```

---

# Conventions de Nommage

## Classes

Utiliser le format PascalCase.

Exemples :

```python
Teacher
Student
Room
ValidationResult
GreedySolver
LocalSearchSolver
```

---

## Fonctions

Utiliser le format snake_case.

Exemples :

```python
teacher_presence_days()

build_preprocessing()

validate_solution()

compute_candidate_slots()
```

---

## Variables

Utiliser le format snake_case.

Exemples :

```python
teacher_id

candidate_pairs

available_slots
```

---

## Constantes

Utiliser le format UPPER_CASE.

Exemples :

```python
DEFAULT_WEIGHTS

MAX_ITERATIONS

DEFAULT_CONFIG
```

---

# Organisation des Imports

Respecter l'ordre suivant :

```python
# bibliothèque standard

from dataclasses import dataclass

# bibliothèques externes

from ortools.sat.python import cp_model

# modules du projet

from core.instance import Instance
```

---

# Règles d'Architecture

Les dépendances autorisées sont :

```text
parsers -> core

preprocessing -> core

validation -> core

metrics -> core

solvers -> core
solvers -> preprocessing
solvers -> validation
solvers -> metrics
```

Les dépendances interdites sont :

```text
core -> preprocessing

core -> validation

core -> metrics

core -> solvers

metrics -> validation

preprocessing -> solvers

validation -> solvers
```

---

# Règle de Séparation des Responsabilités

## Core

Le module Core contient uniquement :

- les objets métier ;
- les structures de données.

Il ne doit contenir :

- aucun solveur ;
- aucune métrique ;
- aucune validation ;
- aucun parsing.

---

## Validation

Le module Validation contient :

- toutes les contraintes dures ;
- toutes les vérifications officielles.

Aucune contrainte ne doit être réécrite ailleurs.

---

## Metrics

Le module Metrics contient :

- tous les critères d'évaluation.

Les métriques doivent rester :

- déterministes ;
- reproductibles ;
- uniquement en lecture.

---

## Solvers

Les solveurs peuvent :

- produire une solution ;
- modifier une solution de travail ;
- consulter les métriques ;
- consulter la validation.

Les solveurs ne doivent jamais :

- modifier une instance ;
- contourner le validateur ;
- dupliquer les contraintes métier.

---

# Réutilisation du Code

Éviter tout copier-coller.

Si une fonction existe déjà :

```python
teacher_attendance()

SolutionValidator()

SolutionEvaluator()
```

elle doit être réutilisée.

La duplication de logique métier est interdite.

---

# Gestion de l'Aléatoire

Tout comportement aléatoire doit être reproductible.

Toujours utiliser :

```python
rng = Random(config.random_seed)
```

Ne jamais utiliser :

```python
random.random()
```

sans gestion explicite de la graine.

---

# Gestion des Erreurs

Toujours lever des exceptions explicites.

Préférer :

```python
raise ValueError(
    "Identifiant enseignant inconnu"
)
```

À :

```python
raise Exception()
```

---

# Mutabilité

Les objets suivants doivent être considérés comme immuables :

```python
Instance
Teacher
Student
Room
```

Les solveurs peuvent modifier uniquement :

```python
ScheduleState

Solution de travail
```

pendant l'exécution.

---

# Performance

Privilégier les pré-calculs.

Toujours réutiliser :

```python
AvailabilityMatrix

JuryCandidates

DomainFilters
```

Éviter les recalculs inutiles dans les solveurs.

---

# Validation Obligatoire

Avant toute évaluation :

```text
Solution
    ↓
Validation
    ↓
Metrics
```

Une solution invalide ne doit jamais être évaluée.

Toujours utiliser :

```python
SolutionValidator
```

avant :

```python
SolutionEvaluator
```

---

# Tests

Toute nouvelle fonctionnalité doit être vérifiée.

Tests minimums :

- cas nominal ;
- cas limites ;
- entrées invalides ;
- violations de contraintes.

---

# Conventions Git

Préfixes recommandés :

```text
feat:
fix:
refactor:
test:
docs:
```

Exemples :

```text
feat(local-search): ajout du voisinage swap

fix(metrics): correction du calcul de load_range

refactor(preprocessing): simplification du cache jury

docs(architecture): mise à jour des dépendances

test(validation): ajout des tests de conflit de salle
```

---

# Checklist Avant Commit

Vérifier :

- le projet compile ;
- le typage est complet ;
- les docstrings sont présentes ;
- l'architecture est respectée ;
- aucune duplication de logique métier n'a été introduite ;
- current_progress.md est à jour si nécessaire.

---

# Principe Fondamental

Le validateur est la source officielle de vérité.

Si un solveur, une métrique ou une heuristique contredit le validateur :

```text
Le validateur a toujours raison.
```