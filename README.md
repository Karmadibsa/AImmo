# AImmo : Observatoire du Marché Immobilier Toulonnais

AImmo est un outil intelligent d'aide à la recherche et à l'analyse immobilière, conçu sous la forme d'une application web déployée. Ce projet a pour objectif d'accompagner les particuliers (notamment les couples) et les professionnels (agents immobiliers) en leur simplifiant l'accès et l'analyse du marché de l'immobilier toulonnais en temps réel, tout en s'appuyant sur des algorithmes statistiques développés from scratch et sur l'Intelligence Artificielle.

## Fonctionnalités Principales

AImmo offre un éventail d'outils et de services pour répondre aux besoins clés de la recherche immobilière :
- **Centralisation des recherches** : Regroupement exhaustif des biens pertinents de l'utilisateur.
- **Tableau de bord et recommandations** : Interface Streamlit permettant de filtrer selon des critères personnalisés et de visualiser les résultats pertinents.
- **Analyse du marché** : Suivi des tendances avec une vision claire et précise pour formuler des offres compétitives.
- **Estimation de prix de vente** : Modèles de prédiction du prix d'un bien immobilier, permettant d'estimer la valeur d'un bien ou de maximiser une plus-value.
- **Assistance conversationnelle** : Chatbot dédié capable d'accompagner les utilisateurs dans leur recherche 24h/24 et 7j/7.
- **Outil Professionnel de génération de rapports** : Édition automatisée de rapports PDF détaillés pour les agents immobiliers et leurs clients.

## L'Équipe et Répartition du Travail

L'équipe est composée d'experts aux profils complémentaires pour mener à bien le projet, de la collecte des données jusqu'à l'interface finale :

| Membre | Rôle | Contributions principales |
|---|---|---|
| **Axel MOMPER** | Data Engineer | Collecte, structuration et stockage des données. |
| **Mathis MICHEAU** | Data Scientist | Analyse et modèles prédictifs, conception des algorithmes. |
| **Benoit MOLLENS** | AI Engineer | Développement de l'assistant conversationnel. |
| **Robin PETIT** | Frontend & DevOps | Interface Streamlit, infrastructure et déploiement. |
| **Julie VANWEYDEVELDT** | Cheffe de Projet | Gestion, organisation et coordination du projet. |

## Structure du Projet

```text
.
├── analysis/
│   ├── stats.py          <- Fonctions statistiques from scratch
│   ├── regression.py     <- Régression linéaire from scratch
│   └── scoring.py        <- Score d'opportunité par bien
├── app/
│   └── streamlit_app.py  <- Dashboard principal
├── data/
│   ├── dvf_toulon.csv    <- Données DVF
│   └── annonces.csv      <- Annonces réelles collectées
├── tests/
│   ├── test_stats.py     <- Tests unitaires pour stats.py
│   ├── test_regression.py <- Tests unitaires pour regression.py
│   └── test_auto_eval.py <- Tests d'évaluation CI (ne pas modifier)
├── docs/
│   ├── REGLES.md     <- Règles du projet
├── presentation/
│   ├── presentation.pptx <- Présentation du projet
│   └── rapport.pdf <- Rapport du projet
├── requirements.txt
└── README.md             <- Documentation du projet
```

## Prérequis et Installation

1. Cloner le dépôt de code :
```bash
git clone https://github.com/nidouillet-mba-2026/AImmo
cd AImmo
```

2. Installer les dépendances requises :
```bash
pip install -r requirements.txt
```

## Lancement Local

Pour exécuter l'application sur un environnement local :
```bash
streamlit run app/streamlit_app.py
```

## Déploiement

URL de l'application déployée : [À compléter]

## Données et Références

- **DVF** : Données de Demande de Valeurs Foncières téléchargées depuis [data.gouv.fr](https://dvf-api.data.gouv.fr/dvf/csv/?com=83137).
- **Annonces** : Données collectées via script Python ou outil externe tel que GumLoop (date à préciser).
- **Références techniques** : Méthodologie et algorithmes basés sur l'ouvrage "Data Science From Scratch" (Joel Grus), chapitres 5 (Statistiques) et 14 (Régression linéaire).

## Intégration Continue et Évaluation

L'évaluation automatique du projet s'effectue via l'Intégration Continue (CI) configurée sur les GitHub Actions. À chaque soumission de code (`git push`), une suite de tests permet d'évaluer automatiquement le travail effectué.
- Le score CI est calculé sur 55 points (les 45 points restants sont évalués en soutenance).
- Les résultats des analyses sont disponibles dans l'onglet Actions du dépôt GitHub (dernier workflow > Job Summary).
