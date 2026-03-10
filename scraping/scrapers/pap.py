"""
Scraper pour PAP.fr (Particulier à Particulier).

PAP est un site plus traditionnel (pas de Cloudflare fort), mais FlareSolverr
est quand même utilisé pour la cohérence et pour gérer les éventuelles
protections légères.

Stratégies de parsing (par ordre de priorité) :
  1. JSON-LD Schema.org (ItemList ou RealEstateListing)
  2. HTML sémantique avec sélecteurs CSS + regex

Pagination : paramètre `page` dans la query string.
URL exemple :
  https://www.pap.fr/annonce/vente-appartement-maison-toulon-83-g43624-jusqu-a-500000-euros?page=2
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from scraping.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pap.fr"


class PapScraper(BaseScraper):
    SOURCE = "pap"

    # ─── Point d'entrée parsing ───────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        # Stratégie 1 : JSON-LD
        results = self._parse_jsonld(html)
        if results:
            logger.debug(f"[PAP] JSON-LD → {len(results)} annonces")
            return results

        # Stratégie 2 : HTML sémantique
        results = self._parse_html(html)
        if results:
            logger.debug(f"[PAP] HTML → {len(results)} annonces")
            return results

        logger.warning("[PAP] Aucune annonce parsée — vérifiez la structure HTML")
        return []

    # ─── Stratégie 1 : JSON-LD ───────────────────────────────────────────────

    def _parse_jsonld(self, html: str) -> list[dict]:
        """
        Cherche des blocs JSON-LD (Schema.org).
        PAP peut exposer ses annonces sous forme d'ItemList ou de
        RealEstateListing directement dans la page.
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, AttributeError):
                continue

            # Cas 1 : ItemList (page de résultats)
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for elem in data.get("itemListElement", []):
                    item = elem.get("item", elem)
                    listing = self._normalize_jsonld(item)
                    if listing.get("titre") or listing.get("prix"):
                        results.append(listing)
                if results:
                    return results

            # Cas 2 : Liste directe d'annonces
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in (
                    "RealEstateListing",
                    "Apartment",
                    "House",
                    "Product",
                ):
                    listing = self._normalize_jsonld(item)
                    if listing.get("titre") or listing.get("prix"):
                        results.append(listing)

        return results

    def _normalize_jsonld(self, item: dict) -> dict:
        """Normalise un objet JSON-LD en listing standard."""
        # Prix
        offers = item.get("offers", {})
        if isinstance(offers, list) and offers:
            offers = offers[0]
        prix = self._to_float((offers or {}).get("price")) if offers else None

        # Surface
        floor_size = item.get("floorSize", {})
        if isinstance(floor_size, dict):
            surface = self._to_float(floor_size.get("value"))
        else:
            surface = self._to_float(floor_size)

        # Localisation
        address = item.get("address", {})
        if isinstance(address, dict):
            localisation = " ".join(
                filter(
                    None,
                    [
                        address.get("addressLocality"),
                        address.get("postalCode"),
                    ],
                )
            ).strip()
        else:
            localisation = str(address) if address else ""

        # URL
        url = item.get("url", "") or item.get("@id", "")
        if url and not url.startswith("http"):
            url = BASE_URL + url

        return {
            "source": self.SOURCE,
            "titre": str(item.get("name", "")).strip(),
            "prix": prix,
            "surface": surface,
            "nb_pieces": self._to_int(item.get("numberOfRooms")),
            "localisation": localisation,
            "description": str(item.get("description", "")).strip(),
            "url": url,
        }

    # ─── Stratégie 2 : HTML ───────────────────────────────────────────────────

    def _parse_html(self, html: str) -> list[dict]:
        """
        Parsing HTML des résultats PAP.
        PAP utilise une structure sémantique :
          <article class="search-item"> ou <li class="search-item">
          avec h2 pour le titre, .price / .prix pour le prix, etc.
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Différents sélecteurs selon la version du template PAP
        containers: list[Tag] = (
            soup.select("article.search-item")
            or soup.select("li.search-item")
            or soup.select("[class*='search-item']")
            or soup.select("[class*='listing-item']")
            or soup.select("[class*='result-item']")
            or soup.select("article[data-id]")
            or soup.select("li[data-id]")
        )

        if not containers:
            logger.debug("[PAP] Aucun container trouvé dans le HTML")

        for container in containers:
            try:
                listing = self._extract_from_container(container)
                # On ne garde que les annonces avec au moins un champ utile
                if listing.get("titre") or listing.get("prix"):
                    results.append(listing)
            except Exception as e:
                logger.debug(f"[PAP] Erreur extraction container: {e}")

        return results

    def _extract_from_container(self, el: Tag) -> dict:
        """Extrait les champs d'un container d'annonce PAP."""
        # ── Lien + URL ────────────────────────────────────────────────────────
        link = el.find("a", href=True)
        url = ""
        if link:
            href = link["href"]
            url = href if href.startswith("http") else BASE_URL + href

        # ── Titre ─────────────────────────────────────────────────────────────
        title_el = (
            el.find("h2")
            or el.find("h3")
            or el.find(class_=re.compile(r"title|titre", re.I))
        )
        titre = title_el.get_text(strip=True) if title_el else ""

        # ── Texte complet (pour regex) ────────────────────────────────────────
        text = el.get_text(" ", strip=True)

        # ── Prix ──────────────────────────────────────────────────────────────
        prix = None
        price_el = el.find(class_=re.compile(r"price|prix", re.I))
        if price_el:
            prix = self._to_float(price_el.get_text())
        else:
            # Pattern : "150 000 €" ou "150000€"
            m = re.search(r"([\d][\d\s\u00a0\u202f]*)\s*€", text)
            if m:
                prix = self._to_float(m.group(1))

        # ── Surface ───────────────────────────────────────────────────────────
        surface = None
        surface_el = el.find(class_=re.compile(r"surface", re.I))
        if surface_el:
            surface = self._to_float(surface_el.get_text())
        else:
            m = re.search(r"([\d][,.\d]*)\s*m²", text)
            if m:
                surface = self._to_float(m.group(1))

        # ── Nombre de pièces ──────────────────────────────────────────────────
        nb_pieces = None
        m = re.search(r"(\d+)\s*pièce", text, re.I)
        if m:
            nb_pieces = int(m.group(1))
        else:
            # Cherche aussi "3P", "4P" (abréviations courantes)
            m = re.search(r"\b(\d+)\s*[Pp]\b", text)
            if m:
                nb_pieces = int(m.group(1))

        # ── Localisation ──────────────────────────────────────────────────────
        loc_el = el.find(class_=re.compile(r"location|localisation|city|ville|town", re.I))
        localisation = loc_el.get_text(strip=True) if loc_el else ""
        if not localisation:
            # Regex code postal français (5 chiffres)
            m = re.search(r"\b(\d{5})\b", text)
            if m:
                localisation = m.group(1)

        # ── Description ───────────────────────────────────────────────────────
        desc_el = el.find(class_=re.compile(r"desc|summary|body|text|content", re.I))
        description = desc_el.get_text(strip=True) if desc_el else ""

        return {
            "source": self.SOURCE,
            "titre": titre,
            "prix": prix,
            "surface": surface,
            "nb_pieces": nb_pieces,
            "localisation": localisation,
            "description": description,
            "url": url,
        }

    # ─── Pagination ───────────────────────────────────────────────────────────

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """
        PAP : ajoute ou incrémente le paramètre `page` dans l'URL.
        Ex: .../jusqu-a-500000-euros → .../jusqu-a-500000-euros?page=2
        """
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        new_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
        return urlunparse(parsed._replace(query=new_query))
