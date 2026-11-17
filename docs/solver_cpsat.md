# Solveur CP-SAT

## Objectif

Le solveur CP-SAT constitue la composante d'optimisation exacte du projet.

Son rôle est de rechercher une solution de meilleure qualité que celle produite par les heuristiques tout en garantissant le respect de l'ensemble des contraintes du problème.

Il repose sur :

```text
Google OR-Tools
CP-SAT Solver
```

---

# Position dans l'Architecture

Le solveur CP-SAT intervient après :

```text
Core
Preprocessing
Validation
Metrics
Greedy
Local Search
```

Pipeline prévu :

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

---

# Pourquoi CP-SAT ?

Les approches gloutonnes et la recherche locale sont rapides mais ne garantissent pas de solution optimale.

CP-SAT permet :

- une exploration systématique de l'espace de recherche ;
- une meilleure qualité de solution ;
- une gestion efficace des contraintes combinatoires ;
- l'utilisation d'un point de départ (warm start).

---

# Fondements Mathématiques

La formulation du modèle est décrite dans :

```text
constraints_catalog.md

cop_formulation.md

mathematical_model.md
```

Le solveur implémentera directement cette formulation.

---

# Architecture du Module

Répertoire :

```text
src/solvers/cpsat/
```

Contenu prévu :

```text
__init__.py

variables.py

constraints.py

objectives.py

model.py

cpsat_solver.py
```

---

# Responsabilités des Fichiers

## variables.py

Responsable de :

- la création des variables CP-SAT ;
- leur indexation ;
- leur organisation.

Aucune contrainte ne doit être créée ici.

---

## constraints.py

Responsable de :

- l'ajout des contraintes dures ;
- la traduction des règles métier.

Exemples :

```text
Disponibilités

Conflits horaires

Capacités

Continuité du jury
```

---

## objectives.py

Responsable de :

- la création de la fonction objectif ;
- la définition des poids ;
- la scalarisation éventuelle.

---

## model.py

Responsable de :

- l'assemblage du modèle complet ;
- la coordination entre variables, contraintes et objectifs.

---

## cpsat_solver.py

Point d'entrée du solveur.

Responsabilités :

- construire le modèle ;
- lancer OR-Tools ;
- extraire la solution ;
- construire les rapports.

---

# Variables de Décision

Le modèle reposera sur des variables booléennes.

---

## Pré-soutenance

```text
x[s,p,e,d,k]
```

vaut :

```text
1
```

si l'étudiant :

```text
s
```

effectue sa pré-soutenance :

```text
jour d
créneau k
jury (p,e)
```

---

## Finale

```text
y[s,p,e,r,d,k]
```

vaut :

```text
1
```

si l'étudiant :

```text
s
```

effectue sa finale :

```text
jury (p,e)

salle r

jour d

créneau k
```

---

# Contraintes à Implémenter

---

## Disponibilités

Respect :

```text
Étudiant

Président

Examinateur

Encadrant

Salle
```

---

## Conflits Enseignant

Un enseignant ne peut participer à deux soutenances simultanément.

---

## Conflits Étudiant

Un étudiant ne peut être planifié deux fois au même instant.

---

## Conflits Salle

Une salle ne peut accueillir qu'une seule finale à la fois.

---

## Capacités Journalières

Respect :

```text
max_sessions_per_day
```

enseignant et salle.

---

## Compatibilité Domaine

L'examinateur doit couvrir le domaine de l'étudiant.

---

## Rôles

Respect :

```text
Président

Examinateur
```

---

## Continuité du Jury

Le binôme :

```text
(président, examinateur)
```

doit rester identique entre :

```text
pré-soutenance

finale
```

---

# Fonction Objectif

Le problème est multi-objectif.

Les cinq critères du projet doivent être optimisés :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

---

# Représentation Interne

Le solveur CP-SAT utilisera une fonction scalaire :

```text
score_total
```

de la forme :

```text
w1*f1
+
w2*f2
+
w3*f3
+
w4*f4
+
w5*f5
```

où*:

```text
w_i ≥ 0
*``

sont définis par*configuration.

---

# Warm Start
*Le*modèle doit*être compatible avec un*démarrage à*chaud.

Source*du warm start :

```text*Greedy Solver
       *↓
Local Search Solver
        ↓
CP*SAT
```

---

##*Objectif

*ournir au solveur*:

```text
une solution initiale v*lide*```

afin de :

- réduire le temps*de recherche ;
- accélérer la conv*rgence ;
- améliorer la qualité fi*ale.

---

# Configuration*
Configuration prévue :

```python*CPSATConfig
```

---

##*Paramètres Principaux

```text
*andom_seed

time_limit_seconds

nu**search_workers

relative*gap_limit*
use_warm_start
``*

---

## Paramètres d*Optimisation

```text
objective_we*ghts

*og_search*progress

max*memory_mb*```

---

# Rapport*de Résolution

Le solve*r produira :

```python
*PSATReport
```

con*enant :

```text
solution

status
*statistics*
validation

evaluation

objective*value

gap*
elapsed_time
```

---

#*Statuts Possibles

## OPTIMAL

```*ext
Solution*optimale prouvée.
*``

---

## FEASIBLE

```text*Solution valide trouvée.

*ptimalité non prouvée*
```

---

## IN*EASIBLE

```text
Aucune*solution réalisable.
```

---

*# MODEL_INVALID*
```text
Erreur de mod*lisation.
```

---

## UNKNOWN*
```text
Recherche interrompue.
``*

---

# Validation

Toute solutio* extraite doit être vérifiée via :*
```python
SolutionValidator
```

*vant d'être retournée.

Pipeline :*
```text
CP-SAT
    ↓
Solution
   *↓
Validation
    ↓
Evaluation
```
*---

# Reproductibilité

Le solveu* doit être reproductible.

Tous le* appels à OR-Tools doivent utilise* :

```text
random_seed
```

défin* dans la configuration.

---

# Intégration avec Hybrid Solver

Le so*veur Hybrid utilisera :

```text
G*eedy
    ↓
Local Search
    ↓
CP-S*T
```

Le CP-SAT doit donc accepte* :

```python
initial_solution
```*
comme point de départ.

---

# Avantages

Le solveur CP-SAT apporte *

✅ optimisation exacte

✅ gestion*robuste des contraintes

✅ preuve *'optimalité lorsque possible

✅ ex*loitation du warm start

✅ qualité*supérieure aux heuristiques

---

* Limites

Le coût de calcul augmen*e fortement avec :

- le nombre d'*tudiants ;
- le nombre d'enseignan*s ;
- le nombre de salles ;
- le n*mbre de créneaux.

Le solveur peut*nécessiter :

```text
*imite de temps

*ap acceptable

warm*start
```

sur les grandes*instances.

---

# Conclusion

Le *olveur CP*SAT représente le niveau*d'optimisation le plus avancé du p*ojet.

Son objectif est d'ex*loiter la modélisation mathématiqu* définie dans la documentation afi* de produire des*solutions de très haute qualité,*tout en restant compatible avec le* composants*déjà développés :

- Pre*rocessing ;
- Validation ;
- Metri*s ;
- Greedy Solver ;
- Local Sear*h Solver.

Il constitue également *a b*ique centrale du futur Hybrid Solv*r.