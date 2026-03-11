"""
Scraper pour Figaro Immobilier (immobilier.lefigaro.fr).

Portail immobilier du groupe Figaro — agrège des annonces d'agences
et de réseaux mandataires. Généralement moins protégé que SeLoger.

Stratégies de parsing :
  1. JSON-LD Schema.org (ItemList / RealEstateListing)
  2. HTML sémantique (sélecteurs CSS)

Pagination : paramètre `page` dans la query string.
URL de recherche :
  https://immobilier.lefigaro.fr/annonces/immobilier-vente/toulon-83000.html
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup

from scraping.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://immobilier.lefigaro.fr"


class FigaroScraper(BaseScraper):
    SOURCE = "figaro"

    # ─── Point d'entrée parsing ───────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        # Stratégie 1 : JSON-LD
        results = self._parse_jsonld(html)
        if results:
            logger.debug(f"[FIGARO] JSON-LD -> {len(results)} annonces")
            return results

        # Stratégie 2 : HTML sémantique
        results = self._parse_html(html)
        if results:
            logger.debug(f"[FIGARO] HTML -> {len(results)} annonces")
            return results

        soup = BeautifulSoup(html, "lxml")
        title = soup.find("title")
        logger.warning(
            f"[FIGARO] Aucune annonce parsee "
            f"(HTML: {len(html):,} chars, titre: {title.get_text() if title else 'aucun'}). "
            "Verifiez si le site a change de structure ou si FlareSolverr est bloque."
        )
        return []

    # ─── Stratégie 1 : JSON-LD ───────────────────────────────────────────────

    def _parse_jsonld(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, AttributeError):
                continue

            # ItemList de la page de résultats
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for elem in data.get("itemListElement", []):
                    item = elem.get("item", elem)
                    r = self._normalize_jsonld(item)
                    if r.get("prix") or r.get("surface"):
                        results.append(r)
                if results:
                    return results

            # Annonces individuelles
            items = data if isinstance(data, list) else [data]
            for item in items:
                t = item.get("@type", "")
                if t in ("RealEstateListing", "Apartment", "House", "Product", "Offer"):
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

        raw_type = str(item.get("@type", ""))
        titre = str(item.get("name", "")).strip()

        return {
            "source": self.SOURCE,
            "type_bien": self._normalize_type_bien(raw_type + " " + titre),
            "titre": titre,
            "prix": self._to_float((offers or {}).get("price")),
            "surface": self._to_float(
                floor_size.get("value") if isinstance(floor_size, dict) else floor_size
            ),
            "nb_pieces": self._to_int(item.get("numberOfRooms")),
            "localisation": loc,
            "description": str(item.get("description", "")).strip(),
            "url": url,
        }

    # ─── Stratégie 2 : HTML ───────────────────────────────────────────────────

    def _parse_html(self, html: str) -> list[dict]:
        """
        Parsing HTML de Figaro Immobilier.
        Sélecteurs vérifiés sur la structure connue du site.
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Sélecteurs possibles pour les cartes d'annonces
        cards = (
            soup.select("article.property-card")
            or soup.select("[class*='property-card']")
            or soup.select("[class*='listing-item']")
            or soup.select("[class*='annonce']")
            or soup.select("li[class*='item']")
            or soup.select("[data-id]")
        )

        if not cards:
            logger.debug("[FIGARO] Aucune carte d'annonce trouvee en HTML")

        for card in cards:
            try:
                text = card.get_text(" ", strip=True)

                # Prix
                prix_m = re.search(
                    r"([\d][\d\s\u00a0\u202f]*)\s*\u20ac",
                    text.replace("\u202f", " ").replace("\u00a0", " ")
                )
                prix = self._to_float(prix_m.group(1)) if prix_m else None

                # Surface
                surface_m = re.search(r"([\d,. ]+)\s*m\u00b2", text)
                surface = self._to_float(surface_m.group(1)) if surface_m else None

                # Pièces
                pieces_m = re.search(r"(\d+)\s*pi\u00e8ce", text, re.I)
                nb_pieces = int(pieces_m.group(1)) if pieces_m else None

                # URL
                link = card.find("a", href=True)
                url = ""
                if link:
                    href = link["href"]
                    url = href if href.startswith("http") else BASE_URL + href

                # Titre
                titre_el = (
                    card.find("h2")
                    or card.find("h3")
                    or card.find(class_=re.compile(r"title|titre", re.I))
                )
                titre = titre_el.get_text(strip=True) if titre_el else ""

                # Localisation (code postal dans le texte)
                loc_m = re.search(r"\b(\d{5})\b", text)
                localisation = loc_m.group(1) if loc_m else ""

                if prix or surface:
                    results.append({
                        "source": self.SOURCE,
                        "type_bien": self._normalize_type_bien(titre),
                        "titre": titre,
                        "prix": prix,
                        "surface": surface,
                        "nb_pieces": nb_pieces,
                        "localisation": localisation,
                        "description": "",
                        "url": url,
                    })
            except Exception as e:
                logger.debug(f"[FIGARO] Erreur card: {e}")

        return results

    # ─── Pagination ───────────────────────────────────────────────────────────

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """Figaro Immobilier : paramètre `page` dans la query string."""
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        new_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
        return urlunparse(parsed._replace(query=new_query))
