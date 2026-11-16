# Guide de Développement (Development Guide)

Ce guide fournit les instructions essentielles pour les développeurs et participants désireux de contribuer au code source, d'exécuter les tests et de respecter les normes de qualité du projet.

## 1. Configuration de l'Environnement de Développement

### Prérequis
* **Python** : Version 3.10 ou supérieure[cite: 3].
* **Environnement Virtuel** : Recommandé pour isoler les dépendances du projet.

### Installation Pas à Pas
```bash
# 1. Créer l'environnement virtuel
python -m venv venv

# 2. Activer l'environnement virtuel
# Sur Linux / macOS :
source venv/bin/activate
# Sur Windows :
venv\Scripts\activate

# 3. Installer les dépendances du projet
pip install --upgrade pip
pip install -r requirements.txt