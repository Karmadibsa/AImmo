"""
Scraper pour LeBoncoin.fr.

Stratégie principale : extraction du JSON __NEXT_DATA__ injecté par Next.js.
  → Chemin : props.pageProps.searchData.ads (+ variantes)
  → Chaque annonce contient : subject, price, attributes (surface/pièces),
    location, url, body (description)

Fallback HTML : attributs data-qa-id si __NEXT_DATA__ est absent/vide.

Pagination : paramètre `page` dans la query string (page=2, page=3…)
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup

from scraping.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.leboncoin.fr"


class LeboncoinScraper(BaseScraper):
    SOURCE = "leboncoin"

    # ─── Point d'entrée parsing ───────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        # Stratégie 1 : __NEXT_DATA__ JSON
        results = self._parse_next_data(html)
        if results:
            logger.debug(f"[LEBONCOIN] __NEXT_DATA__ → {len(results)} annonces")
            return results

        # Stratégie 2 : HTML avec data-qa-id
        results = self._parse_html(html)
        if results:
            logger.debug(f"[LEBONCOIN] HTML fallback → {len(results)} annonces")
            return results

        logger.warning("[LEBONCOIN] Aucune annonce parsée — vérifiez la structure HTML")
        return []

    # ─── Stratégie 1 : __NEXT_DATA__ ─────────────────────────────────────────

    def _parse_next_data(self, html: str) -> list[dict]:
        """Extrait les annonces depuis le bloc JSON __NEXT_DATA__ de Next.js."""
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return []

        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError as e:
            logger.debug(f"[LEBONCOIN] Erreur JSON __NEXT_DATA__: {e}")
            return []

        # Plusieurs chemins possibles selon la version du site
        ads = (
            self._deep_get(data, "props", "pageProps", "searchData", "ads")
            or self._deep_get(data, "props", "pageProps", "ads")
            or self._deep_get(data, "props", "pageProps", "initialSearchData", "ads")
            or self._deep_get(data, "props", "pageProps", "data", "ads")
            or self._deep_get(data, "props", "pageProps", "searchResults", "ads")
        )

        if not ads or not isinstance(ads, list):
            logger.debug("[LEBONCOIN] Chemin ads non trouvé dans __NEXT_DATA__")
            return []

        return [self._normalize_ad(ad) for ad in ads if isinstance(ad, dict)]

    def _normalize_ad(self, ad: dict) -> dict:
        """Transforme une annonce brute LeBoncoin en listing normalisé."""

        # ── Prix ──────────────────────────────────────────────────────────────
        prix = None
        raw_price = ad.get("price") or ad.get("price_cents")
        if isinstance(raw_price, list) and raw_price:
            prix = float(raw_price[0])
            if ad.get("price_cents"):  # conversion centimes → euros
                prix /= 100
        elif isinstance(raw_price, (int, float)):
            prix = float(raw_price)

        # ── Attributs (surface, pièces, type de bien) ─────────────────────────
        surface = None
        nb_pieces = None
        for attr in ad.get("attributes", []):
            key = attr.get("key", "")
            val = attr.get("value") or attr.get("value_label", "")
            if key == "square":
                surface = self._to_float(val)
            elif key == "rooms":
                nb_pieces = self._to_int(val)

        # ── Localisation ──────────────────────────────────────────────────────
        loc = ad.get("location", {}) or {}
        localisation = " ".join(
            filter(None, [loc.get("city"), loc.get("zipcode")])
        ).strip()

        # ── URL ───────────────────────────────────────────────────────────────
        raw_url = ad.get("url", "") or ""
        url = raw_url if raw_url.startswith("http") else f"{BASE_URL}{raw_url}"

        return {
            "source": self.SOURCE,
            "titre": str(ad.get("subject", "")).strip(),
            "prix": prix,
            "surface": surface,
            "nb_pieces": nb_pieces,
            "localisation": localisation,
            "description": str(ad.get("body", "")).strip(),
            "url": url,
        }

    # ─── Stratégie 2 : HTML data-qa-id ───────────────────────────────────────

    def _parse_html(self, html: str) -> list[dict]:
        """
        Fallback : parsing HTML avec attributs data-qa-id de LeBoncoin.
        Donne moins d'informations que __NEXT_DATA__ (surface/pièces absents).
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # LeBoncoin utilise des attributs data-qa-id sur les conteneurs d'annonces
        containers = soup.find_all(attrs={"data-qa-id": "aditem_container"})

        # Fallback si data-qa-id absent (classes générées par CSS modules)
        if not containers:
            containers = soup.select(
                "article[data-id], li[data-id], [class*='adCard'], [class*='listItem']"
            )

        for item in containers:
            try:
                # Titre
                title_el = item.find(attrs={"data-qa-id": "aditem_title"}) or item.find(
                    class_=re.compile(r"title", re.I)
                )
                titre = title_el.get_text(strip=True) if title_el else ""

                # Prix
                price_el = item.find(attrs={"data-qa-id": "aditem_price"}) or item.find(
                    class_=re.compile(r"price|prix", re.I)
                )
                prix = self._to_float(price_el.get_text()) if price_el else None

                # Localisation
                loc_el = item.find(attrs={"data-qa-id": "aditem_location"})
                localisation = loc_el.get_text(strip=True) if loc_el else ""

                # URL
                link = item.find("a", href=True)
                raw_url = link["href"] if link else ""
                url = raw_url if raw_url.startswith("http") else f"{BASE_URL}{raw_url}"

                # Surface (regex dans le texte)
                text = item.get_text(" ", strip=True)
                surface = None
                m = re.search(r"([\d,. ]+)\s*m²", text)
                if m:
                    surface = self._to_float(m.group(1))

                # Pièces (regex)
                nb_pieces = None
                m = re.search(r"(\d+)\s*pièce", text, re.I)
                if m:
                    nb_pieces = int(m.group(1))

                results.append(
                    {
                        "source": self.SOURCE,
                        "titre": titre,
                        "prix": prix,
                        "surface": surface,
                        "nb_pieces": nb_pieces,
                        "localisation": localisation,
                        "description": "",
                        "url": url,
                    }
                )
            except Exception as e:
                logger.debug(f"[LEBONCOIN] Erreur parsing item: {e}")

        return results

    # ─── Pagination ───────────────────────────────────────────────────────────

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """Incrémente le paramètre `page` dans l'URL LeBoncoin."""
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        # Reconstruction de la query string sans double-encodage
        parts = []
        for k, vs in qs.items():
            for v in vs:
                parts.append(f"{k}={v}")
        return urlunparse(parsed._replace(query="&".join(parts)))

    # ─── Utilitaire ───────────────────────────────────────────────────────────

    @staticmethod
    def _deep_get(obj: dict, *keys):
        """Accès sécurisé à un chemin de clés dans un dict imbriqué."""
        for key in keys:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
        return obj
