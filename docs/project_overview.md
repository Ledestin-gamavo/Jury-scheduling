# Présentation Générale du Projet

## Contexte

L'organisation des soutenances académiques constitue un problème complexe de planification et d'affectation de ressources.

Chaque soutenance implique simultanément :

- un étudiant ;
- plusieurs enseignants ;
- éventuellement une salle ;
- une phase académique spécifique ;
- un ensemble de contraintes institutionnelles.

Lorsque le nombre d'étudiants et d'enseignants augmente, construire un planning manuellement devient difficile, chronophage et source d'erreurs.

Ce projet vise à automatiser ce processus.

---

# Problématique

Comment construire automatiquement un planning de soutenances :

- valide ;
- cohérent ;
- équitable ;
- optimisé ;

tout en respectant l'ensemble des contraintes académiques ?

Le problème étudié combine plusieurs sous-problèmes :

- affectation de ressources ;
- ordonnancement ;
- satisfaction de contraintes ;
- optimisation multi-objectif.

Il appartient à la catégorie des problèmes d'optimisation combinatoire.

---

# Objectifs du Projet

Le système doit être capable de :

### 1. Produire un planning valide

Toutes les contraintes institutionnelles doivent être respectées.

Par exemple :

- disponibilités ;
- rôles ;
- domaines ;
- conflits horaires ;
- capacités journalières ;
- continuité du jury.

---

### 2. Optimiser la qualité du planning

Une fois les contraintes satisfaites, le système cherche à améliorer la qualité du calendrier.

Cette amélioration repose sur cinq critères :

- réduction des jours de présence ;
- réduction des temps morts ;
- équilibrage de charge ;
- regroupement des étudiants d'un même encadrant ;
- réutilisation des mêmes jurys.

---

### 3. Fournir plusieurs stratégies de résolution

Le projet ne repose pas sur une seule méthode de résolution.

Plusieurs approches sont étudiées :

- heuristiques constructives ;
- recherche locale ;
- programmation par contraintes ;
- hybridation des approches.

---

# Description du Problème

Pour chaque étudiant, le système doit déterminer :

### Pré-soutenance

- jour ;
- créneau ;
- président ;
- examinateur.

---

### Finale (si admissible)

- jour ;
- créneau ;
- salle ;
- président ;
- examinateur.

Le binôme :

```text
(président, examinateur)
```

doit rester identique entre les deux phases.

---

# Contraintes Principales

Le projet prend en compte plusieurs familles de contraintes.

---

## Disponibilités

Respect des disponibilités :

- des étudiants ;
- des enseignants ;
- des salles.

---

## Conflits

Absence de chevauchement :

- enseignant ;
- étudiant ;
- salle.

---

## Contraintes Académiques

Respect :

- des rôles ;
- des domaines ;
- des jurys ;
- des encadrants.

---

## Capacités

Respect :

- du nombre maximal de soutenances par enseignant et par jour ;
- du nombre maximal de soutenances par salle et par jour.

---

# Architecture Générale

Le projet suit une architecture modulaire.

```text
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
```

Chaque couche possède une responsabilité clairement identifiée.

---

# Modules Développés

## Core

Contient les objets métier :

- Teacher ;
- Student ;
- Room ;
- Session ;
- Solution ;
- Instance.

---

## Parsers

Chargement et transformation des données d'entrée.

---

## Preprocessing

Pré-calculs nécessaires à l'optimisation :

- disponibilités ;
- jurys candidats ;
- filtres de domaines.

---

## Validation

Contrôle des contraintes dures.

Ce module constitue la référence officielle de validation.

---

## Metrics

Évaluation de la qualité des solutions.

---

## Greedy Solver

Construction rapide d'une première solution valide.

---

## Local Search Solver

Amélioration progressive d'une solution existante.

---

## CP-SAT Solver

Optimisation exacte basée sur OR-Tools.

---

## Hybrid Solver

Combinaison de plusieurs stratégies de résolution.

---

# Méthodologie de Résolution

Le processus de résolution prévu est le suivant :

```text
1. Construire une solution valide
   (Greedy)

2. Améliorer cette solution
   (Local Search)

3. Utiliser la solution obtenue
   comme point de départ

4. Lancer CP-SAT

5. Produire la meilleure solution finale
```

Cette approche permet de combiner :

- rapidité ;
- robustesse ;
- qualité d'optimisation.

---

# Critères d'Évaluation

Une solution valide est évaluée selon cinq métriques :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

Toutes ces métriques sont à minimiser.

L'évaluation est réalisée par :

```python
SolutionEvaluator
```

---

# Technologies Utilisées

Le projet est développé en :

```text
Python 3.10+
```

Principales bibliothèques :

```text
dataclasses

typing

OR-Tools (CP-SAT)
```

Le projet suit :

- une architecture modulaire ;
- un typage strict ;
- une documentation systématique ;
- des règles strictes de dépendances.

---

# Résultats Attendus

À l'issue du projet, le système devra être capable de :

- générer automatiquement un planning complet ;
- respecter toutes les contraintes académiques ;
- optimiser les différents critères de qualité ;
- fournir des statistiques et indicateurs de performance ;
- comparer plusieurs approches de résolution.

---

# Perspectives

Les extensions futures envisagées incluent :

- optimisation multi-objectifs avancée ;
- visualisation graphique des plannings ;
- génération automatique de rapports ;
- benchmarking de solveurs ;
- expérimentation de nouvelles métaheuristiques ;
- intégration dans une plateforme web.

---

# Conclusion

Le projet Jury Scheduling constitue une application concrète de l'optimisation combinatoire et de la recherche opérationnelle.

En combinant modélisation mathématique, satisfaction de contraintes et optimisation multi-objectifs, il vise à produire automatiquement des plannings de soutenances valides et de haute qualité, tout en restant extensible et réutilisable dans différents contextes académiques.