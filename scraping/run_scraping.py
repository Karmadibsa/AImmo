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
        "onTheMarket":    [True],   # annonces actives uniquement (évite les archives)
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


def _dpe(val: str | None) -> str | None:
    """Retourne la lettre DPE/GES (A-G) ou None si invalide / non renseigné."""
    return val if val and val in "ABCDEFG" else None


def _pub_date(val: str | None) -> str | None:
    """Filtre les dates epoch (1970) renvoyées par BienIci quand la date est inconnue."""
    return None if not val or val.startswith("1970") else val


# Prix minimum réaliste pour une transaction immobilière
PRIX_MIN = 10_000

def _parse_annonce(ad: dict) -> dict | None:
    """
    Transforme une annonce brute BienIci en ligne prête pour Supabase.
    Filtre et retourne None pour :
      - annonces hors-marché (status.onTheMarket == False)
      - viager avec rente mensuelle (lifeAnnuityMonthlyAllowance > 0)
      - prix < 10 000 € (données corrompues / test)
      - prix ou surface manquants
    Note : le filtre onTheMarket est aussi appliqué côté API (_build_url),
    ce garde Python sert de filet de sécurité.
    """
    # ── 1. Annonces hors-marché (expirées, vendues, retirées) ─────────────────
    status = ad.get("status") or {}
    if status.get("onTheMarket") is False:
        return None

    # ── 2. Viager avec rente mensuelle — prix = rente, pas valeur réelle ──────
    if (ad.get("lifeAnnuityMonthlyAllowance") or 0) > 0:
        return None

    prix    = _to_float(ad.get("price"))
    surface = _to_float(ad.get("surfaceArea"))

    # ── 3. Prix ou surface manquants / prix irréaliste ────────────────────────
    if not prix or not surface or prix < PRIX_MIN:
        return None

    ad_id = ad.get("id", "")

    # ── Type de bien ──────────────────────────────────────────────────────────
    raw_type  = ad.get("propertyType", "")
    type_bien = PROPERTY_TYPE_MAP.get(raw_type)
    if type_bien is None:
        # Filtre strict : on n'accepte que Maison et Appartement.
        # Les programmes neufs, terrains, parkings, etc. sont ignorés.
        return None

    # ── Source (agence ou particulier) ────────────────────────────────────────
    source = ad.get("accountDisplayName") or "BienIci"

    # ── Localisation — district est un dict, pas une string ──────────────────
    district = ad.get("district")
    quartier = (
        district.get("name") if isinstance(district, dict) else None
    ) or ad.get("city") or "Toulon"

    # ── Coordonnées GPS (floutées par BienIci au niveau quartier) ─────────────
    blur = ad.get("blurInfo") or {}
    pos  = blur.get("position") or {}

    # ── Retourne tous les champs disponibles ──────────────────────────────────
    return {
        # ── Identité / base ───────────────────────────────────────────────────
        "lien":               f"https://www.bienici.com/annonce/{ad_id}",
        "titre":              ad.get("title") or f"{type_bien} {surface} m² — {quartier}",
        "prix":               prix,
        "surface":            surface,
        "pieces":             _to_int(ad.get("roomsQuantity")),
        "quartier":           quartier,
        "type_bien":          type_bien,
        "source":             source,
        # ── Détails du bien ───────────────────────────────────────────────────
        "chambres":           _to_int(ad.get("bedroomsQuantity")),
        "sdb":                _to_int(ad.get("bathroomsQuantity")),
        "sde":                _to_int(ad.get("showerRoomsQuantity")),
        "wc":                 _to_int(ad.get("toiletQuantity")),
        "etage":              _to_int(ad.get("floor")),
        "nb_etages":          _to_int(ad.get("floorQuantity")),
        "annee_construction": _to_int(ad.get("yearOfConstruction")),
        "neuf":               ad.get("newProperty"),
        "travaux":            ad.get("workToDo"),
        # ── Énergie / DPE ─────────────────────────────────────────────────────
        "dpe":                _dpe(ad.get("energyClassification")),
        "ges":                _dpe(ad.get("greenhouseGazClassification")),
        "energie_valeur":     _to_int(ad.get("energyValue")),
        # ── Équipements (booléens) ────────────────────────────────────────────
        "ascenseur":          ad.get("hasElevator"),
        "balcon":             ad.get("hasBalcony"),
        "terrasse":           ad.get("hasTerrace"),
        "jardin":             ad.get("hasGarden"),
        "piscine":            ad.get("hasPool"),
        "cave":               ad.get("hasCellar"),
        "parking":            (ad.get("parkingPlacesQuantity") or 0) > 0,
        "nb_parking":         _to_int(ad.get("parkingPlacesQuantity")),
        "cheminee":           ad.get("hasFirePlace"),
        "climatisation":      ad.get("hasAirConditioning"),
        "vue_degagee":        ad.get("hasUnobstructedView"),
        "interphone":         ad.get("hasIntercom"),
        "digicode":           ad.get("hasDoorCode"),
        "gardien":            ad.get("hasCaretaker"),
        "pmr":                ad.get("isDisabledPeopleFriendly"),
        # ── Copropriété ───────────────────────────────────────────────────────
        "copropriete":        ad.get("isInCondominium"),
        "nb_lots_copro":      _to_int(ad.get("condominiumPartsQuantity")),
        "charges_annuelles":  _to_int(ad.get("annualCondominiumFees")),
        "copro_procedure":    ad.get("isCondominiumInProcedure"),
        # ── Localisation ──────────────────────────────────────────────────────
        "latitude":           _to_float(pos.get("lat")),
        "longitude":          _to_float(pos.get("lon")),
        "exposition":         ad.get("exposition") or None,
        # ── Marché ────────────────────────────────────────────────────────────
        "prix_baisse":        ad.get("priceHasDecreased"),
        "prix_m2_bienici":    _to_float(ad.get("pricePerSquareMeter")),
        "type_vendeur":       ad.get("accountType") or None,
        "date_publication":   _pub_date(ad.get("publicationDate")),
        # ── Texte ─────────────────────────────────────────────────────────────
        "description":        ad.get("description") or None,
        "nb_balcons":      _to_int(ad.get("balconyQuantity")),
        "nb_terrasses":    _to_int(ad.get("terracesQuantity")),
        "visite_virtuelle": next(
            (t.get("url") for t in (ad.get("virtualTours") or []) if t.get("url")),
            None,
        ),
        "photos":          [
            p.get("url_photo") or p.get("url")
            for p in (ad.get("photos") or [])
            if p.get("url_photo") or p.get("url")
        ] or None,
    }


# ── Pagination complète ───────────────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """
    Parcourt toutes les pages de l'API BienIci et retourne
    la liste complète des annonces filtrées.
    """
    # Dict lien→annonce pour déduplication en temps réel
    # (BienIci peut retourner la même annonce sur plusieurs pages)
    annonces_map: dict[str, dict] = {}
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
                    f"— {len(annonces_map)} annonces collectées."
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
            total = data.get("total", 0)
            logger.info(f"  → {total} annonces déclarées sur BienIci")

        if not ads:
            logger.info(f"  Page {page + 1} vide — fin de pagination.")
            break

        for ad in ads:
            parsed = _parse_annonce(ad)
            if parsed:
                annonces_map[parsed["lien"]] = parsed  # dedup par lien

        logger.info(
            f"  Page {page + 1}/{MAX_PAGES}"
            f" | {len(ads)} reçues"
            f" | {len(annonces_map)} valides cumulées"
        )

        time.sleep(PAUSE_PAGES)

    annonces = list(annonces_map.values())
    logger.info(f"\n  ✅ Scraping terminé — {len(annonces)} annonces uniques récupérées")
    return annonces


# ── Push Supabase (stratégie hybride) ────────────────────────────────────────

# Seuil de sécurité : on n'écrase la table QUE si le scraping a retourné
# au moins MIN_ANNONCES annonces valides (évite de vider la base si l'API
# plante ou retourne un résultat vide/tronqué).
MIN_ANNONCES = 20


def push_to_supabase(annonces: list[dict]) -> None:
    """
    Stratégie hybride :
      1. Le scraping est déjà terminé et stocké en mémoire (annonces).
      2. Si le nombre d'annonces >= MIN_ANNONCES → on vide la table Supabase
         puis on insère toutes les nouvelles annonces (dataset 100 % propre).
      3. Si trop peu d'annonces → on n'écrase rien et on quitte en erreur.

    Avantages :
      - Pas de données zombies (viager, off-market périmés, etc.)
      - Sûr : la table n'est vidée QUE si le scraping a réussi
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise EnvironmentError(
            "Variables SUPABASE_URL et SUPABASE_KEY manquantes.\n"
            "Définissez-les en variables d'env ou dans les secrets GitHub Actions."
        )

    client = create_client(supabase_url, supabase_key)

    # ── Garde de sécurité ────────────────────────────────────────────────────
    if len(annonces) < MIN_ANNONCES:
        logger.warning(
            f"  ⚠️  Seulement {len(annonces)} annonces récupérées "
            f"(seuil minimum : {MIN_ANNONCES}). "
            "Table Supabase non modifiée pour protéger les données existantes."
        )
        sys.exit(1)

    # ── Étape 1 : Vider la table ─────────────────────────────────────────────
    # On supprime toutes les lignes (filtre générique : lien != chaîne vide,
    # ce qui couvre 100 % des vraies annonces).
    logger.info(f"  🗑️  Suppression de l'ancienne table ({len(annonces)} nouvelles annonces prêtes)…")
    client.table("annonces").delete().neq("lien", "").execute()
    logger.info("  ✅ Table vidée")

    # ── Étape 2 : Insérer le nouveau dataset ─────────────────────────────────
    total_pushed = 0
    for i in range(0, len(annonces), BATCH_SIZE):
        batch = annonces[i : i + BATCH_SIZE]
        client.table("annonces").insert(batch).execute()
        total_pushed += len(batch)
        logger.info(f"  Supabase insert : {total_pushed}/{len(annonces)}")

    logger.info(f"  ✅ {total_pushed} annonces insérées dans Supabase")


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
