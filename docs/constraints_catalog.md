# Catalogue des Contraintes

## Objectif

Ce document recense l'ensemble des contraintes du problème de planification des soutenances.

Les contraintes décrites ici constituent les règles métier officielles du projet.

Toute solution produite par un solveur doit respecter ces contraintes.

La validation officielle est réalisée par :

```python
SolutionValidator
```

---

# Classification des Contraintes

Les contraintes sont classées en deux catégories :

## Contraintes Dures

Une solution qui viole une seule contrainte dure est invalide.

Elles doivent être satisfaites à 100 %.

---

## Contraintes Souples

Les contraintes souples ne rendent pas une solution invalide.

Elles sont optimisées par les métriques.

---

# Contraintes Dures

---

# C1 - Existence des Références

Chaque identifiant utilisé dans une séance doit exister dans l'instance.

Doivent exister :

```text
Étudiant
Président
Examinateur
Salle
```

Violation :

```text
Référence inconnue
```

---

# C2 - Unicité de la Pré-soutenance

Chaque étudiant doit posséder exactement une pré-soutenance.

Formellement :

```text
∀ étudiant

nombre_pré_soutenances = 1
```

---

# C3 - Unicité de la Finale

Si un étudiant est admissible :

```text
eligible_final = True
```

alors il doit posséder exactement une finale.

Formellement :

```text
∀ étudiant admissible

nombre_finales = 1
```

---

# C4 - Interdiction de Finale

Si :

```text
eligible_final = False
```

alors aucune finale ne doit exister.

Formellement :

```text
∀ étudiant non admissible

nombre_finales = 0
```

---

# C5 - Respect des Périodes

Les phases doivent être programmées dans leurs fenêtres respectives.

Pré-soutenance :

```text
jours ∈ PREDEFENCE_PERIOD
```

Finale :

```text
jours ∈ FINAL_PERIOD
```

---

# C6 - Disponibilité de l'Étudiant

Un étudiant ne peut être programmé que lorsqu'il est disponible.

Formellement :

```text
student_available(student, day, slot)
```

---

# C7 - Disponibilité du Président

Le président doit être disponible.

Formellement :

```text
teacher_available(
    president,
    day,
    slot
)
```

---

# C8 - Disponibilité de l'Examinateur

L'examinateur doit être disponible.

Formellement :

```text
teacher_available(
    examiner,
    day,
    slot
)
```

---

# C9 - Disponibilité de l'Encadrant

Pour une finale, l'encadrant doit être disponible.

Formellement :

```text
teacher_available(
    supervisor,
    day,
    slot
)
```

---

# C10 - Absence de Conflit Enseignant

Un enseignant ne peut participer à deux soutenances simultanément.

Formellement :

```text
∀ enseignant

au plus une séance
par (jour, créneau)
```

Cette contrainte s'applique à :

- président ;
- examinateur ;
- encadrant.

---

# C11 - Absence de Conflit Étudiant

Un étudiant ne peut participer à deux soutenances simultanément.

Formellement :

```text
∀ étudiant

au plus une séance
par (jour, créneau)
```

---

# C12 - Distinction Président / Examinateur

Président et examinateur doivent être deux personnes différentes.

Formellement :

```text
president ≠ examiner
```

---

# C13 - Rôle Président

Le président doit posséder le rôle :

```text
PRESIDENT
```

---

# C14 - Rôle Examinateur

L'examinateur doit posséder le rôle :

```text
EXAMINER
```

---

# C15 - Couverture du Domaine

L'examinateur doit couvrir le domaine académique de l'étudiant.

Formellement :

```text
examiner.domaines
⊇
student.domain
```

---

# C16 - Composition du Jury de Finale

Pour une finale :

```text
Président
Examinateur
Encadrant
```

doivent être trois personnes distinctes.

Formellement :

```text
president ≠ examiner

president ≠ supervisor

examiner ≠ supervisor
```

---

# C17 - Continuité du Jury

Le binôme :

```text
(président, examinateur)
```

doit être identique entre :

- pré-soutenance ;
- finale.

Formellement :

```text
jury_predefence
=
jury_final
```

---

# C18 - Salle Interdite en Pré-soutenance

Une pré-soutenance se déroule en ligne.

Par conséquent :

```text
room_id = None
```

---

# C19 - Salle Obligatoire en Finale

Une finale doit être associée à une salle valide.

Formellement :

```text
room_id ≠ None
```

---

# C20 - Disponibilité de Salle

Une salle utilisée doit être disponible.

Formellement :

```text
room_available(
    room,
    day,
    slot
)
```

---

# C21 - Conflit de Salle

Une salle ne peut accueillir qu'une seule soutenance à un instant donné.

Formellement :

```text
∀ salle

au plus une séance
par (jour, créneau)
```

---

# C22 - Capacité Journalière Enseignant

Chaque enseignant possède :

```text
max_sessions_per_day
```

Le nombre de séances affectées dans une journée ne doit jamais dépasser cette limite.

---

# C23 - Capacité Journalière Salle

Chaque salle possède :

```text
max_sessions_per_day
```

Le nombre de finales programmées dans cette salle ne doit jamais dépasser cette limite.

---

# Contraintes Souples

Les contraintes souples sont optimisées par les métriques.

---

# S1 - Réduction des Jours de Présence

Métrique :

```text
teacher_presence_days
```

Objectif :

Limiter le nombre de jours de présence des enseignants.

---

# S2 - Réduction des Temps Morts

Métrique :

```text
teacher_idle_slots
```

Objectif :

Réduire les créneaux vides entre deux soutenances.

---

# S3 - Équilibrage de Charge

Métrique :

```text
teacher_load_range
```

Objectif :

Répartir équitablement les soutenances entre les enseignants.

---

# S4 - Regroupement par Encadrant

Métrique :

```text
supervisor_group_breaks
```

Objectif :

Regrouper les étudiants d'un même encadrant.

---

# S5 - Réduction des Binômes Distincts

Métrique :

```text
distinct_jury_pairs
```

Objectif :

Réutiliser les mêmes couples :

```text
(président, examinateur)
```

sur plusieurs étudiants.

---

# Validation Officielle

Une solution est valide si :

```python
SolutionValidator.validate(...)
```

retourne :

```python
valid = True
```

Toute autre interprétation des contraintes est considérée comme non officielle.

Le validateur constitue la source de vérité du projet.