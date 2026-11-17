# Modèle Mathématique

## Introduction

Le problème de planification des soutenances peut être formulé comme un problème d'optimisation combinatoire sous contraintes.

L'objectif consiste à construire un calendrier de soutenances respectant l'ensemble des contraintes académiques tout en optimisant plusieurs critères de qualité.

Cette formulation constitue la base théorique du projet et servira de référence pour :

- l'analyse du problème ;
- le développement du solveur CP-SAT ;
- la rédaction du rapport final ;
- la justification scientifique des choix d'implémentation.

---

# Nature du Problème

Le problème appartient à la famille des :

```text
Constraint Optimization Problems (COP)
```

et peut également être vu comme un problème :

```text
NP-difficile
```

en raison de la combinaison simultanée :

- d'affectation de ressources ;
- d'ordonnancement ;
- de satisfaction de contraintes ;
- d'optimisation multi-objectif.

---

# Ensembles

## Étudiants

```math
S = \{s_1,s_2,...,s_n\}
```

Ensemble des étudiants.

---

## Enseignants

```math
T = \{t_1,t_2,...,t_m\}
```

Ensemble des enseignants.

---

## Présidents

```math
P \subseteq T
```

Enseignants habilités à présider.

---

## Examinateurs

```math
E \subseteq T
```

Enseignants habilités à examiner.

---

## Encadrants

```math
U \subseteq T
```

Ensemble des encadrants.

---

## Salles

```math
R = \{r_1,r_2,...,r_q\}
```

Ensemble des salles disponibles.

---

## Jours

```math
D = \{1,2,\ldots,d_{max}\}
```

Ensemble des jours de planification.

---

## Créneaux

```math
K = \{1,2,\ldots,k_{max}\}
```

Ensemble des créneaux quotidiens.

---

## Phases

```math
F = \{PREDEFENCE, FINAL\}
```

---

# Paramètres

## Encadrant d'un étudiant

```math
sup(s)
```

Encadrant associé à l'étudiant \(s\).

---

## Domaine d'un étudiant

```math
dom(s)
```

Domaine académique de l'étudiant.

---

## Admissibilité

```math
eligible(s)
```

avec :

```math
eligible(s)=
\begin{cases}
1 & \text{si l'étudiant passe la finale} \\
0 & \text{sinon}
\end{cases}
```

---

# Disponibilités

## Enseignant

```math
A_T(t,d,k)
```

avec :

```math
A_T(t,d,k)=1
```

si l'enseignant est disponible.

---

## Étudiant

```math
A_S(s,d,k)
```

avec :

```math
A_S(s,d,k)=1
```

si l'étudiant est disponible.

---

## Salle

```math
A_R(r,d,k)
```

avec :

```math
A_R(r,d,k)=1
```

si la salle est disponible.

---

# Compatibilité Académique

## Domaine

```math
covers(e,s)
```

vaut :

```math
1
```

si l'examinateur \(e\) couvre le domaine de l'étudiant \(s\).

---

## Capacité Enseignant

```math
cap_T(t)
```

Nombre maximal de soutenances par jour.

---

## Capacité Salle

```math
cap_R(r)
```

Nombre maximal de soutenances par jour.

---

# Variables de Décision

## Pré-soutenance

Variable binaire :

```math
x_{s,p,e,d,k}
```

avec :

```math
x_{s,p,e,d,k}=1
```

si :

- l'étudiant \(s\)
- est affecté au jury \((p,e)\)
- au jour \(d\)
- au créneau \(k\)

pour sa pré-soutenance.

---

## Finale

Variable binaire :

```math
y_{s,p,e,r,d,k}
```

avec :

```math
y_{s,p,e,r,d,k}=1
```

si :

- l'étudiant \(s\)
- est affecté au jury \((p,e)\)
- dans la salle \(r\)
- au jour \(d\)
- au créneau \(k\)

pour sa finale.

---

# Contraintes

## Unicité de la Pré-soutenance

Chaque étudiant doit posséder exactement une pré-soutenance.

```math
\forall s \in S
```

```math
\sum x_{s,p,e,d,k}=1
```

---

## Unicité de la Finale

Pour chaque étudiant admissible :

```math
\forall s \in S
```

```math
eligible(s)=1
```

```math
\sum y_{s,p,e,r,d,k}=1
```

---

## Absence de Finale

Pour chaque étudiant non admissible :

```math
eligible(s)=0
```

```math
\sum y_{s,p,e,r,d,k}=0
```

---

## Disponibilité des Étudiants

```math
x_{s,p,e,d,k}
\leq
A_S(s,d,k)
```

```math
y_{s,p,e,r,d,k}
\leq
A_S(s,d,k)
```

---

## Disponibilité des Enseignants

Pour chaque participant :

```math
x_{s,p,e,d,k}
\leq
A_T(p,d,k)
```

```math
x_{s,p,e,d,k}
\leq
A_T(e,d,k)
```

---

Pour les finales :

```math
y_{s,p,e,r,d,k}
\leq
A_T(sup(s),d,k)
```

---

## Compatibilité Domaine

```math
x_{s,p,e,d,k}
\leq
covers(e,s)
```

```math
y_{s,p,e,r,d,k}
\leq
covers(e,s)
```

---

## Absence de Chevauchement Enseignant

Un enseignant ne peut participer à deux soutenances simultanément.

```math
\forall t,d,k
```

```math
participations(t,d,k)
\leq 1
```

---

## Absence de Chevauchement Étudiant

```math
\forall s,d,k
```

```math
sessions(s,d,k)
\leq 1
```

---

## Conflit de Salle

```math
\forall r,d,k
```

```math
occupations(r,d,k)
\leq 1
```

---

## Plafond Journalier Enseignant

```math
\forall t,d
```

```math
sessions(t,d)
\leq
cap_T(t)
```

---

## Plafond Journalier Salle

```math
\forall r,d
```

```math
sessions(r,d)
\leq
cap_R(r)
```

---

## Continuité du Jury

Pour chaque étudiant admissible :

```math
jury_{pre}(s)
=
jury_{final}(s)
```

---

## Distinction des Membres du Jury

Pour une finale :

```math
président
\neq
examinateur
```

```math
président
\neq
encadrant
```

```math
examinateur
\neq
encadrant
```

---

# Fonctions Objectifs

Le problème est multi-objectif.

Les cinq objectifs sont directement dérivés du cahier des charges.

---

# Objectif 1

Minimiser :

```math
f_1 =
teacher\_presence\_days
```

Réduire le nombre total de jours de présence des enseignants.

---

# Objectif 2

Minimiser :

```math
f_2 =
teacher\_idle\_slots
```

Réduire les temps morts.

---

# Objectif 3

Minimiser :

```math
f_3 =
teacher\_load\_range
```

Équilibrer la charge entre enseignants.

---

# Objectif 4

Minimiser :

```math
f_4 =
supervisor\_group\_breaks
```

Regrouper les étudiants d'un même encadrant.

---

# Objectif 5

Minimiser :

```math
f_5 =
distinct\_jury\_pairs
```

Favoriser la réutilisation des jurys.

---

# Formulation Multi-Objectif

Le vecteur objectif du problème est :

```math
F =
(f_1,f_2,f_3,f_4,f_5)
```

avec :

```math
\min F
```

---

# Scalarisation pour les Solveurs

Pour les solveurs utilisant une fonction objectif unique :

```math
\min Z
```

avec :

```math
Z =
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

```math
w_i \ge 0
```

sont des poids définis expérimentalement.

---

# Approche d'Optimisation du Projet

Le système complet repose sur une optimisation en plusieurs étapes.

```text
Instance
    ↓
Preprocessing
    ↓
Greedy Solver
    ↓
Local Search
    ↓
CP-SAT Solver
    ↓
Solution Finale
```

Le solveur glouton fournit une solution initiale.

La recherche locale améliore cette solution.

Le solveur CP-SAT exploite ensuite cette solution comme point de départ afin d'atteindre une qualité supérieure.

---

# Conclusion

Le problème étudié est un problème d'optimisation combinatoire multi-objectif sous contraintes.

La formulation proposée :

- respecte le cahier des charges ;
- est compatible avec OR-Tools CP-SAT ;
- couvre l'ensemble des contraintes métier ;
- intègre les cinq critères d'évaluation définis dans le projet.

Elle constitue la référence théorique utilisée par les solveurs d'optimisation du dépôt.