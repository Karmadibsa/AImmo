"""
Script principal de scraping immobilier via FlareSolverr.

Scrape PAP.fr, SeLoger.com et LeBoncoin.fr pour les biens à Toulon (≤ 500 000 €).
Le résultat est sauvegardé dans un unique fichier CSV avec un nom fixe
(pas de timestamp) pour que le frontend puisse toujours lire le même fichier.

Fichier généré (écrasé à chaque run) :
  data/annonces.csv       ← tous sites combinés, lu par le front

Usage :
  # Scraper tous les sites (toutes les pages disponibles)
  python -m scraping.run_scraping

  # Limiter le nombre de pages (utile pour tester)
  python -m scraping.run_scraping --max-pages 5

  # Scraper un seul site
  python -m scraping.run_scraping --site leboncoin

  # FlareSolverr sur un autre hôte (ex: docker-compose)
  python -m scraping.run_scraping --flaresolverr http://flaresolverr:8191
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# Nombre max de pages par défaut — valeur volontairement élevée.
# Le scraper s'arrête tout seul dès qu'une page ne renvoie aucune annonce,
# donc cette limite n'est qu'un filet de sécurité anti-boucle infinie.
MAX_PAGES_DEFAULT = 50
PRIX_MAX = 500_000          # filtre côté client (certains sites ignorent le filtre URL)

import pandas as pd

from scraping.flaresolverr_client import FlareSolverrClient
from scraping.scrapers.leboncoin import LeboncoinScraper
from scraping.scrapers.pap import PapScraper
from scraping.scrapers.seloger import SeLogerScraper

# ─── URLs de recherche configurées ────────────────────────────────────────────
# Toulon (83), appartements + maisons, prix max 500 000 €

SEARCH_URLS: dict[str, str] = {
    "pap": (
        "https://www.pap.fr/annonce/vente-appartement-maison-toulon-83"
        "-g43624-jusqu-a-500000-euros"
    ),
    # URL navigateur standard (plus résistante aux changements Next.js que /classified-search)
    "seloger": (
        "https://www.seloger.com/vente/appartements-maisons/var--83/toulon/"
        "?prix_max=500000"
    ),
    "leboncoin": (
        "https://www.leboncoin.fr/recherche"
        "?category=9"
        "&locations=Toulon__43.125797951705614_5.943649933994845_5849"
        "&price=min-500000"
        "&real_estate_type=1,2"
    ),
}

SCRAPERS: dict[str, type] = {
    "pap": PapScraper,
    "seloger": SeLogerScraper,
    "leboncoin": LeboncoinScraper,
}

OUTPUT_DIR = Path("data")


# ─── Entrée principale ────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("scraping.main")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    sites = list(SCRAPERS.keys()) if args.site == "all" else [args.site]
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    logger.info("=" * 60)
    logger.info("  SCRAPING IMMOBILIER TOULON — ≤ 500 000 €")
    logger.info("=" * 60)
    logger.info(f"  FlareSolverr : {args.flaresolverr}")
    logger.info(f"  Sites        : {', '.join(sites)}")
    logger.info(f"  Pages max    : {args.max_pages} (s'arrête dès qu'une page est vide)")
    logger.info(f"  Sortie       : {output_dir}/annonces.csv  [nom fixe, écrasé à chaque run]")
    logger.info("=" * 60)

    all_dfs: list[pd.DataFrame] = []

    try:
        with FlareSolverrClient(host=args.flaresolverr) as client:
            for site in sites:
                logger.info(f"\n{'─' * 60}")
                logger.info(f"  {site.upper()}")
                logger.info(f"{'─' * 60}")

                scraper = SCRAPERS[site](client)
                url = SEARCH_URLS[site]

                results = scraper.scrape(url, max_pages=args.max_pages, html_dump_dir=args.save_html)
                df = scraper.to_dataframe()

                # ── Nettoyage par site ─────────────────────────────────────
                df = _clean(df, logger, site)
                all_dfs.append(df)
                logger.info(f"[{site.upper()}] {len(df)} annonces propres récupérées")

    except ConnectionError as exc:
        logger.error(f"\n❌  {exc}")
        logger.error(
            "\n  Conseil : lancez FlareSolverr avec :\n"
            "    docker-compose up flaresolverr -d\n"
            "  puis relancez ce script."
        )
        sys.exit(1)

    # ─── Fichier combiné — nom fixe lu par le front ───────────────────────────
    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)
        df_all = _clean(df_all, logger, "all")        # dédup cross-sites
        df_all = _align_dvf_columns(df_all)           # aligne sur le schéma DVF

        combined_path = output_dir / "annonces.csv"   # nom FIXE — lu par le front
        df_all.to_csv(combined_path, index=False, encoding="utf-8-sig")

        logger.info(f"\n{'=' * 60}")
        logger.info("  RÉSUMÉ FINAL")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Scraping effectué le : {scraped_at}")
        logger.info(f"  Total annonces nettes : {len(df_all)}")
        for source in df_all["source"].unique():
            n = len(df_all[df_all["source"] == source])
            prix_med = df_all.loc[df_all["source"] == source, "valeur_fonciere"].median()
            logger.info(f"    • {source:<12} : {n:>4} annonces  |  prix médian: {prix_med:,.0f} €")
        logger.info(f"\n  Fichier combiné (front) : {combined_path}")
        logger.info(f"{'=' * 60}\n")
    else:
        logger.warning("Aucune annonce récupérée. Vérifiez FlareSolverr et les URLs.")


# ─── Alignement colonnes DVF ──────────────────────────────────────────────────

def _split_localisation(loc: str) -> tuple[str | None, str | None]:
    """Extrait (nom_commune, code_postal) depuis 'Toulon (83000)' ou 'Toulon 83000'."""
    if not isinstance(loc, str) or not loc.strip():
        return None, None
    m = re.search(r"^(.+?)\s*\(?\s*(\d{5})\s*\)?$", loc.strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return loc.strip(), None


def _align_dvf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomme et restructure les colonnes de annonces.csv pour les aligner
    sur le schéma de dvf_toulon.csv afin de faciliter les analyses croisées.

    Mapping :
      prix        → valeur_fonciere
      surface     → surface_reelle_bati
      nb_pieces   → nombre_pieces_principales
      type_bien   → type_local
      date_scraped→ date_mutation
      localisation→ nom_commune + code_postal + code_departement

    Colonnes DVF sans équivalent scraping ajoutées vides :
      longitude, latitude
    """
    df = df.copy()

    # ── Renommages directs ────────────────────────────────────────────────────
    df = df.rename(columns={
        "prix":       "valeur_fonciere",
        "surface":    "surface_reelle_bati",
        "nb_pieces":  "nombre_pieces_principales",
        "type_bien":  "type_local",
        "date_scraped": "date_mutation",
    })

    # ── Décomposition de localisation ─────────────────────────────────────────
    if "localisation" in df.columns:
        parsed = df["localisation"].map(_split_localisation)
        df["nom_commune"] = parsed.map(lambda x: x[0])
        df["code_postal"]  = parsed.map(lambda x: x[1])
        df["code_departement"] = df["code_postal"].map(
            lambda cp: cp[:2] if isinstance(cp, str) and len(cp) >= 2 else None
        )
        df = df.drop(columns=["localisation"])

    # ── Colonnes DVF sans équivalent (laissées vides) ─────────────────────────
    df["longitude"] = None
    df["latitude"]  = None

    # ── Ordre final des colonnes ──────────────────────────────────────────────
    ordre = [
        "source",
        "type_local",
        "titre",
        "valeur_fonciere",
        "surface_reelle_bati",
        "nombre_pieces_principales",
        "nom_commune",
        "code_postal",
        "code_departement",
        "longitude",
        "latitude",
        "description",
        "url",
        "date_mutation",
    ]
    # Garde uniquement les colonnes présentes (sécurité)
    ordre = [c for c in ordre if c in df.columns]
    df = df[ordre]

    return df


# ─── Nettoyage post-scraping ──────────────────────────────────────────────────


# Domaines officiels attendus par scraper — toute URL hors-domaine est rejetée
# (ex: PAP redirige les programmes neufs vers immoneuf.com)
_DOMAINE_PAR_SITE: dict[str, str] = {
    "pap":       "pap.fr",
    "seloger":   "seloger.com",
    "leboncoin": "leboncoin.fr",
}


def _clean(df: pd.DataFrame, logger, label: str) -> pd.DataFrame:
    """
    Nettoie un DataFrame d'annonces :
      1. Supprime les doublons par URL
      2. Filtre les URLs hors-domaine (ex : PAP → immoneuf.com)
      3. Filtre les prix > PRIX_MAX
      4. Supprime les annonces sans surface (inutilisables pour l'analyse)
    """
    n_avant = len(df)

    # 1. Dédoublonnage sur l'URL normalisée (sans query string de pagination)
    if "url" in df.columns:
        df = df.drop_duplicates(subset=["url"], keep="first")
        n_dup = n_avant - len(df)
        if n_dup:
            logger.info(f"[{label.upper()}] {n_dup} doublons supprimés (même URL)")

    # 2. Filtre les URLs hors-domaine (ne s'applique qu'aux passes par-site, pas "all")
    domaine_attendu = _DOMAINE_PAR_SITE.get(label)
    if domaine_attendu and "url" in df.columns:
        masque_domaine = df["url"].isna() | df["url"].str.contains(domaine_attendu, na=False)
        n_hors_domaine = (~masque_domaine).sum()
        df = df[masque_domaine]
        if n_hors_domaine:
            logger.info(
                f"[{label.upper()}] {n_hors_domaine} annonces hors-domaine supprimees "
                f"(URL hors '{domaine_attendu}' - ex: redirections partenaires)"
            )

    # 3. Filtre prix > 500 000 €
    if "prix" in df.columns:
        masque_prix = df["prix"].isna() | (df["prix"] <= PRIX_MAX)
        n_hors_budget = (~masque_prix).sum()
        df = df[masque_prix]
        if n_hors_budget:
            logger.info(f"[{label.upper()}] {n_hors_budget} annonces > {PRIX_MAX:,} € supprimées")

    # 4. Supprime les annonces sans surface (inutilisables pour l'analyse immobilière)
    if "surface" in df.columns:
        masque_sans_surface = df["surface"].isna()
        n_sans_surface = masque_sans_surface.sum()
        df = df[~masque_sans_surface]
        if n_sans_surface:
            logger.info(f"[{label.upper()}] {n_sans_surface} annonces sans surface supprimées")

    return df.reset_index(drop=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scraping immobilier Toulon via FlareSolverr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES_DEFAULT,
        metavar="N",
        help=f"Nombre max de pages par site (défaut: {MAX_PAGES_DEFAULT}, s'arrête dès qu'une page est vide)",
    )
    parser.add_argument(
        "--site",
        choices=[*SCRAPERS.keys(), "all"],
        default="all",
        help="Site à scraper : pap | seloger | leboncoin | all (défaut: all)",
    )
    parser.add_argument(
        "--flaresolverr",
        default="http://localhost:8191",
        metavar="URL",
        help="URL de FlareSolverr (défaut: http://localhost:8191)",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        metavar="DIR",
        help=f"Dossier de sortie (défaut: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--save-html",
        default=None,
        metavar="DIR",
        help=(
            "Sauvegarde le HTML brut de chaque page dans DIR (ex: debug_html/). "
            "Utile pour déboguer quand un site change de structure. "
            "Exemple : --save-html debug_html"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
