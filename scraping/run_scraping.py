"""
Scraping immobilier BienIci → Supabase.

Architecture :
  - Appel direct à l'API JSON publique de BienIci (sans FlareSolverr)
  - Pagination automatique : récupère la totalité des annonces disponibles
  - Upsert vers Supabase par lots (lien = clé primaire, pas de doublons)
  - Exécuté quotidiennement par GitHub Actions ou manuellement

Variables d'environnement requises (secrets GitHub Actions) :
  SUPABASE_URL  — URL du projet Supabase (ex: https://xxxx.supabase.co)
  SUPABASE_KEY  — Clé publique anon key

Usage local (pour tester) :
  SUPABASE_URL=... SUPABASE_KEY=... python -m scraping.run_scraping
"""

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from supabase import create_client

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scraping.bienici")

# ── Constantes ────────────────────────────────────────────────────────────────
BIENICI_API = "https://www.bienici.com/realEstateAds.json"
PAGE_SIZE   = 24        # nb annonces par page (max accepté par l'API)
MAX_PAGES   = 100       # plafond de sécurité : 100 × 24 = 2 400 annonces max
                        # (BienIci bloque les offsets > ~2 500 avec HTTP 400)
PRIX_MAX    = 500_000   # filtre côté API
ZONE_TOULON = "-35280"  # identifiant BienIci pour Toulon
PAUSE_PAGES = 0.8       # secondes entre les pages
BATCH_SIZE  = 500       # taille des lots pour l'upsert Supabase

# Mapping propertyType BienIci → libellé français (schéma DVF / Streamlit)
PROPERTY_TYPE_MAP: dict[str, str] = {
    "house": "Maison",
    "flat":  "Appartement",
}


# ── Construction de l'URL API ─────────────────────────────────────────────────

def _build_url(page_from: int) -> str:
    """Construit l'URL de l'API BienIci avec pagination et filtres Toulon."""
    filters = {
        "size":           PAGE_SIZE,
        "from":           page_from,
        "filterType":     "buy",
        "propertyType":   ["house", "flat"],
        "maxPrice":       PRIX_MAX,
        "zoneIdsByTypes": {"zoneIds": [ZONE_TOULON]},
    }
    return BIENICI_API + "?filters=" + urllib.parse.quote(json.dumps(filters))


# ── Requête HTTP ──────────────────────────────────────────────────────────────

def _fetch_page(url: str) -> dict:
    """Appelle l'API BienIci et retourne le JSON parsé."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept":          "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer":         "https://www.bienici.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


# ── Parsing d'une annonce ─────────────────────────────────────────────────────

def _to_float(val) -> float | None:
    """
    Convertit en float de manière robuste.
    Gère les cas où l'API BienIci retourne une liste (fourchette de prix)
    ou une valeur nulle/invalide.
    """
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0] if val else None
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val) -> int | None:
    """Convertit en int via _to_float — gère aussi les listes (ex: roomsQuantity)."""
    f = _to_float(val)
    return int(f) if f is not None else None


def _parse_annonce(ad: dict) -> dict | None:
    """
    Transforme une annonce brute BienIci en ligne prête pour Supabase.
    Retourne None si l'annonce manque de prix ou de surface.
    """
    prix    = _to_float(ad.get("price"))
    surface = _to_float(ad.get("surfaceArea"))

    # Annonces sans prix ni surface : inutilisables pour l'analyse
    if not prix or not surface:
        return None

    ad_id = ad.get("id", "")

    # Type de bien
    raw_type  = ad.get("propertyType", "")
    type_bien = PROPERTY_TYPE_MAP.get(raw_type, raw_type.capitalize() if raw_type else "Autre")

    # Source : nom agence si dispo, sinon particulier / BienIci
    source   = "BienIci"
    agencies = (ad.get("userRelativeData") or {}).get("agencies", [])
    if agencies and agencies[0].get("name"):
        source = agencies[0]["name"]
    elif ad.get("accountDisplayName"):
        source = ad["accountDisplayName"]

    # Localisation
    quartier = ad.get("district") or ad.get("city") or "Toulon"

    return {
        "lien":      f"https://www.bienici.com/annonce/{ad_id}",
        "titre":     ad.get("title") or f"{type_bien} {surface} m² — {quartier}",
        "prix":      prix,
        "surface":   surface,
        "pieces":    _to_int(ad.get("roomsQuantity")),
        "quartier":  quartier,
        "type_bien": type_bien,
        "source":    source,
    }


# ── Pagination complète ───────────────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """
    Parcourt toutes les pages de l'API BienIci et retourne
    la liste complète des annonces filtrées.
    """
    annonces:  list[dict] = []
    page_from: int        = 0
    total:     int | None = None

    logger.info("Démarrage du scraping BienIci (Toulon, ≤ 500 000 €)…")

    for page in range(MAX_PAGES):
        page_from = page * PAGE_SIZE
        url = _build_url(page_from)

        try:
            data = _fetch_page(url)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                # Limite de pagination BienIci atteinte — on sort proprement
                logger.info(
                    f"  ⚠️  HTTP 400 à la page {page + 1} (offset {page_from}) "
                    f"— {len(annonces)} annonces collectées."
                )
            else:
                logger.warning(f"  ⚠️  HTTP {e.code} page {page + 1} : {e}")
            break
        except Exception as exc:
            logger.warning(f"  ⚠️  Erreur page {page + 1} : {exc}")
            break

        ads = data.get("realEstateAds", [])

        # Première page : affiche le total déclaré par l'API
        if page == 0:
            total    = data.get("total", 0)
            logger.info(f"  → {total} annonces déclarées sur BienIci")

        if not ads:
            logger.info(f"  Page {page + 1} vide — fin de pagination.")
            break

        for ad in ads:
            parsed = _parse_annonce(ad)
            if parsed:
                annonces.append(parsed)

        logger.info(
            f"  Page {page + 1}/{MAX_PAGES}"
            f" | {len(ads)} reçues"
            f" | {len(annonces)} valides cumulées"
        )

        time.sleep(PAUSE_PAGES)

    logger.info(f"\n  ✅ Scraping terminé — {len(annonces)} annonces récupérées")
    return annonces


# ── Upsert Supabase ───────────────────────────────────────────────────────────

def push_to_supabase(annonces: list[dict]) -> None:
    """
    Upsert par lots vers la table `annonces` de Supabase.
    Si un lien existe déjà, la ligne est mise à jour (prix, surface, etc.).
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise EnvironmentError(
            "Variables SUPABASE_URL et SUPABASE_KEY manquantes.\n"
            "Définissez-les en variables d'env ou dans les secrets GitHub Actions."
        )

    client       = create_client(supabase_url, supabase_key)
    total_pushed = 0

    for i in range(0, len(annonces), BATCH_SIZE):
        batch = annonces[i : i + BATCH_SIZE]
        client.table("annonces").upsert(batch, on_conflict="lien").execute()
        total_pushed += len(batch)
        logger.info(f"  Supabase upsert : {total_pushed}/{len(annonces)}")

    logger.info(f"  ✅ {total_pushed} annonces synchronisées dans Supabase")


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("=" * 60)
    logger.info("  SCRAPING BIENICI → SUPABASE")
    logger.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 1. Scraping complet avec pagination
    annonces = scrape_all()

    if not annonces:
        logger.warning("Aucune annonce récupérée — vérifiez l'API BienIci.")
        sys.exit(1)

    # 2. Push vers Supabase
    push_to_supabase(annonces)

    # 3. Résumé final
    types: dict[str, int] = {}
    for a in annonces:
        types[a["type_bien"]] = types.get(a["type_bien"], 0) + 1

    logger.info("\n" + "=" * 60)
    logger.info("  RÉSUMÉ")
    logger.info(f"  Total synchronisé : {len(annonces)} annonces")
    for t, n in sorted(types.items()):
        logger.info(f"    • {t:<15} : {n:>4}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
