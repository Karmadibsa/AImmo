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
import urllib.parse
import urllib.request
from datetime import datetime, timezone

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
PRIX_MAX    = 500_000   # filtre côté API
ZONE_TOULON = "-35280"  # identifiant BienIci pour Toulon
PAUSE_PAGES = 1.5       # secondes entre les pages (respect de l'API)
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

def _parse_annonce(ad: dict, scraped_at: str) -> dict | None:
    """
    Transforme une annonce brute BienIci en ligne prête pour Supabase.
    Retourne None si l'annonce manque de prix ou de surface.
    """
    prix    = ad.get("price")
    surface = ad.get("surfaceArea")

    # Annonces sans prix ni surface : inutilisables pour l'analyse
    if not prix or not surface:
        return None

    ad_id = ad.get("id", "")

    # Type de bien
    raw_type  = ad.get("propertyType", "")
    type_bien = PROPERTY_TYPE_MAP.get(raw_type, raw_type.capitalize() if raw_type else "Autre")

    # Source : nom agence si dispo, sinon particulier / BienIci
    source    = "BienIci"
    agencies  = (ad.get("userRelativeData") or {}).get("agencies", [])
    if agencies and agencies[0].get("name"):
        source = agencies[0]["name"]
    elif ad.get("accountDisplayName"):
        source = ad["accountDisplayName"]

    # Localisation
    quartier = ad.get("district") or ad.get("city") or "Toulon"

    return {
        "lien":         f"https://www.bienici.com/annonce/{ad_id}",
        "titre":        ad.get("title") or f"{type_bien} {surface} m² — {quartier}",
        "prix":         float(prix),
        "surface":      float(surface),
        "pieces":       ad.get("roomsQuantity"),
        "quartier":     quartier,
        "type_bien":    type_bien,
        "source":       source,
        "description":  ad.get("description") or "",
        "date_scraped": scraped_at,
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
    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info("Démarrage du scraping BienIci (Toulon, ≤ 500 000 €)…")

    while True:
        url  = _build_url(page_from)
        data = _fetch_page(url)
        ads  = data.get("realEstateAds", [])

        # Premier appel : on lit le total disponible dans l'API
        if total is None:
            total    = data.get("total", 0)
            nb_pages = (total // PAGE_SIZE) + (1 if total % PAGE_SIZE else 0)
            logger.info(f"  → {total} annonces disponibles (~{nb_pages} pages)")

        if not ads:
            break

        for ad in ads:
            parsed = _parse_annonce(ad, scraped_at)
            if parsed:
                annonces.append(parsed)

        logger.info(
            f"  Page {page_from // PAGE_SIZE + 1}"
            f" | {len(ads)} reçues"
            f" | {len(annonces)} valides cumulées"
        )

        page_from += PAGE_SIZE
        if page_from >= (total or 0):
            break

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
