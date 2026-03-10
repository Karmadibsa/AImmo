# Scraping Immobilier — Toulon ≤ 500 000 €

Module de scraping des sites immobiliers français via **FlareSolverr**.
Scrape PAP.fr, SeLoger.com et LeBoncoin.fr et produit des CSV standardisés.

---

## Prérequis

| Outil | Version | Pourquoi |
|-------|---------|----------|
| Python | ≥ 3.11 | Script de scraping |
| Docker Desktop | dernière | Lancer FlareSolverr |
| pip packages | voir `requirements.txt` | beautifulsoup4, lxml, pandas, requests |

---

## Installation

```bash
# 1. Installer les dépendances Python
pip install -r requirements.txt

# 2. Démarrer Docker Desktop (icône dans la barre des tâches)
#    Attendre que la baleine 🐳 soit stable (non animée)

# 3. Lancer FlareSolverr (une seule fois, tourne en arrière-plan)
docker-compose up flaresolverr -d

# 4. Vérifier que FlareSolverr est prêt
curl http://localhost:8191
# → doit répondre : {"msg":"FlareSolverr is ready!","version":"..."}
```

---

## Lancer le scraping

Toutes les commandes sont à exécuter depuis la **racine du projet**.

```bash
# ── Cas standard : scraper les 3 sites, toutes les pages disponibles ──
python -m scraping.run_scraping

# ── Tester rapidement (2 pages par site) ──
python -m scraping.run_scraping --max-pages 2

# ── Un seul site ──
python -m scraping.run_scraping --site pap
python -m scraping.run_scraping --site seloger
python -m scraping.run_scraping --site leboncoin

# ── Combiner les deux options ──
python -m scraping.run_scraping --site leboncoin --max-pages 5

# ── FlareSolverr sur un autre port (ex : depuis docker-compose interne) ──
python -m scraping.run_scraping --flaresolverr http://flaresolverr:8191

# ── Changer le dossier de sortie ──
python -m scraping.run_scraping --output data/scraping

# ── Sauvegarder le HTML brut pour déboguer (structure HTML changée ?) ──
python -m scraping.run_scraping --save-html debug_html/
```

---

## Lancer le scheduler (automatique toutes les N heures)

Le scheduler lance `run_scraping` en sous-processus à intervalles réguliers.
Stopper avec **Ctrl+C**.

```bash
# ── Scraping toutes les heures (défaut) — lance un premier run immédiatement ──
python -m scraping.scheduler

# ── Toutes les 2 heures ──
python -m scraping.scheduler --interval 2

# ── Attendre 1 heure avant le premier run (ne pas lancer immédiatement) ──
python -m scraping.scheduler --no-now

# ── Toutes les 30 minutes ──
python -m scraping.scheduler --interval 0.5
```

> **Note** : Le scheduler n'a pas besoin de redémarrer FlareSolverr.
> Si un run échoue (FlareSolverr coupé, site down…), il log l'erreur et réessaie automatiquement au prochain cycle.

---

## Fichiers générés

Le CSV est **écrasé à chaque run** avec un nom fixe (pas de timestamp)
pour que le frontend puisse toujours lire le même fichier.

```
data/
└── annonces.csv     # ← LU PAR LE FRONT (tous sites combinés : PAP + SeLoger + LeBoncoin)
```

### Colonnes du CSV

| Colonne | Type | Description |
|---------|------|-------------|
| `source` | str | Site source (`pap`, `seloger`, `leboncoin`) |
| `type_bien` | str | `Appartement` ou `Maison` (None si inconnu) |
| `titre` | str | Titre de l'annonce |
| `prix` | float | Prix en € (toujours ≤ 500 000) |
| `surface` | float | Surface en m² |
| `nb_pieces` | int | Nombre de pièces |
| `localisation` | str | Ville + code postal |
| `description` | str | Description de l'annonce |
| `url` | str | URL complète de l'annonce |
| `date_scraped` | str | Date/heure du scraping (ISO 8601) |

---

## Nettoyage automatique des données

Le script applique ces filtres **après** le scraping :

1. **Dédoublonnage** sur l'URL → SeLoger répète les annonces "premium" sur plusieurs pages
2. **Filtre prix > 500 000 €** → certains sites ignorent le filtre côté serveur
3. **Suppression des lignes vides** → sans prix ET sans surface (données inutilisables)

---

## Architecture du module

```
scraping/
├── README.md                    ← ce fichier
├── __init__.py
├── flaresolverr_client.py       ← Client HTTP pour FlareSolverr (sessions, GET)
├── run_scraping.py              ← Script CLI principal (scraping ponctuel)
├── scheduler.py                 ← Scheduler automatique (toutes les N heures)
└── scrapers/
    ├── __init__.py
    ├── base.py                  ← Classe de base (pagination, CSV, helpers)
    ├── pap.py                   ← Scraper PAP.fr
    ├── seloger.py               ← Scraper SeLoger.com
    └── leboncoin.py             ← Scraper LeBoncoin.fr
```

### Comment fonctionne FlareSolverr ?

```
python script  ──POST──▶  FlareSolverr (port 8191)
                               │
                               │  Lance Chrome headless
                               │  Résout le challenge Cloudflare
                               │  Attend le rendu JavaScript
                               ▼
                          HTML complet
               ◀──────────────────────────
```

Sans FlareSolverr, LeBoncoin et SeLoger bloquent les requêtes automatisées.

### Stratégies de parsing par site

| Site | Méthode 1 | Méthode 2 | Méthode 3 |
|------|-----------|-----------|-----------|
| LeBoncoin | `__NEXT_DATA__` JSON ⭐ | `data-qa-id` HTML | — |
| SeLoger | `__NEXT_DATA__` JSON ⭐ | JSON-LD Schema.org | HTML + regex |
| PAP | JSON-LD Schema.org ⭐ | HTML sémantique + regex | — |

---

## Dépannage

### `unable to get image` ou `pipe not found`
→ **Docker Desktop n'est pas lancé.** Lance-le depuis le menu Démarrer et attends qu'il soit prêt.

### `Impossible de joindre FlareSolverr sur http://localhost:8191`
→ FlareSolverr n'est pas démarré. Relance :
```bash
docker-compose up flaresolverr -d
```

### `0 annonces` sur un site
→ Le site a changé sa structure HTML. Les sélecteurs CSS du scraper sont à mettre à jour.
Vérifier dans les logs : `[SELOGER] Aucune annonce parsée — vérifiez la structure HTML`.

### Doublons dans le CSV
→ Normalement gérés automatiquement. Si ça persiste, vérifier que `_clean()` est bien appelé dans `run_scraping.py`.
