"""
Script principal de scraping immobilier via FlareSolverr.

Scrape PAP.fr, SeLoger.com et LeBoncoin.fr pour les biens à Toulon (≤ 500 000 €).
Les résultats sont sauvegardés dans donnees/ sous forme de CSV.

Usage :
  # Scraper tous les sites (3 pages par défaut)
  python -m scraping.run_scraping

  # Changer le nombre de pages
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
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 60)
    logger.info("  SCRAPING IMMOBILIER TOULON — ≤ 500 000 €")
    logger.info("=" * 60)
    logger.info(f"  FlareSolverr : {args.flaresolverr}")
    logger.info(f"  Sites        : {', '.join(sites)}")
    logger.info(f"  Pages max    : {args.max_pages}")
    logger.info(f"  Sortie       : {output_dir}/")
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

                # CSV individuel par site
                csv_path = output_dir / f"scraping_{site}_{date_str}.csv"
                scraper.save_csv(str(csv_path))

    except ConnectionError as exc:
        logger.error(f"\n❌  {exc}")
        logger.error(
            "\n  Conseil : lancez FlareSolverr avec :\n"
            "    docker-compose up flaresolverr -d\n"
            "  puis relancez ce script."
        )
        sys.exit(1)

    # ─── Fichier combiné ──────────────────────────────────────────────────────
    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)
        combined_path = output_dir / f"scraping_all_{date_str}.csv"
        df_all.to_csv(combined_path, index=False, encoding="utf-8-sig")

        logger.info(f"\n{'=' * 60}")
        logger.info("  RÉSUMÉ FINAL")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Total annonces scrappées : {len(df_all)}")
        for source in df_all["source"].unique():
            n = len(df_all[df_all["source"] == source])
            prix_med = df_all.loc[df_all["source"] == source, "prix"].median()
            logger.info(f"    • {source:<12} : {n:>4} annonces  |  prix médian: {prix_med:,.0f} €")
        logger.info(f"\n  Fichier combiné : {combined_path}")
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
        default=3,
        metavar="N",
        help="Nombre de pages à scraper par site (défaut: 3)",
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
