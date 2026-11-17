# Solveur Glouton (Greedy Solver)

## Objectif

Le solveur glouton constitue la première méthode de résolution du projet.

Son rôle est de construire rapidement une solution valide respectant l'ensemble des contraintes du problème.

Il fournit :

- une première solution exploitable ;
- un point de départ pour la recherche locale ;
- un point de départ pour le solveur CP-SAT.

---

# Position dans l'Architecture

Le Greedy Solver intervient après les phases :

```text
Core
    ↓
Preprocessing
    ↓
Validation
```

et avant :

```text
Local Search
    ↓
CP-SAT
```

Pipeline :

```text
Instance
    ↓
Preprocessing
    ↓
Greedy Solver
    ↓
Solution Valide
```

---

# Philosophie

La stratégie gloutonne consiste à construire progressivement le planning.

À chaque étape :

```text
Choisir le meilleur candidat localement
```

sans explorer exhaustivement toutes les possibilités futures.

Cette approche privilégie :

- la rapidité ;
- la simplicité ;
- la robustesse.

---

# Structure du Module

Répertoire :

```text
src/solvers/greedy/
```

Contenu :

```text
__init__.py

greedy_config.py

candidate_ranking.py

session_builder.py

repair.py

greedy_solver.py
```

---

# Vue Générale de l'Algorithme

Le solveur exécute cinq étapes principales.

```text
1. Construction des pré-soutenances

2. Construction des finales

3. Validation

4. Réparation locale

5. Évaluation
```

---

# Étape 1 : Construction des Pré-soutenances

Les étudiants sont traités dans un ordre intelligent.

Méthode utilisée :

```text
MRV
(Minimum Remaining Values)
```

Le principe consiste à traiter en priorité :

```text
les étudiants les plus difficiles à placer
```

afin de réduire le risque d'échec ultérieur.

---

# Heuristique MRV

Chaque étudiant reçoit un niveau de difficulté.

Cette difficulté dépend notamment :

```text
nombre de créneaux possibles

nombre de jurys possibles
```

Les étudiants les plus contraints sont traités en premier.

---

# Sélection du Jury

Pour chaque étudiant :

```text
plusieurs binômes
(président, examinateur)
```

peuvent être admissibles.

Le module :

```text
candidate_ranking.py
```

classe ces binômes.

---

## Critères Utilisés

### Réutilisation des Jurys

Un jury déjà utilisé est favorisé.

Objectif :

```text
réduire distinct_jury_pairs
```

---

### Charge Enseignant

Les enseignants peu sollicités sont favorisés.

Objectif :

```text
améliorer teacher_load_range
```

---

# Sélection du Créneau

Après sélection du jury :

```text
créneau candidat
```

↓

```text
classement
```

↓

```text
meilleur créneau
```

---

## Critères Utilisés

### Jours de Présence

Favoriser les jours déjà occupés.

Objectif :

```text
teacher_presence_days
```

---

### Temps Morts

Favoriser les créneaux qui réduisent les trous.

Objectif :

```text
teacher_idle_slots
```

---

### Regroupement Encadrant

Favoriser les créneaux proches d'autres étudiants du même encadrant.

Objectif :

```text
supervisor_group_breaks
```

---

# Étape 2 : Construction des Finales

Les finales sont construites après les pré-soutenances.

Le principe fondamental est :

```text
continuité du jury
```

Le jury utilisé en finale doit être identique à celui utilisé en pré-soutenance.

---

# Sélection de la Salle

Les salles admissibles sont classées.

Critère principal :

```text
regroupement de l'encadrant
```

Le solveur cherche à maintenir autant que possible les étudiants d'un même encadrant dans des blocs cohérents.

---

# SessionBuilder

Classe centrale :

```python
SessionBuilder
```

Responsabilités :

- vérifier les contraintes dures ;
- trouver les créneaux admissibles ;
- construire les séances ;
- assurer la continuité du jury.

---

# ScheduleState

Classe :

```python
ScheduleState
```

Responsable de l'état courant du planning.

Elle maintient :

```text
occupations enseignants

occupations étudiants

occupations salles

charges

utilisation des jurys

groupes encadrants
```

---

# Contraintes Vérifiées

Le solveur respecte notamment :

```text
Disponibilités

Conflits enseignants

Conflits étudiants

Conflits salles

Capacités journalières

Compatibilité domaine

Rôles académiques

Continuité du jury
```

---

# Étape 3 : Validation

Une fois la construction terminée :

```python
SolutionValidator
```

est exécuté.

Il constitue la validation officielle.

Aucune solution n'est considérée valide sans cette étape.

---

# Étape 4 : Réparation Locale

Lorsque certains étudiants restent non placés :

```text
RepairOperator
```

est utilisé.

---

## Principe

### Conservation

Les étudiants déjà cohérents sont conservés.

---

### Réinsertion

Les étudiants non planifiés sont replanifiés.

---

### Éviction Contrôlée

Si nécessaire :

```text
quelques étudiants sont retirés
```

pour libérer des ressources.

Ils sont ensuite réinsérés.

---

# Réparation par Éviction

Le solveur privilégie l'éviction :

```text
des étudiants partageant
le même encadrant
```

ou

```text
des étudiants partageant
un enseignant commun
```

car ils sont les plus susceptibles de provoquer le conflit.

---

# Reproductibilité

Tous les choix aléatoires utilisent :

```python
random_seed
```

Ainsi :

```text
même instance

même configuration

même graine
```

↓

```text
même résultat
```

---

# Configuration

La configuration est centralisée dans :

```python
GreedyConfig
```

---

# Paramètres Principaux

```text
random_seed

use_candidate_ordering

use_repair

max_repair_iterations

use_mrv_ordering
```

---

# Paramètres Avancés

Poids heuristiques :

```text
weight_new_jury_pair

weight_teacher_load

weight_presence_days

weight_idle_slots

weight_group_breaks
```

Ces poids influencent le comportement du classement glouton.

---

# Évaluation

Une fois validée :

```python
SolutionEvaluator
```

calcule :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

---

# Avantages

Le Greedy Solver présente plusieurs avantages.

### Rapidité

Construction très rapide d'une solution.

---

### Simplicité

Architecture claire et maintenable.

---

### Robustesse

Respect systématique des contraintes.

---

### Point de Départ

Fournit une excellente solution initiale pour :

```text
Local Search

CP-SAT

Hybrid Solver
```

---

# Limites

Le solveur reste une heuristique.

Il ne garantit pas :

```text
l'optimalité
```

ni même :

```text
une planification complète
```

sur certaines instances très contraintes.

---

# Statuts Possibles

Le solveur peut retourner les statuts :

---

## VALID

```text
Planning complet et valide
```

---

## INCOMPLETE

```text
Certains étudiants
n'ont pas pu être placés
```

---

## INVALID

```text
Planning rejeté
par la validation
```

---

## INVALID_INSTANCE

```text
Instance incohérente
avant même la résolution
```

---

# Intégration avec le Pipeline Global

Le Greedy Solver constitue la première étape de résolution complète.

Architecture cible :

```text
Greedy Solver
        ↓
Local Search Solver
        ↓
CP-SAT Solver
        ↓
Solution Finale
```

Cette approche permet de combiner :

- rapidité de construction ;
- amélioration progressive ;
- optimisation avancée.

---

# Conclusion

Le Greedy Solver constitue la pierre angulaire du système de résolution.

Son rôle est de produire rapidement une solution valide en exploitant plusieurs heuristiques de construction :

- MRV ;
- classement des jurys ;
- classement des créneaux ;
- classement des salles ;
- réparation locale.

Même s'il ne garantit pas l'optimalité, il fournit une base solide pour toutes les étapes d'optimisation ultérieures du projet.