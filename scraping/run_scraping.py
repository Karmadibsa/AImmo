"""
Script principal de scraping immobilier via FlareSolverr.

Scrape PAP.fr, SeLoger.com et LeBoncoin.fr pour les biens à Toulon (≤ 500 000 €).
Les résultats sont sauvegardés dans donnees/ sous forme de CSV avec des noms fixes
(pas de timestamp) pour que le frontend puisse toujours lire le même fichier.

Fichiers générés (écrasés à chaque run) :
  donnees/scraping_pap.csv
  donnees/scraping_seloger.csv
  donnees/scraping_leboncoin.csv
  donnees/scraping_all.csv       ← fichier combiné lu par le front

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
import sys
from datetime import datetime
from pathlib import Path

# Nombre max de pages par défaut — valeur volontairement élevée.
# Le scraper s'arrête tout seul dès qu'une page ne renvoie aucune annonce,
# donc cette limite n'est qu'un filet de sécurité anti-boucle infinie.
MAX_PAGES_DEFAULT = 50

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
    "seloger": (
        "https://www.seloger.com/classified-search"
        "?distributionTypes=Buy"
        "&estateTypes=House,Apartment"
        "&locations=AD08FR34378"
        "&priceMax=500000"
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

OUTPUT_DIR = Path("donnees")


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
    logger.info(f"  Sortie       : {output_dir}/  [noms fixes, écrasés à chaque run]")
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

                results = scraper.scrape(url, max_pages=args.max_pages)
                df = scraper.to_dataframe()
                all_dfs.append(df)

                # CSV individuel par site — nom fixe (écrasé à chaque run)
                csv_path = output_dir / f"scraping_{site}.csv"
                scraper.save_csv(str(csv_path))

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
        combined_path = output_dir / "scraping_all.csv"       # nom FIXE
        df_all.to_csv(combined_path, index=False, encoding="utf-8-sig")

        logger.info(f"\n{'=' * 60}")
        logger.info("  RÉSUMÉ FINAL")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Scraping effectué le : {scraped_at}")
        logger.info(f"  Total annonces       : {len(df_all)}")
        for source in df_all["source"].unique():
            n = len(df_all[df_all["source"] == source])
            prix_med = df_all.loc[df_all["source"] == source, "prix"].median()
            logger.info(f"    • {source:<12} : {n:>4} annonces  |  prix médian: {prix_med:,.0f} €")
        logger.info(f"\n  Fichier combiné (front) : {combined_path}")
        logger.info(f"{'=' * 60}\n")
    else:
        logger.warning("Aucune annonce récupérée. Vérifiez FlareSolverr et les URLs.")


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
    return parser.parse_args()


if __name__ == "__main__":
    main()
