"""
Scraper pour BienIci.fr.

BienIci est un agrégateur immobilier majeur (groupe SeLoger/Axel Springer)
qui rassemble les annonces de centaines d'agences + particuliers.

Stratégies de parsing (par ordre de priorité) :
  1. JSON inline injecté dans le HTML (window.__data, __REDUX_STATE__, etc.)
  2. JSON-LD Schema.org (RealEstateListing)
  3. HTML sémantique (fallback data-testid / classes CSS)

Pagination : paramètre `page` dans la query string.
URL de recherche :
  https://www.bienici.com/recherche/achat/appartement,maison/toulon-83000/?prix-max=500000
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup

from scraping.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bienici.com"


class BienIciScraper(BaseScraper):
    SOURCE = "bienici"

    # ─── Point d'entrée parsing ───────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        # Stratégie 1 : JSON inline (window.__data etc.)
        results = self._parse_inline_json(html)
        if results:
            logger.debug(f"[BIENICI] JSON inline -> {len(results)} annonces")
            return results

        # Stratégie 2 : JSON-LD
        results = self._parse_jsonld(html)
        if results:
            logger.debug(f"[BIENICI] JSON-LD -> {len(results)} annonces")
            return results

        # Stratégie 3 : HTML sémantique
        results = self._parse_html(html)
        if results:
            logger.debug(f"[BIENICI] HTML -> {len(results)} annonces")
            return results

        soup = BeautifulSoup(html, "lxml")
        title = soup.find("title")
        logger.warning(
            f"[BIENICI] Aucune annonce parsee "
            f"(HTML: {len(html):,} chars, titre: {title.get_text() if title else 'aucun'}). "
            "FlareSolverr a peut-etre renvoye une page bloquee."
        )
        return []

    # ─── Stratégie 1 : JSON inline ───────────────────────────────────────────

    def _parse_inline_json(self, html: str) -> list[dict]:
        """
        BienIci injecte parfois ses données dans un <script> global.
        On cherche les patterns connus : window.__data, __REDUX_STATE__, etc.
        """
        soup = BeautifulSoup(html, "lxml")

        for script in soup.find_all("script"):
            text = script.string or ""
            if not text or len(text) < 100:
                continue

            # Patterns connus de BienIci
            patterns = [
                r'window\.__data\s*=\s*(\{.*?\})\s*;',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
                r'window\.__REDUX_STATE__\s*=\s*(\{.*?\})\s*;',
                r'"realEstateAds"\s*:\s*(\[.*?\])',
            ]

            for pattern in patterns:
                m = re.search(pattern, text, re.DOTALL)
                if not m:
                    continue
                try:
                    data = json.loads(m.group(1))
                    ads = self._find_ads_in_json(data)
                    if ads:
                        return [self._normalize_ad(ad) for ad in ads if isinstance(ad, dict)]
                except (json.JSONDecodeError, ValueError):
                    continue

        return []

    def _find_ads_in_json(self, obj, depth: int = 0, max_depth: int = 8) -> list:
        """Recherche récursive d'une liste d'annonces dans un JSON quelconque."""
        AD_KEYS = {"price", "surfaceArea", "roomsQuantity", "id", "propertyType"}

        def _is_ad_list(lst):
            if len(lst) < 1:
                return False
            hits = sum(1 for x in lst[:5] if isinstance(x, dict) and AD_KEYS & set(x.keys()))
            return hits >= 1

        if depth > max_depth:
            return []
        if isinstance(obj, list) and _is_ad_list(obj):
            return obj
        if isinstance(obj, dict):
            for key in ("realEstateAds", "ads", "listings", "results", "items", "classifieds"):
                if key in obj and isinstance(obj[key], list):
                    result = self._find_ads_in_json(obj[key], depth + 1, max_depth)
                    if result:
                        return result
            for val in obj.values():
                if isinstance(val, (dict, list)):
                    result = self._find_ads_in_json(val, depth + 1, max_depth)
                    if result:
                        return result
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    result = self._find_ads_in_json(item, depth + 1, max_depth)
                    if result:
                        return result
        return []

    # ─── Stratégie 2 : JSON-LD ───────────────────────────────────────────────

    def _parse_jsonld(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, AttributeError):
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                t = item.get("@type", "")
                if t == "ItemList":
                    for elem in item.get("itemListElement", []):
                        it = elem.get("item", elem)
                        r = self._normalize_jsonld(it)
                        if r.get("prix") or r.get("surface"):
                            results.append(r)
                elif t in ("RealEstateListing", "Apartment", "House", "Product"):
                    r = self._normalize_jsonld(item)
                    if r.get("prix") or r.get("surface"):
                        results.append(r)

        return results

    def _normalize_jsonld(self, item: dict) -> dict:
        offers = item.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
        floor_size = item.get("floorSize", {})
        address = item.get("address", {})
        url = item.get("url", "")
        if url and not url.startswith("http"):
            url = BASE_URL + url

        loc = ""
        if isinstance(address, dict):
            loc = " ".join(filter(None, [
                address.get("addressLocality"),
                address.get("postalCode"),
            ])).strip()

        return {
            "source": self.SOURCE,
            "type_bien": self._normalize_type_bien(
                str(item.get("@type", "")) + " " + str(item.get("name", ""))
            ),
            "titre": str(item.get("name", "")).strip(),
            "prix": self._to_float((offers or {}).get("price")),
            "surface": self._to_float(
                floor_size.get("value") if isinstance(floor_size, dict) else floor_size
            ),
            "nb_pieces": self._to_int(item.get("numberOfRooms")),
            "localisation": loc,
            "description": str(item.get("description", "")).strip(),
            "url": url,
        }

    # ─── Normalisation annonce brute ─────────────────────────────────────────

    def _normalize_ad(self, ad: dict) -> dict:
        """Normalise une annonce brute BienIci (format JSON interne)."""

        # Prix
        prix = None
        raw_price = ad.get("price") or ad.get("prix")
        if isinstance(raw_price, (int, float)):
            prix = float(raw_price)
        elif isinstance(raw_price, list) and raw_price:
            prix = float(raw_price[0])
        else:
            prix = self._to_float(raw_price)

        # Surface
        surface = self._to_float(
            ad.get("surfaceArea") or ad.get("surface") or ad.get("livingArea")
        )

        # Pièces
        nb_pieces = self._to_int(
            ad.get("roomsQuantity") or ad.get("rooms") or ad.get("nbRooms")
        )

        # Localisation
        city = ad.get("city") or {}
        if isinstance(city, dict):
            localisation = " ".join(filter(None, [
                city.get("name") or city.get("label"),
                ad.get("postalCode") or city.get("postalCode"),
            ])).strip()
        else:
            localisation = f"{city} ({ad.get('postalCode', '')})".strip("()")

        # URL
        url = str(ad.get("url") or ad.get("link") or "")
        if url and not url.startswith("http"):
            url = BASE_URL + url
        # BienIci stocke parfois un id numérique au lieu d'une URL
        if not url and ad.get("id"):
            url = f"{BASE_URL}/annonce/{ad['id']}"

        # Type de bien
        raw_type = (
            ad.get("propertyType")
            or ad.get("estateType")
            or ad.get("nature")
            or ""
        )
        type_bien = self._normalize_type_bien(str(raw_type))

        # Titre (reconstruit si absent)
        titre = str(ad.get("title") or ad.get("name") or "").strip()
        if not titre:
            parts = [type_bien or "Bien"]
            if nb_pieces:
                parts.append(f"{nb_pieces} pieces")
            if surface:
                parts.append(f"{int(surface)}m2")
            if localisation:
                parts.append(localisation)
            titre = " - ".join(parts)

        return {
            "source": self.SOURCE,
            "type_bien": type_bien,
            "titre": titre,
            "prix": prix,
            "surface": surface,
            "nb_pieces": nb_pieces,
            "localisation": localisation,
            "description": str(ad.get("description") or "").strip(),
            "url": url,
        }

    # ─── Stratégie 3 : HTML ───────────────────────────────────────────────────

    def _parse_html(self, html: str) -> list[dict]:
        """Fallback HTML pour BienIci (sélecteurs CSS possibles)."""
        soup = BeautifulSoup(html, "lxml")
        results = []

        cards = (
            soup.select("[data-testid='adCard']")
            or soup.select("article[class*='ad-card']")
            or soup.select("[class*='realEstateAd']")
            or soup.select("article[class*='Card']")
            or soup.select("li[class*='card']")
        )

        for card in cards:
            try:
                text = card.get_text(" ", strip=True)

                prix_m = re.search(r"([\d][\d\s\u00a0\u202f]*)\s*\u20ac", text)
                prix = self._to_float(prix_m.group(1)) if prix_m else None

                surface_m = re.search(r"([\d,. ]+)\s*m\u00b2", text)
                surface = self._to_float(surface_m.group(1)) if surface_m else None

                pieces_m = re.search(r"(\d+)\s*pi\u00e8ce", text, re.I)
                nb_pieces = int(pieces_m.group(1)) if pieces_m else None

                link = card.find("a", href=True)
                url = ""
                if link:
                    href = link["href"]
                    url = href if href.startswith("http") else BASE_URL + href

                titre_el = card.find("h2") or card.find("h3")
                titre = titre_el.get_text(strip=True) if titre_el else ""

                if prix or surface:
                    results.append({
                        "source": self.SOURCE,
                        "type_bien": self._normalize_type_bien(titre),
                        "titre": titre,
                        "prix": prix,
                        "surface": surface,
                        "nb_pieces": nb_pieces,
                        "localisation": "",
                        "description": "",
                        "url": url,
                    })
            except Exception as e:
                logger.debug(f"[BIENICI] Erreur card: {e}")

        return results

    # ─── Pagination ───────────────────────────────────────────────────────────

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """BienIci : paramètre `page` dans la query string."""
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        new_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
        return urlunparse(parsed._replace(query=new_query))
