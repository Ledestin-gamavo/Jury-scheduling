# Guide de Développement

## Objectif

Ce document décrit l'environnement de développement, les bonnes pratiques, les conventions du projet et le workflow recommandé pour les contributeurs.

Toute nouvelle contribution doit respecter les règles définies dans :

- architecture.md
- coding_standards.md
- constraints_catalog.md

---

# Vue d'Ensemble du Projet

Le projet implémente un système complet de planification de soutenances académiques.

Pipeline principal :

```text
Instance JSON
        ↓
Parsers
        ↓
Core
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
```

---

# Environnement Recommandé

## Version Python

```text
Python 3.10+
```

Version recommandée :

```text
Python 3.11+
```

---

## Création d'un Environnement Virtuel

Windows :

```powershell
python -m venv .venv

.venv\Scripts\activate
```

Linux :

```bash
python -m venv .venv

source .venv/bin/activate
```

---

# Installation des Dépendances

Fichier :

```text
requirements.txt
```

Installation :

```bash
pip install -r requirements.txt
```

---

# Structure Générale

Code source :

```text
src/
```

Documentation :

```text
docs/
```

Tests :

```text
tests/
```

Exemples :

```text
examples/
```

---

# Configuration PYTHONPATH

Le projet utilise le dossier :

```text
src/
```

comme racine logique.

Avant d'exécuter les tests :

Windows :

```powershell
$env:PYTHONPATH="src"
```

Linux :

```bash
export PYTHONPATH=src
```

---

# Vérification du Projet

## Vérification Syntaxique

Depuis la racine :

```bash
python -m compileall src
```

Cette commande doit réussir sans erreur.

---

## Vérification des Imports

```python
from parsers import *
from preprocessing import *
from validation import *
from metrics import *

from solvers.greedy import *
from solvers.local_search import *
```

Aucune erreur ne doit être produite.

---

# Workflow de Développement

Avant de modifier un module :

1. Lire current_progress.md
2. Lire architecture.md
3. Vérifier les dépendances autorisées
4. Comprendre les modules existants

---

## Étape 1

Créer ou modifier le code.

---

## Étape 2

Compiler :

```bash
python -m compileall src
```

---

## Étape 3

Exécuter les tests.

---

## Étape 4

Vérifier la validation.

---

## Étape 5

Mettre à jour :

```text
current_progress.md
```

si nécessaire.

---

# Développement d'un Nouveau Module

Chaque nouveau module doit :

- être documenté ;
- être typé ;
- respecter les conventions de nommage ;
- posséder des docstrings.

---

# Développement d'un Nouveau Solveur

Tout solveur doit suivre l'architecture suivante :

```python
class ExampleSolver:
    def solve(
        self,
        instance: Instance,
    ) -> Solution:
        ...
```

Il doit :

✅ produire une solution

✅ utiliser preprocessing

✅ utiliser validation

✅ utiliser metrics

---

Il ne doit jamais :

❌ modifier Instance

❌ dupliquer SolutionValidator

❌ dupliquer SolutionEvaluator

---

# Validation

Le validateur constitue la référence officielle.

Avant toute évaluation :

```text
Solution
    ↓
Validation
    ↓
Metrics
```

Toujours :

```python
validator = SolutionValidator()

result = validator.validate(
    instance,
    solution
)
```

---

# Évaluation

L'évaluation est réalisée via :

```python
SolutionEvaluator
```

Exemple :

```python
evaluator = SolutionEvaluator()

evaluation = evaluator.evaluate(
    instance,
    solution
)
```

---

# Débogage

Pour déboguer :

1. Tester les modules individuellement.
2. Tester les imports.
3. Tester les solveurs sur une petite instance.
4. Vérifier les contraintes avant les métriques.

Priorité :

```text
Validation
    ↓
Metrics
    ↓
Solveurs
```

---

# Gestion de l'Aléatoire

Tous les solveurs doivent être reproductibles.

Utiliser :

```python
Random(config.random_seed)
```

Exemple :

```python
rng = Random(42)
```

---

# Gestion des Instances

Les instances doivent être considérées comme immuables.

Ne jamais modifier :

```python
Instance

Teacher

Student

Room
```

pendant la résolution.

---

# Guide de Tests

Ordre recommandé :

```text
Core
    ↓
Preprocessing
    ↓
Validation
    ↓
Metrics
    ↓
Greedy
    ↓
Local Search
    ↓
CP-SAT
    ↓
Hybrid
```

---

# Vérification d'une Solution

Toujours vérifier :

```python
validation.valid
```

avant :

```python
evaluation
```

---

# Bonnes Pratiques

✅ petites fonctions

✅ forte modularité

✅ documentation systématique

✅ typage strict

✅ dépendances minimales

✅ réutilisation du code existant

---

# Mauvaises Pratiques

❌ copier-coller la logique de validation

❌ contourner les métriques

❌ multiplier les dépendances

❌ modifier les objets métier

❌ ajouter une contrainte dans un solveur

---

# Gestion Git

Préfixes recommandés :

```text
feat:
fix:
docs:
refactor:
test:
```

Exemples :

```text
feat(cpsat): add room conflict constraints

fix(validation): correct capacity verification

docs(metrics): update definitions

test(greedy): add repair tests
```

---

# Checklist Avant Commit

Vérifier :

- compilation réussie ;
- tests réussis ;
- validation correcte ;
- typage complet ;
- documentation à jour ;
- architecture respectée.

---

# Principe Fondamental

Une solution est correcte uniquement si :

```python
SolutionValidator.validate(...)
```

retourne :

```python
valid=True
```

Le validateur constitue l'autorité finale du projet.