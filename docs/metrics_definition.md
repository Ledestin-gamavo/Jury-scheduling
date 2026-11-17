# Définition des Métriques

## Objectif

Ce document décrit les cinq métriques utilisées pour évaluer la qualité d'une solution.

Contrairement aux contraintes dures, les métriques ne déterminent pas si une solution est valide ou invalide.

Elles permettent de mesurer la qualité d'une solution valide et servent d'objectifs d'optimisation pour :

- Greedy Solver ;
- Local Search Solver ;
- CP-SAT Solver ;
- Hybrid Solver.

Toutes les métriques sont à minimiser.

---

# Vue d'Ensemble

Le vecteur de performance d'une solution est défini par :

```text
(
teacher_presence_days,
teacher_idle_slots,
teacher_load_range,
supervisor_group_breaks,
distinct_jury_pairs
)
```

Une solution est considérée meilleure lorsqu'elle réduit une ou plusieurs composantes de ce vecteur.

---

# Métrique 1 : Teacher Presence Days

## Nom

```text
teacher_presence_days
```

---

## Objectif

Réduire le nombre de jours durant lesquels les enseignants doivent se déplacer ou être mobilisés.

---

## Motivation

Un enseignant convoqué sur plusieurs jours consécutifs mobilise davantage de temps et de ressources.

Il est donc préférable de regrouper les soutenances sur un nombre réduit de jours.

---

## Définition

Pour chaque enseignant :

```text
Nombre de jours distincts
où l'enseignant participe
à au moins une soutenance
```

La métrique correspond à la somme sur tous les enseignants.

---

## Participants Pris en Compte

Pré-soutenances :

- président ;
- examinateur.

Finales :

- président ;
- examinateur ;
- encadrant.

---

## Formulation

Soit :

```math
days(t)
```

l'ensemble des jours où l'enseignant \(t\) participe à au moins une séance.

La métrique vaut :

```math
f_1
=
\sum_{t \in T}
|days(t)|
```

---

## Exemple

```text
Enseignant A :

Jour 1
Jour 1
Jour 3

=> 2 jours

Enseignant B :

Jour 3

=> 1 jour
```

Résultat :

```text
2 + 1 = 3
```

---

## Interprétation

Valeur faible :

✅ enseignants regroupés

Valeur élevée :

❌ enseignants dispersés

---

# Métrique 2 : Teacher Idle Slots

## Nom

```text
teacher_idle_slots
```

---

## Objectif

Réduire les temps morts entre deux soutenances d'un même enseignant.

---

## Motivation

Les enseignants préfèrent généralement enchaîner leurs soutenances plutôt que d'attendre entre deux passages.

---

## Définition

Pour chaque enseignant et pour chaque jour :

```text
trous
=
dernier_creneau
-
premier_creneau
+
1
-
nombre_de_soutenances
```

La métrique correspond à la somme de tous les trous observés.

---

## Formulation

Pour un enseignant \(t\) et un jour \(d\) :

```math
idle(t,d)
=
last(t,d)
-
first(t,d)
+
1
-
sessions(t,d)
```

Puis :

```math
f_2
=
\sum idle(t,d)
```

---

## Exemple

Créneaux :

```text
1
3
4
```

Premier :

```text
1
```

Dernier :

```text
4
```

Nombre de soutenances :

```text
3
```

Score :

```text
4 - 1 + 1 - 3 = 1
```

---

## Interprétation

Valeur faible :

✅ emplois du temps compacts

Valeur élevée :

❌ nombreux temps d'attente

---

# Métrique 3 : Teacher Load Range

## Nom

```text
teacher_load_range
```

---

## Objectif

Équilibrer la charge entre enseignants.

---

## Motivation

Il est préférable que les soutenances soient réparties équitablement plutôt que concentrées sur quelques personnes.

---

## Définition

La charge d'un enseignant correspond à son nombre total de participations à des soutenances.

La métrique mesure :

```text
charge_max
-
charge_min
```

---

## Formulation

Soit :

```math
load(t)
```

le nombre de soutenances de l'enseignant \(t\).

Alors :

```math
f_3
=
\max(load(t))
-
\min(load(t))
```

---

## Exemple

```text
A = 12 soutenances

B = 10 soutenances

C = 4 soutenances
```

Résultat :

```text
12 - 4 = 8
```

---

## Interprétation

Valeur faible :

✅ répartition équilibrée

Valeur élevée :

❌ surcharge de certains enseignants

---

# Métrique 4 : Supervisor Group Breaks

## Nom

```text
supervisor_group_breaks
```

---

## Objectif

Regrouper les étudiants d'un même encadrant.

---

## Motivation

Lorsqu'un encadrant suit plusieurs étudiants, il est plus confortable pour lui que leurs soutenances soient regroupées.

---

## Définition

Les soutenances d'étudiants d'un même encadrant sont organisées en groupes.

Un groupe est :

```text
une suite maximale
de soutenances consécutives
du même encadrant
```

Chaque groupe supplémentaire ajoute une pénalité.

---

## Formulation Simplifiée

Pour un encadrant :

```math
breaks
=
max(0, groupes - 1)
```

Puis :

```math
f_4
=
\sum breaks
```

---

## Exemple

```text
Créneaux :

1
2
3
```

Un seul groupe :

```text
score = 0
```

---

```text
Créneaux :

1
2

5
6
```

Deux groupes :

```text
score = 1
```

---

## Interprétation

Valeur faible :

✅ étudiants regroupés

Valeur élevée :

❌ étudiants dispersés

---

# Métrique 5 : Distinct Jury Pairs

## Nom

```text
distinct_jury_pairs
```

---

## Objectif

Réutiliser les mêmes binômes jury sur plusieurs étudiants.

---

## Motivation

La réutilisation des jurys favorise :

- la cohérence académique ;
- la stabilité organisationnelle ;
- la simplification logistique.

---

## Définition

On compte le nombre de couples distincts :

```text
(président, examinateur)
```

utilisés dans les pré-soutenances.

---

## Formulation

Soit :

```math
Pairs
=
\{
(p,e)
\}
```

ensemble des binômes utilisés.

Alors :

```math
f_5
=
|Pairs|
```

---

## Exemple

```text
Étudiant 1

(T1,T2)

Étudiant 2

(T1,T2)

Étudiant 3

(T3,T2)
```

Résultat :

```text
2
```

---

## Interprétation

Valeur faible :

✅ forte réutilisation

Valeur élevée :

❌ beaucoup de jurys différents

---

# Évaluation Globale

Le résultat d'une évaluation est représenté par :

```python
EvaluationResult
```

contenant :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

---

# Vecteur d'Évaluation

La représentation de référence est :

```text
(
f1,
f2,
f3,
f4,
f5
)
```

où :

```text
f1 = teacher_presence_days

f2 = teacher_idle_slots

f3 = teacher_load_range

f4 = supervisor_group_breaks

f5 = distinct_jury_pairs
```

---

# Dominance de Pareto

Une solution A domine une solution B si :

```text
A est au moins aussi bonne
sur toutes les métriques

et

strictement meilleure
sur au moins une métrique
```

Cette comparaison est utilisée par :

```python
EvaluationResult.dominates()
```

---

# Score Agrégé

Pour certains solveurs, un score unique peut être utilisé.

Forme générale :

```math
Score
=
w_1f_1
+
w_2f_2
+
w_3f_3
+
w_4f_4
+
w_5f_5
```

où :

```text
w_i ≥ 0
```

sont des poids.

---

# Remarque Importante

Le projet considère le vecteur de métriques comme la référence officielle.

Le score agrégé n'est qu'une simplification destinée :

- aux heuristiques ;
- à la recherche locale ;
- au CP-SAT 