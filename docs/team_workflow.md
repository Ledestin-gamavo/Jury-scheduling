# Workflow d'Équipe

## Objectif

Ce document définit l'organisation du travail collaboratif au sein de l'équipe.

Son objectif est de :

- éviter les conflits de développement ;
- éviter les doublons ;
- faciliter l'intégration des contributions ;
- maintenir la qualité globale du projet.

---

# Répartition des Responsabilités

Le projet est organisé en modules clairement séparés.

Chaque contributeur est responsable d'un périmètre précis.

Exemples :

```text
Core

Preprocessing

Validation

Metrics

Greedy Solver

Local Search

CP-SAT Solver

Hybrid Solver

Benchmarking

Visualisation
```

---

# Principe Fondamental

Un développeur ne doit jamais modifier directement un module dont il n'est pas responsable sans concertation préalable.

Objectif :

```text
limiter les régressions
et les conflits Git.
```

---

# Workflow de Développement

Chaque fonctionnalité suit le cycle suivant :

```text
Analyse
    ↓
Implémentation
    ↓
Compilation
    ↓
Tests
    ↓
Validation
    ↓
Commit
    ↓
Intégration
```

---

# Avant de Commencer un Travail

Toujours :

1. récupérer la dernière version du dépôt ;
2. lire `current_progress.md` ;
3. vérifier l'état de la branche ;
4. identifier précisément les fichiers à modifier.

---

# Règles de Modification

Avant de modifier un fichier :

```text
Lire entièrement son contenu.
```

Avant de créer un fichier :

```text
Vérifier qu'il n'existe pas déjà.
```

Avant de réécrire une logique :

```text
Vérifier si elle existe déjà ailleurs.
```

---

# Communication

Toute évolution de l'architecture doit être signalée au reste de l'équipe.

Exemples :

```text
nouveau module

nouvelle dépendance

nouvelle métrique

nouvelle contrainte
```

---

# Gestion Git

## Fréquence des Commits

Privilégier :

```text
petits commits fréquents
```

Éviter :

```text
gros commits de plusieurs milliers de lignes
```

---

## Convention de Nommage

Utiliser :

```text
feat:
fix:
refactor:
docs:
test:
```

Exemples :

```text
feat(local-search): add swap neighborhood

fix(validation): correct room conflict detection

docs(metrics): complete metric definitions

test(greedy): add repair tests
```

---

# Branches

Organisation recommandée :

```text
main

develop

feature/*
```

---

## Main

Contient uniquement :

```text
versions stables
```

---

## Develop

Contient :

```text
travail validé
```

avant intégration finale.

---

## Feature

Une branche par tâche.

Exemples :

```text
feature/cpsat

feature/local-search-tests

feature/dashboard
```

---

# Intégration de Nouveau Code

Avant un merge :

```text
Compilation
```

obligatoire :

```bash
python -m compileall src
```

---

Puis :

```text
Tests
```

---

Puis :

```text
Validation métier
```

---

# Documentation

Toute fonctionnalité importante doit mettre à jour :

```text
current_progress.md
```

et si nécessaire :

```text
architecture.md

metrics_definition.md

constraints_catalog.md
```

---

# Gestion des Conflits

Si deux développeurs modifient :

```text
le même module
```

la priorité est donnée à :

```text
la cohérence de l'architecture
```

plutôt qu'à la rapidité.

---

# Développement des Solveurs

Les solveurs doivent respecter les dépendances autorisées.

Ils peuvent utiliser :

```text
Core

Preprocessing

Validation

Metrics
```

---

Ils ne doivent jamais :

```text
modifier Core

réimplémenter Validation

réimplémenter Metrics
```

---

# Workflow de Validation

Avant toute expérimentation :

```text
Instance
    ↓
Validation
    ↓
Solveur
    ↓
Validation
    ↓
Évaluation
```

---

# Gestion des Expériences

Toute expérimentation doit documenter :

```text
instance utilisée

configuration

graine aléatoire

résultats
```

afin de garantir la reproductibilité.

---

# Règles de Reproductibilité

Tous les solveurs doivent utiliser :

```python
random_seed
```

Les expériences doivent pouvoir être reproduites à l'identique.

---

# Mise à Jour du Suivi du Projet

À la fin d'une tâche :

1. mettre à jour `current_progress.md` ;
2. documenter les changements importants ;
3. signaler les nouveaux fichiers créés.

---

# Critères de Qualité

Toute contribution doit respecter :

- les standards de codage ;
- le typage ;
- l'architecture ;
- la documentation ;
- la validation métier.

---

# Checklist Avant Push

Vérifier :

```text
✅ compilation

✅ imports

✅ tests

✅ validation

✅ documentation

✅ current_progress mis à jour
```

---

# Principe Final

La priorité du projet est :

```text
Cohérence
    >
Rapidité
```

Un développement plus lent mais maintenable est toujours préférable à une implémentation rapide mais difficile à intégrer.