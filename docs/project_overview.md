.
├── README.md
├── requirements.txt              # dépendances Python
├── validator.py                  # validateur OFFICIEL (fourni, non modifié)
├── visualiseur.html              # visualiseur officiel (fourni)
├── schema_contract.md            # contrat technique v4.0 (fourni)
├── instance.schema.json          # schéma machine des instances (fourni)
├── solution.schema.json          # schéma machine des solutions (fourni)
├── data/                         # 30 instances + manifest.json/.csv (fournis)
├── examples/                     # mini-démo + gabarit de solution vide (fournis)
├── templates/resultats.csv       # en-tête du CSV de résultats (fourni)
├── tests/                        # tests (validateur officiel + tests de l'équipe)
├── docs/                         # documentation du projet
├── src/soutenances/              # code de l'équipe
│   ├── core/                     # modèle métier
│   ├── parsers/                  # lecture des instances
│   ├── validation/               # contrôle de faisabilité
│   ├── metrics/                  # calcul des 5 critères
│   ├── solvers/                  # GreedySolver, CPSATSolver, HybridSolver
│   ├── benchmarking/             # campagnes d'exécution
│   ├── exporters/                # écriture des solutions et résultats
│   └── visualization/            # graphiques d'analyse
├── scripts/                      # points d'entrée en ligne de commande
└── results/                      # sorties d'expériences