# Architecture Logicielle (Software Architecture)

## 1. Principes Directeurs et Design Patterns

L'architecture logicielle du projet repose sur les principes de la programmation orientée objet, de la séparation des préoccupations (*Separation of Concerns*) et de la modularité stricte. 

Les choix architecturaux garantissent :
* **Indépendance des couches** : Le cœur de modélisation (`src/core/`) est découplé des mécanismes de persistance (`src/parsers/`) et des algorithmes de résolution (`src/solvers/`).
* **extensibilité** : L'ajout d'un nouveau solveur ou d'une nouvelle métrique s'effectue sans modifier le code existant, grâce à l'utilisation de classes abstraites de base (`BaseSolver`).
* **Traçabilité et Conformité** : Chaque solution produite est validée par un validateur centralisé garantissant l'intégrité par rapport au contrat de schéma v4.0[cite: 1].

## 2. Flux de Données (Data Flow)

Le cycle de vie des données au sein de l'application suit un pipeline déterministe en quatre étapes majeures :

1. **Ingestion et Parsing** : 
   Les fichiers JSON bruts sont lus via `src/parsers/instance_loader.py`. Les dictionnaires et structures sont contrôlés par `src/parsers/schema_checker.py` et convertis en objets du domaine (`src/core/`).
2. **Prétraitement** : 
   Le module `src/preprocessing/` filtre les domaines, construit les matrices de disponibilité et extrait les candidats potentiels pour les jurys.
3. **Résolution (Optimisation)** : 
   L'un des solveurs actifs (`GreedySolver`, `CPSATSolver` ou l'orientation architecturale `HybridSolver`) prend en entrée l'instance prétraitée et produit un objet `Solution`[cite: 3].
4. **Validation et Évaluation** : 
   La solution générée est soumise au module `src/validation/solution_validator.py` pour vérifier la satisfaction de toutes les contraintes dures. Si elle est valide, le module `src/metrics/evaluate.py` calcule le vecteur des cinq métriques d'optimisation[cite: 1].

## 3. Rôle des Solveurs et Orientation Hybride

Le projet met en œuvre trois composantes de résolution principales :
* **`GreedySolver`** : Construit une solution par étapes successives en appliquant des choix locaux optimaux. Idéal pour obtenir rapidement une solution initiale réalisable.
* **`CPSATSolver`** : Traduit le problème en un modèle de satisfaction et d'optimisation de contraintes, résolu via le moteur OR-Tools CP-SAT. Permet d'explorer l'optimalité globale.
* **`HybridSolver`** : Présenté strictement comme une **orientation architecturale**[cite: 3]. Il formalise la possibilité d'utiliser une solution gloutonne pour initialiser un solveur de programmation par contraintes ou d'affiner par recherche locale, sans imposer de pipeline définitif ou figé[cite: 3].

## 4. Importance de la Modmodularité pour un Hackathon

Dans le contexte exigeant d'un hackathon, la modularité rigoureuse de cette architecture procure des avantages décisifs :
* **Travail en Équipe Parallèle** : Différents membres de l'équipe peuvent travailler simultanément sur des modules indépendants (ex: l'un développe les métriques dans `src/metrics/`, l'autre peaufine le solveur CP-SAT dans `src/solvers/cpsatsolver/`, un troisième conçoit les visualisations).
* **Testabilité et Débogage** : Chaque composant dispose de tests unitaires dédiés dans `tests/`, permettant d'isoler rapidement les régressions ou les non-conformités par rapport au schéma v4.0[cite: 1].
* **Flexibilité Expérimentale** : Il est possible de substituer un algorithme de résolution par un autre sans altérer le code d'évaluation ou d'exportation.