# Aperçu du Projet (Project Overview)

## 1. Contexte Institutionnel et Pédagogique

Le présent projet s'inscrit dans le cadre du cours d'**Outils de Résolution de Problèmes d’Optimisation** dispensé en **Licence 3 en Intelligence Artificielle** à l'**Institut de Formation et de Recherche en Informatique (IFRI)** de l'**Université d’Abomey-Calavi**, sous la supervision du **Dr Ing. (MC) Houndji Vinasetan Ratheil**[cite: 1, 3]. 

Il met en œuvre des concepts avancés de recherche opérationnelle, d'optimisation combinatoire, de modélisation par contraintes et d'ingénierie logicielle appliquée à un problème réel d'établissement universitaire : la planification des soutenances académiques de fin de cycle[cite: 1, 3].

## 2. Description du Problème d'Optimisation

Le problème consiste à affecter temporellement et spatialement un ensemble d'étudiants, d'enseignants et de salles pour deux phases distinctes et consécutives :
1. **Les pré-soutenances** : Organisées obligatoirement en mode **en ligne**, sans allocation de salles physiques (`room_id: null`). Chaque pré-soutenance requiert un président et un examinateur distincts.
2. **Les soutenances finales** : Organisées en **présentiel** dans des salles physiques dotées de capacités journalières. Chaque soutenance finale requiert le même président, le même examinateur (continuité de jury obligatoire) ainsi qu'un rapporteur fixe (le directeur de mémoire/superviseur)[cite: 1].

### Périodes Temporelles
Le calendrier académique est structuré en jours et créneaux horaires indexés à partir de zéro[cite: 1]. Les jours de pré-soutenance et les jours de soutenance finale appartiennent à des ensembles disjoints et strictement ordonnés : tous les jours de pré-soutenance précèdent chronologiquement les jours de soutenance finale[cite: 1].

## 3. Contraintes Métier (Hard Constraints)

Toute solution valide (conforme au contrat de schéma v4.0) doit respecter sans exception les conditions suivantes[cite: 1] :
* **Disponibilités** : Les enseignants, les étudiants et les salles (pour les finales) doivent être strictement disponibles sur les créneaux et jours assignés[cite: 1].
* **Non-chevauchement (No-Overlap)** : Aucun acteur (enseignant ou étudiant) ne peut participer à deux sessions simultanées[cite: 1]. Les salles physiques ne peuvent héberger qu'une seule soutenance par créneau[cite: 1].
* **Plafonds journaliers** : Le nombre maximal de sessions par jour pour chaque enseignant et chaque salle ne doit pas être dépassé[cite: 1].
* **Éligibilité et Rôles** : Les membres de jury doivent posséder les rôles requis (`president`, `examiner`). L'examinateur doit couvrir le domaine de recherche de l'étudiant, contrairement au président[cite: 1].
* **Continuité du Jury** : Pour un étudiant éligible à la soutenance finale, le président et l'examinateur de la soutenance finale doivent être rigoureusement identiques à ceux de sa pré-soutenance[cite: 1].
* **Intégrité Structurelle** : Chaque session occupe exactement un créneau horaire indivisible `[slot, slot + 1)`[cite: 1].

## 4. Critères d'Optimisation (Soft Constraints & Métriques)

Les performances d'une solution valide sont évaluées à travers un vecteur de cinq métriques normalisées (toutes à minimiser)[cite: 1] :
1. **`teacher_presence_days`** : Somme sur tous les enseignants du nombre de jours distincts comportant au moins une participation[cite: 1].
2. **`teacher_idle_slots`** : Nombre de créneaux creux (trous d'oisiveté) cumulés pour chaque enseignant et chaque jour entre sa première et sa dernière session[cite: 1].
3. **`teacher_load_range`** : Écart entre la charge maximale et la charge minimale de sessions assignées parmi tous les enseignants du système[cite: 1].
4. **`supervisor_group_breaks`** : Pénalisation liée aux ruptures de blocs consécutifs pour les superviseurs (groupes de sessions en ligne ou blocs continus en présentiel)[cite: 1].
5. **`distinct_jury_pairs`** : Nombre de paires ordonnées distinctes `(president_id, examiner_id)` mobilisées à travers l'ensemble des étudiants[cite: 1].

## 5. Approche de Résolution

Dans le cadre, le projet met en œuvre trois solveurs aux paradigmes complémentaires[cite: 3] :
* **`GreedySolver`** : Approche heuristique rapide basée sur des règles de priorité gloutonnes.
* **`CPSATSolver`** : Approche exacte par programmation par contraintes (Google OR-Tools CP-SAT).
* **`HybridSolver`** : Orientation architecturale combinant exploration heuristique et optimisation par contraintes.