# Jury-scheduling — Optimisation de Plannings de Soutenances

Ce dépôt héberge le projet académique et compétitif de planification automatique de soutenances pour la Licence 3 en Intelligence Artificielle de l'Institut de Formation et de Recherche en Informatique (IFRI) de l'Université d’Abomey-Calavi, sous la direction du Dr Ing. (MC) Houndji Vinasetan Ratheil.

## 📋 Contexte et Objectifs

Le projet s'inscrit dans le cadre des outils de résolution de problèmes d'optimisation combinatoire et de recherche opérationnelle. L'objectif principal est de concevoir, implémenter et évaluer des algorithmes de résolution (heuristiques gloutonnes, programmation par contraintes CP-SAT, et approches hybrides) capables de planifier automatiquement les pré-soutenances (en ligne) et les soutenances finales (en présentiel) des étudiants tout en satisfaisant un ensemble strict de contraintes métier et en minimisant plusieurs indicateurs de performance.

## 🏗️ Architecture du Projet

Le dépôt suit une structure modulaire rigoureuse et normalisée, garantissant une séparation claire entre les données, le cœur logique, les validateurs, les solveurs et la documentation :

* `data/` : Contient les instances brutes (`raw/`), transformées (`processed/`), les solutions générées et les résultats de benchmarks.
* `docs/` : Documentation technique académique détaillée du projet.
* `src/` : Code source modulaire organisé par domaine (core, parsers, preprocessing, validation, metrics, solvers, benchmarking, exporters, visualization, utils).
* `scripts/` : Scripts utilitaires pour la migration, la validation, les benchmarks et la génération de rapports.
* `notebooks/` : Notebooks Jupyter pour l'analyse exploratoire et la comparaison des solveurs.
* `tests/` : Suite de tests unitaires et d'intégration.
* `results/` : Sorties des différents solveurs et rapports graphiques.
* `references/` : Schémas JSON officiels (v4.0) et contrats de spécification.

## 🚀 Démarrage Rapide

1. **Clonage et Installation** :
   Le projet nécessite Python 3.10 ou supérieur. Aucune bibliothèque externe complexe n'est exigée pour le socle de validation de base.
   ```bash
   git clone <url-du-depot>
   cd jury-scheduling-hackathon
   pip install -r requirements.txt