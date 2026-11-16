# État d'Avancement du Projet

## Objectif du document

Ce document sert de point de synchronisation pour toute l'équipe.

Avant de commencer un développement, chaque membre doit consulter ce fichier afin de savoir :

- ce qui est déjà implémenté ;
- ce qui est en cours ;
- ce qui reste à développer ;
- les conventions techniques à respecter ;
- les dépendances entre modules.

---

# Architecture officielle du projet

Tous les développements doivent respecter STRICTEMENT l'arborescence officielle du dépôt.

Aucun nouveau dossier ne doit être créé sans validation collective.

Le code est organisé autour des modules suivants :

```text
core
parsers
preprocessing
validation
metrics
solvers
benchmarking
exporters
visualization
utils
```

---

# État actuel du développement

## ✅ Terminé

### Module : core

Les fichiers suivants sont implémentés :

```text
src/core/

✅ enums.py
✅ teacher.py
✅ student.py
✅ room.py
✅ session.py
✅ solution.py
✅ instance.py
```

---

## Fonctionnalités déjà disponibles

### enums.py

Contient :

- SCHEMA_VERSION
- Phase
- Role
- InstanceSize
- Availability
- check_identifier()

Rôle :

Fournir les types fondamentaux du domaine.

---

### teacher.py

Contient :

Classe :

```python
Teacher
```

Fonctionnalités :

- domaines de compétence
- rôles éligibles
- disponibilités
- plafond journalier
- vérifications d'éligibilité

---

### student.py

Contient :

Classe :

```python
Student
```

Fonctionnalités :

- domaine scientifique
- encadrant
- admissibilité finale
- disponibilités

---

### room.py

Contient :

Classe :

```python
Room
```

Fonctionnalités :

- disponibilités
- plafond journalier
- gestion des finales

---

### session.py

Contient :

Classe :

```python
Session
```

Fonctionnalités :

- représentation d'une séance
- gestion du jury
- gestion de la salle
- déplacement d'une séance

---

### solution.py

Contient :

Classe :

```python
Solution
```

Fonctionnalités :

- stockage des séances
- indexation
- filtrage
- duplication

Aucune validation métier.

---

### instance.py

Contient :

Classe :

```python
Instance
```

Fonctionnalités :

- stockage complet des données
- index internes
- accès rapides
- calculs utilitaires
- vérification structurelle

Cette classe sera la base :

- du solveur glouton ;
- du modèle CP-SAT ;
- du validateur ;
- des métriques.

---

# Règles importantes

## Règle 1

Ne jamais modifier :

```text
references/
```

Contient :

- schema_contract.md
- solution.schema.json
- instance.schema.json
- validator.py

Ces fichiers sont la référence officielle.

---

## Règle 2

Ne jamais faire de lecture JSON dans core.

Le module core ne dépend :

- ni des parseurs ;
- ni des solveurs ;
- ni du validateur.

---

## Règle 3

Le module core doit rester indépendant.

Dépendance autorisée :

```text
core
```

Dépendances interdites :

```text
core -> parsers
core -> metrics
core -> validation
core -> solvers
```

---

## Règle 4

Aucune logique métier ne doit être dupliquée.

Si une fonctionnalité existe déjà dans core, elle doit être réutilisée.

---

# Prochaine étape

## Module à développer

```text
src/parsers/
```

Fichiers prévus :

```text
instance_loader.py
solution_loader.py
schema_checker.py
```

Objectif :

Transformer les fichiers JSON en objets métier.

Ces modules dépendront de :

```text
core
```

mais core ne devra jamais dépendre d'eux.

---

# Étapes futures

Ordre obligatoire :

1. parsers
2. preprocessing
3. validation
4. metrics
5. greedy solver
6. cp-sat solver
7. local search
8. hybrid solver
9. benchmarking
10. exporters
11. visualization

---

# Responsabilités

Toute modification importante doit mettre à jour :

```text
docs/current_progress.md
```

afin que tous les membres disposent du même état du projet.