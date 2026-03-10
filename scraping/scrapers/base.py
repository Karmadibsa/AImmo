"""
Classe de base pour tous les scrapers immobiliers.

Gère :
  - La boucle de pagination (jusqu'à max_pages pages)
  - L'appel à FlareSolverr via le client
  - La normalisation du schéma de données
  - La sauvegarde CSV
  - Les helpers de conversion (prix, surface, etc.)
"""

import logging
import random
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pandas as pd

from scraping.flaresolverr_client import FlareSolverrClient

logger = logging.getLogger(__name__)

# Schéma standardisé partagé entre tous les scrapers
LISTING_SCHEMA = [
    "source",
    "type_bien",
    "titre",
    "prix",
    "surface",
    "nb_pieces",
    "localisation",
    "description",
    "url",
    "date_scraped",
]


class BaseScraper(ABC):
    """
    Scraper de base.

    À sous-classer en implémentant :
      - `_parse_page(html)` → liste de listings
      - `_next_page(url, page_num)` → URL suivante ou None (optionnel)
    """

    SOURCE: str = "unknown"  # Identifiant du site (ex: "leboncoin")

    def __init__(
        self,
        client: FlareSolverrClient,
        delay: tuple[float, float] = (3.0, 7.0),
    ):
        """
        Args:
            client : Client FlareSolverr configuré
            delay  : Délai aléatoire (min_s, max_s) entre chaque page
        """
        self.client = client
        self.delay = delay
        self.results: list[dict] = []

    # ─── Interface publique ───────────────────────────────────────────────────

    def scrape(self, start_url: str, max_pages: int = 5) -> list[dict]:
        """
        Scrape jusqu'à `max_pages` pages depuis `start_url`.

        Args:
            start_url : URL de la première page de résultats
            max_pages : Nombre maximum de pages à parcourir

        Returns:
            Liste de listings normalisés (voir LISTING_SCHEMA)
        """
        self.results = []
        url: Optional[str] = start_url
        scraped_at = datetime.now().isoformat()

        for page in range(1, max_pages + 1):
            if not url:
                break

            logger.info(f"[{self.SOURCE.upper()}] ── Page {page}/{max_pages} ──")

            try:
                html = self.client.get(url)
                items = self._parse_page(html)

                if not items:
                    logger.warning(
                        f"[{self.SOURCE.upper()}] Aucune annonce page {page} → arrêt pagination"
                    )
                    break

                # Injection des champs meta
                for item in items:
                    item.setdefault("source", self.SOURCE)
                    item.setdefault("date_scraped", scraped_at)

                self.results.extend(items)
                logger.info(
                    f"[{self.SOURCE.upper()}] {len(items)} annonces "
                    f"(cumulé: {len(self.results)})"
                )

                # Page suivante
                url = self._next_page(url, page)
                if url:
                    pause = random.uniform(*self.delay)
                    logger.debug(f"[{self.SOURCE.upper()}] Pause {pause:.1f}s…")
                    time.sleep(pause)

            except Exception as exc:
                logger.error(
                    f"[{self.SOURCE.upper()}] Erreur page {page}: {exc}",
                    exc_info=True,
                )
                break

        logger.info(
            f"[{self.SOURCE.upper()}] Scraping terminé — {len(self.results)} annonces au total"
        )
        return self.results

    def to_dataframe(self) -> pd.DataFrame:
        """Retourne les résultats sous forme de DataFrame avec colonnes standardisées."""
        if not self.results:
            return pd.DataFrame(columns=LISTING_SCHEMA)
        df = pd.DataFrame(self.results)
        # Ordre des colonnes (garde uniquement celles présentes)
        cols = [c for c in LISTING_SCHEMA if c in df.columns]
        return df[cols]

    def save_csv(self, path: str) -> str:
        """
        Sauvegarde les résultats en CSV (encodage UTF-8 avec BOM pour Excel).

        Returns:
            Chemin du fichier créé
        """
        df = self.to_dataframe()
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"[{self.SOURCE.upper()}] Sauvegardé : {path} ({len(df)} lignes)")
        return path

    # ─── À implémenter ────────────────────────────────────────────────────────

    @abstractmethod
    def _parse_page(self, html: str) -> list[dict]:
        """
        Parse le HTML d'une page de résultats et retourne les annonces.

        Chaque annonce doit respecter LISTING_SCHEMA autant que possible.
        """

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """
        Retourne l'URL de la page suivante (page_num + 1).

        Implémentation par défaut : incrémente/ajoute le paramètre `page`
        dans la query string. Surcharger si le site utilise un autre mécanisme.
        """
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        new_query = urlencode({k: v[0] for k, v in qs.items()})
        return urlunparse(parsed._replace(query=new_query))

    # ─── Helpers de conversion ────────────────────────────────────────────────

    @staticmethod
    def _to_float(val) -> Optional[float]:
        """
        Convertit une valeur (str, int, float) en float.

        Gère les formats français :
          - "150 000 €"  → 150000.0
          - "45,5 m²"    → 45.5
          - "1 234,50"   → 1234.5

        Returns None si la conversion échoue.
        """
        if val is None:
            return None
        s = re.sub(r"[€$£\s\u00a0\u202f]", "", str(val).strip())  # retire symboles + espaces
        s = re.sub(r"[m²/]", "", s)  # retire unités
        # Format FR "1 234,56" → "1234.56"
        if "," in s and "." in s:
            # Le point est le séparateur de milliers → l'enlever, virgule = décimale
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        s = re.sub(r"[^\d.]", "", s)
        try:
            return float(s) if s else None
        except ValueError:
            return None

    @staticmethod
    def _to_int(val) -> Optional[int]:
        """
        Convertit une valeur en int.
        Ex: "3 pièces" → 3, "45" → 45.
        Returns None si impossible.
        """
        if val is None:
            return None
        digits = re.sub(r"[^\d]", "", str(val))
        try:
            return int(digits) if digits else None
        except ValueError:
            return None

    @staticmethod
    def _normalize_type_bien(raw: str) -> Optional[str]:
        """
        Normalise le type de bien en "Appartement" ou "Maison".

        Accepte les variantes FR/EN et les abréviations courantes :
          - "apartment", "flat", "studio", "loft", "duplex" → "Appartement"
          - "house", "villa", "pavillon", "maison"          → "Maison"

        Returns None si le type ne peut pas être déterminé.
        """
        if not raw:
            return None
        s = str(raw).lower().strip()
        if any(kw in s for kw in ("appartement", "apartment", "flat", "studio", "loft", "duplex")):
            return "Appartement"
        if any(kw in s for kw in ("maison", "house", "villa", "pavillon")):
            return "Maison"
        return None
