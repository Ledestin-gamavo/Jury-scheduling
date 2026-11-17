# Solveur Hybride

## Objectif

Le solveur hybride représente la stratégie de résolution la plus avancée du projet.

Son rôle est de combiner les avantages :

- des heuristiques constructives ;
- de la recherche locale ;
- de la programmation par contraintes.

L'objectif est d'obtenir une solution de meilleure qualité que celle produite par chaque solveur individuellement.

---

# Philosophie

Aucune méthode de résolution n'est parfaite.

Chaque approche possède ses propres forces :

## Greedy Solver

Forces :

- rapide ;
- robuste ;
- produit rapidement une solution valide.

Faiblesses :

- fortement dépendant des choix locaux ;
- qualité limitée.

---

## Local Search Solver

Forces :

- améliore la solution existante ;
- réduit plusieurs métriques.

Faiblesses :

- bloqué dans des optima locaux ;
- exploration limitée.

---

## CP-SAT Solver

Forces :

- optimisation avancée ;
- preuve d'optimalité possible.

Faiblesses :

- coût de calcul élevé ;
- sensible à la taille du problème.

---

## Hybrid Solver

Principe :

```text
utiliser chaque méthode
pour ce qu'elle fait le mieux
```

---

# Position dans l'Architecture

Pipeline complet :

```text
Instance
    ↓
Preprocessing
    ↓
Greedy Solver
    ↓
Local Search Solver
    ↓
CP-SAT Solver
    ↓
Solution Finale
```

Le solveur hybride orchestre ce pipeline.

---

# Architecture du Module

Répertoire :

```text
src/solvers/hybrid/
```

Contenu :

```text
__init__.py

hybrid_solver.py
```

---

# Pipeline de Résolution

Le solveur hybride exécute trois étapes successives.

---

## Étape 1

Construction d'une solution valide.

Solveur utilisé :

```text
Greedy Solver
```

Objectifs :

- satisfaire toutes les contraintes ;
- construire une première solution réalisable.

Sortie :

```text
Solution G0
```

---

## Étape 2

Amélioration locale.

Solveur utilisé :

```text
Local Search Solver
```

Objectifs :

- réduire les métriques ;
- améliorer le score global.

Entrée :

```text
G0
```

Sortie :

```text
L0
```

---

## Étape 3

Optimisation avancée.

Solveur utilisé :

```text
CP-SAT Solver
```

Objectifs :

- optimiser davantage la solution ;
- exploiter le warm start ;
- éventuellement prouver l'optimalité.

Entrée :

```text
L0
```

Sortie :

```text
C0
```

---

# Représentation du Pipeline

```text
Greedy
    ↓
Solution initiale

Local Search
    ↓
Solution améliorée

CP-SAT
    ↓
Solution finale
```

---

# Warm Start

Le solveur hybride exploite :

```text
local search solution
```

comme solution initiale de CP-SAT.

---

## Avantages

Le solveur CP-SAT démarre avec :

```text
une solution déjà valide
```

et déjà relativement optimisée.

Cela permet :

- d'accélérer la recherche ;
- d'améliorer les bornes ;
- de trouver plus rapidement de bonnes solutions.

---

# Validation Entre les Étapes

Chaque solution intermédiaire doit être validée.

Pipeline :

```text
Solveur
    ↓
Validation
    ↓
Étape suivante
```

---

## Greedy

```text
Validation obligatoire
```

avant Local Search.

---

## Local Search

```text
Validation obligatoire
```

avant CP-SAT.

---

## CP-SAT

Validation finale obligatoire.

---

# Gestion des Échecs

Le solveur hybride doit rester robuste.

---

## Cas 1

Greedy échoue.

Résultat :

```text
Hybrid échoue
```

Le pipeline s'arrête.

---

## Cas 2

Local Search n'améliore pas.

Résultat :

```text
utilisation directe
de la solution Greedy
```

comme warm start.

---

## Cas 3

CP-SAT ne trouve pas mieux.

Résultat :

```text
solution Local Search
```

conservée.

---

## Cas 4

CP-SAT améliore.

Résultat :

```text
solution CP-SAT
```

retenue.

---

# Sélection de la Meilleure Solution

Le solveur conserve toujours :

```text
la meilleure solution valide connue
```

au cours de l'exécution.

Ainsi :

```text
Aucune régression n'est autorisée.
```

---

# Configuration

Configuration prévue :

```python
HybridConfig
```

---

## Paramètres Principaux

```text
run_greedy

run_local_search

run_cpsat

enable_warm_start
```

---

## Paramètres de Temps

```text
local_search_time_limit

cpsat_time_limit
```

---

# Rapport de Résolution

Le solveur retourne :

```python
HybridReport
```

contenant :

```text
solution

validation

evaluation

statistics

elapsed_time

status
```

---

# Statistiques

Le rapport doit inclure :

---

## Partie Greedy

```text
temps

statut

étudiants non placés
```

---

## Partie Local Search

```text
score initial

score final

amélioration
```

---

## Partie CP-SAT

```text
objectif

gap

temps

statut
```

---

# Évaluation

La comparaison repose sur :

```python
SolutionEvaluator
```

et les métriques :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

---

# Avantages

Le solveur hybride combine :

✅ rapidité du Greedy

✅ amélioration du Local Search

✅ puissance du CP-SAT

✅ exploitation du warm start

✅ meilleure qualité globale

---

# Limites

Le coût de calcul est supérieur à celui des solveurs individuels.

Les performances dépendent :

- de la qualité de la solution Greedy ;
- de la qualité de la recherche locale ;
- du temps accordé à CP-SAT.

---

# Cas d'Utilisation Recommandé

Le solveur hybride doit être considéré comme :

```text
la stratégie de résolution principale
```

pour les expériences finales du projet.

Les autres solveurs servent :

- de références ;
- de baselines ;
- de composants intermédiaires.

---

# Conclusion

Le solveur hybride constitue l'aboutissement de l'architecture du projet.

En combinant :

```text
Greedy
    +
Local Search
    +
CP-SAT
```

il vise à produire les meilleures solutions possibles tout en conservant la robustesse et la modularité du système.

Il représente la stratégie qui sera utilisée pour les benchmarks, les expérimentations et l'évaluation finale du projet.