"""
Scheduler de scraping immobilier — lance run_scraping toutes les N heures.

Usage :
  # Scraping toutes les heures (défaut)
  python -m scraping.scheduler

  # Scraping toutes les 2 heures
  python -m scraping.scheduler --interval 2

  # Scraping immédiat puis toutes les heures
  python -m scraping.scheduler --now

  # Stopper : Ctrl+C

Le scraping tourne en sous-processus : les logs de run_scraping s'affichent
directement dans le terminal. En cas d'erreur, le scheduler continue et
réessaie au prochain cycle.
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta

logger = logging.getLogger("scraping.scheduler")


def run_scraping(extra_args: list[str] = None) -> bool:
    """
    Lance python -m scraping.run_scraping en sous-processus.
    Retourne True si le scraping s'est terminé sans erreur, False sinon.
    """
    cmd = [sys.executable, "-m", "scraping.run_scraping"] + (extra_args or [])
    logger.info(f"Lancement : {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error(f"Le scraping a échoué (code {result.returncode})")
        return False
    return True


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    interval_s = args.interval * 3600  # heures → secondes

    logger.info("=" * 60)
    logger.info("  SCHEDULER SCRAPING IMMOBILIER TOULON")
    logger.info("=" * 60)
    logger.info(f"  Intervalle  : toutes les {args.interval}h")
    logger.info(f"  Démarrage   : {'immédiat' if args.now else f'dans {args.interval}h'}")
    logger.info("  Stopper     : Ctrl+C")
    logger.info("=" * 60)

    # Premier run immédiat si --now (ou si args.now par défaut)
    if args.now:
        logger.info("Lancement immédiat du premier scraping…")
        run_scraping()

    # Boucle principale
    while True:
        next_run = datetime.now() + timedelta(seconds=interval_s)
        logger.info(f"Prochain scraping prévu à : {next_run.strftime('%d/%m/%Y %H:%M:%S')}")

        try:
            time.sleep(interval_s)
        except KeyboardInterrupt:
            logger.info("\nScheduler arrêté par l'utilisateur.")
            break

        logger.info(f"\n{'=' * 60}")
        logger.info(f"  SCRAPING AUTOMATIQUE — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        logger.info(f"{'=' * 60}")
        run_scraping()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scheduler de scraping immobilier (relance toutes les N heures)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="H",
        help="Intervalle entre chaque scraping en heures (défaut: 1)",
    )
    parser.add_argument(
        "--now",
        action="store_true",
        default=True,
        help="Lance un scraping immédiatement au démarrage (défaut: oui)",
    )
    parser.add_argument(
        "--no-now",
        dest="now",
        action="store_false",
        help="Attend le premier intervalle avant de scraper",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
