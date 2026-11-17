# Protocole d'Expérimentation

## Objectif

Ce document définit la méthodologie utilisée pour évaluer les performances des solveurs développés dans le projet.

L'objectif est de garantir :

- la reproductibilité ;
- l'équité des comparaisons ;
- la cohérence des résultats ;
- la validité scientifique des conclusions.

---

# Solveurs Évalués

Les expérimentations portent sur les solveurs suivants :

```text
Greedy Solver

Local Search Solver

CP-SAT Solver

Hybrid Solver
```

---

# Objectifs des Expériences

Les expériences doivent permettre de mesurer :

- la validité des solutions ;
- la qualité des solutions ;
- le temps d'exécution ;
- la robustesse ;
- la capacité d'amélioration des solveurs.

---

# Protocole Général

Chaque expérimentation suit le workflow suivant :

```text
Instance
    ↓
Prétraitement
    ↓
Solveur
    ↓
Validation
    ↓
Évaluation
    ↓
Collecte des résultats
```

---

# Vérification de Validité

Avant toute analyse :

```python
SolutionValidator
```

doit confirmer :

```python
valid = True
```

Une solution invalide est automatiquement rejetée.

---

# Environnement d'Exécution

Toutes les expériences doivent être réalisées dans des conditions similaires.

Les paramètres suivants doivent être documentés :

```text
Version Python

Système d'exploitation

Matériel utilisé

Version OR-Tools
```

---

# Reproductibilité

Toutes les expériences doivent utiliser :

```text
random_seed
```

fixé et documenté.

Exemple :

```python
random_seed = 42
```

---

# Jeux de Données

Les instances sont classées selon leur taille.

---

## Petite Taille

Objectif :

```text
validation fonctionnelle
```

Exemple :

```text
10-20 étudiants
```

---

## Taille Moyenne

Objectif :

```text
comparaison des solveurs
```

Exemple :

```text
30-80 étudiants
```

---

## Grande Taille

Objectif :

```text
analyse de passage à l'échelle
```

Exemple :

```text
100+ étudiants
```

---

# Métriques Collectées

Chaque expérience doit enregistrer :

```text
teacher_presence_days

teacher_idle_slots

teacher_load_range

supervisor_group_breaks

distinct_jury_pairs
```

---

# Temps d'Exécution

Les mesures suivantes sont obligatoires :

```text
temps total

temps preprocessing

temps solveur

temps validation
```

---

# Nombre de Séances

Enregistrer :

```text
nombre d'étudiants

nombre de pré-soutenances

nombre de finales

nombre total de séances
```

---

# Expériences Greedy

Objectif :

Mesurer la qualité de la solution initiale.

Enregistrer :

```text
temps

statut

métriques

étudiants non placés
```

---

# Expériences Local Search

Objectif :

Mesurer la capacité d'amélioration.

Enregistrer :

```text
score initial

score final

gain

temps

nombre d'itérations

mouvements acceptés
```

---

# Expériences CP-SAT

Objectif :

Mesurer la qualité d'optimisation.

Enregistrer :

```text
temps

solution trouvée

objective value

gap

statut
```

---

# Expériences Hybrid

Objectif :

Mesurer l'intérêt de la combinaison des solveurs.

Comparer :

```text
Greedy

Greedy + Local Search

Greedy + Local Search + CP-SAT
```

---

# Comparaison des Solveurs

Pour chaque instance :

| Critère | Greedy | Local Search | CP-SAT | Hybrid |
|----------|----------|----------|----------|----------|
| Temps | | | | |
| Validité | | | | |
| f1 | | | | |
| f2 | | | | |
| f3 | | | | |
| f4 | | | | |
| f5 | | | | |

---

# Analyse de Performance

Les résultats doivent permettre de répondre aux questions :

---

## Qualité

Quel solveur produit les meilleures solutions ?

---

## Rapidité

Quel solveur est le plus rapide ?

---

## Robustesse

Quel solveur échoue le moins souvent ?

---

## Scalabilité

Comment évoluent les performances lorsque la taille du problème augmente ?

---

# Analyse de l'Amélioration

Comparaisons attendues :

```text
Greedy
    ↓
Local Search
```

Puis :

```text
Local Search
    ↓
CP-SAT
```

Puis :

```text
CP-SAT
    ↓
Hybrid
```

---

# Représentation des Résultats

Les résultats peuvent être présentés sous forme :

```text
Tableaux

Graphiques

Diagrammes

Rapports CSV
```

---

# Conservation des Résultats

Chaque expérience doit enregistrer :

```text
configuration

instance

graine

date

résultat
```

afin de permettre une reproduction exacte.

---

# Critères d'Acceptation

Une expérimentation est considérée valide si :

```text
solution valide

métriques calculées

temps mesuré

configuration enregistrée
```

---

# Menaces à la Validité

Les facteurs suivants doivent être surveillés :

- aléatoire non contrôlé ;
- instances trop petites ;
- temps limite trop faible ;
- biais dans les jeux de test.

---

# Conclusion

Toutes les expérimentations du projet doivent suivre ce protocole afin de garantir :

- des comparaisons équitables ;
- des résultats reproductibles ;
- une analyse rigoureuse des solveurs ;
- une exploitation fiable des résultats dans le rapport final.