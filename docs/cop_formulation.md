# Formulation du Problème de Satisfaction de Contraintes (COP)

## Objectif

Ce document présente la formulation mathématique du problème sous forme d'un :

```text
Constraint Optimization Problem (COP)
```

Cette formulation servira de base au futur :

```text
CP-SAT Solver
```

et à la rédaction du rapport final.

---

# Nature du Problème

Le problème consiste à planifier un ensemble de soutenances académiques sous contraintes.

Chaque soutenance doit être affectée :

- à un jour ;
- à un créneau ;
- à un jury ;
- à une salle (pour les finales).

Tout en respectant :

- les contraintes métier ;
- les disponibilités ;
- les capacités ;
- les règles institutionnelles.

Le problème est donc un :

```text
Constraint Optimization Problem (COP)
```

car :

- des contraintes dures doivent être satisfaites ;
- plusieurs objectifs doivent être optimisés simultanément.

---

# Ensembles

## Étudiants

```text
S
```

Ensemble des étudiants.

---

## Enseignants

```text
T
```

Ensemble des enseignants.

---

## Présidents

```text
P ⊆ T
```

Enseignants pouvant présider une soutenance.

---

## Examinateurs

```text
E ⊆ T
```

Enseignants pouvant examiner une soutenance.

---

## Encadrants

```text
U ⊆ T
```

Ensemble des encadrants.

---

## Salles

```text
R
```

Ensemble des salles.

---

## Jours

```text
D
```

Ensemble des jours du calendrier.

---

## Créneaux

```text
K
```

Ensemble des créneaux quotidiens.

---

## Phases

```text
F = {PREDEFENCE, FINAL}
```

---

# Paramètres

## Disponibilité d'un enseignant

```text
A_teacher(t,d,k)
```

Vaut :

```text
1 si disponible
0 sinon
```

---

## Disponibilité d'un étudiant

```text
A_student(s,d,k)
```

Vaut :

```text
1 si disponible
0 sinon
```

---

## Disponibilité d'une salle

```text
A_room(r,d,k)
```

Vaut :

```text
1 si disponible
0 sinon
```

---

## Encadrant d'un étudiant

```text
supervisor(s)
```

---

## Domaine de l'étudiant

```text
domain(s)
```

---

## Compatibilité domaine

```text
covers(e,s)
```

Vaut :

```text
1 si e couvre le domaine de s
0 sinon
```

---

## Admissibilité en finale

```text
eligible_final(s)
```

Vaut :

```text
1 si l'étudiant passe la finale
0 sinon
```

---

# Variables de Décision

## Affectation Pré-soutenance

```text
x[s,p,e,d,k]
```

Variable binaire.

Vaut :

```text
1
```

si :

```text
l'étudiant s

effectue sa pré-soutenance

avec le jury (p,e)

au jour d
au créneau k
```

---

## Affectation Finale

```text
y[s,p,e,r,d,k]
```

Variable binaire.

Vaut :

```text
1
```

si :

```text
l'étudiant s

effectue sa finale

avec le jury (p,e)

dans la salle r

au jour d
au créneau k
```

---

# Contraintes

---

# C1

Pré-soutenance unique

```text
∀ s

Σ x[s,p,e,d,k] = 1
```

---

# C2

Finale unique pour les admissibles

```text
∀ s admissible

Σ y[s,p,e,r,d,k] = 1
```

---

# C3

Aucune finale pour les non admissibles

```text
∀ s non admissible

Σ y[s,p,e,r,d,k] = 0
```

---

# C4

Disponibilité étudiant

```text
x[s,p,e,d,k]
≤
A_student(s,d,k)
```

```text
y[s,p,e,r,d,k]
≤
A_student(s,d,k)
```

---

# C5

Disponibilité président

```text
x[s,p,e,d,k]
≤
A_teacher(p,d,k)
```

```text
y[s,p,e,r,d,k]
≤
A_teacher(p,d,k)
```

---

# C6

Disponibilité examinateur

```text
x[s,p,e,d,k]
≤
A_teacher(e,d,k)
```

```text
y[s,p,e,r,d,k]
≤
A_teacher(e,d,k)
```

---

# C7

Disponibilité encadrant

Pour les finales :

```text
y[s,p,e,r,d,k]
≤
A_teacher(supervisor(s),d,k)
```

---

# C8

Couverture domaine

```text
x[s,p,e,d,k]
≤
covers(e,s)
```

```text
y[s,p,e,r,d,k]
≤
covers(e,s)
```

---

# C9

Conflit Enseignant

Un enseignant ne peut participer à deux soutenances simultanément.

```text
∀ t,d,k

nombre_de_participations(t,d,k)
≤ 1
```

---

# C10

Conflit Étudiant

```text
∀ s,d,k

nombre_de_soutenances(s,d,k)
≤ 1
```

---

# C11

Conflit Salle

```text
∀ r,d,k

nombre_de_finales(r,d,k)
≤ 1
```

---

# C12

Capacité Enseignant

```text
sessions_teacher(t,d)

≤

max_sessions_per_day(t)
```

---

# C13

Capacité Salle

```text
sessions_room(r,d)

≤

max_sessions_per_day(r)
```

---

# C14

Continuité du Jury

Le binôme utilisé en pré-soutenance doit être identique à celui utilisé en finale.

Pour tout étudiant admissible :

```text
jury_predefence(s)

=

jury_final(s)
```

---

# Fonction Objectif

Le problème est multi-objectifs.

---

## Objectif 1

Minimiser :

```text
teacher_presence_days
```

---

## Objectif 2

Minimiser :

```text
teacher_idle_slots
```

---

## Objectif 3

Minimiser :

```text
teacher_load_range
```

---

## Objectif 4

Minimiser :

```text
supervisor_group_breaks
```

---

## Objectif 5

Minimiser :

```text
distinct_jury_pairs
```

---

# Scalarisation

Pour CP-SAT, les objectifs doivent être combinés.

Une fonction pondérée peut être utilisée :

```text
Minimize

w1 × teacher_presence_days
+
w2 × teacher_idle_slots
+
w3 × teacher_load_range
+
w4 × supervisor_group_breaks
+
w5 × distinct_jury_pairs
```

Les poids seront définis expérimentalement.

---

# Warm Start

Le modèle CP-SAT utilisera une solution initiale issue de :

```text
Greedy Solver
        ↓
Local Search
```

Cette solution permettra :

- une convergence plus rapide ;
- une amélioration plus importante ;
- une meilleure qualité finale.

---

# Résultat Attendu

Le solveur CP-SAT devra produire :

```text
Solution valide
```

respectant toutes les contraintes dures et minimisant simultanément les cinq critères d'évaluation du projet.