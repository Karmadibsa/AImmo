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

        found_types: list[str] = []
        n_tags = 0

        for tag in soup.find_all("script", type="application/ld+json"):
            n_tags += 1
            try:
                data = json.loads(tag.string or "")
            except (json.JSONDecodeError, AttributeError):
                continue

            # Cas 1 : ItemList (page de résultats)
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                found_types.append("ItemList")
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
                t = item.get("@type", "")
                if t:
                    found_types.append(t)
                if t in (
                    "RealEstateListing",
                    "Apartment",
                    "House",
                    "Product",
                    # Types supplémentaires parfois utilisés par PAP
                    "Residence",
                    "LodgingBusiness",
                ):
                    listing = self._normalize_jsonld(item)
                    if listing.get("titre") or listing.get("prix"):
                        results.append(listing)

        # Diagnostic si rien n'a été extrait
        if not results:
            if n_tags == 0:
                logger.warning("[PAP] Aucun bloc JSON-LD trouvé dans la page (structure HTML changée ?)")
            elif found_types:
                logger.warning(
                    f"[PAP] JSON-LD présent mais aucune annonce extraite. "
                    f"Types @type rencontrés : {list(set(found_types))}"
                )
            else:
                logger.warning(f"[PAP] {n_tags} bloc(s) JSON-LD trouvé(s) mais sans @type reconnu")

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

        # Type de bien : @type JSON-LD ("Apartment"/"House") ou depuis le titre/URL
        raw_type = item.get("@type", "") or item.get("name", "") or url
        type_bien = self._normalize_type_bien(raw_type)

        return {
            "source": self.SOURCE,
            "type_bien": type_bien,
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
        Parsing HTML des résultats PAP (structure vérifiée en mars 2026).

        Structure actuelle de PAP :
          <div class="search-list-item-alt">
            <a class="item-title" href="/annonces/appartement-toulon-83000-rXXX">
            <span class="item-price">370.000 €</span>
            <span class="h1">Toulon (83000)</span>        ← localisation
            <p class="item-description">description...</p>
          </div>
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Sélecteur principal (vérifié sur le HTML réel)
        containers: list[Tag] = soup.select("div.search-list-item-alt")

        # Fallbacks si PAP change encore de structure
        if not containers:
            containers = (
                soup.select("article.search-item")
                or soup.select("li.search-item")
                or soup.select("[class*='search-item']")
                or soup.select("[class*='listing-item']")
                or soup.select("article[data-id]")
                or soup.select("li[data-id]")
            )

        if not containers:
            page_title = soup.find("title")
            logger.warning(
                f"[PAP] Aucun container trouvé. "
                f"Titre de la page : {page_title.get_text() if page_title else 'inconnu'}"
            )

        for container in containers:
            try:
                listing = self._extract_from_container(container)
                if listing.get("titre") or listing.get("prix"):
                    results.append(listing)
            except Exception as e:
                logger.debug(f"[PAP] Erreur extraction container: {e}")

        return results

    def _extract_from_container(self, el: Tag) -> dict:
        """
        Extrait les champs d'un container d'annonce PAP.
        Structure réelle (mars 2026) : div.search-list-item-alt
        """
        text = el.get_text(" ", strip=True)

        # ── URL + type de bien (dans le href) ─────────────────────────────────
        # PAP inclut "appartement" ou "maison" dans le slug de l'URL
        link = el.find("a", class_="item-title") or el.find("a", href=True)
        url = ""
        if link:
            href = link.get("href", "")
            url = href if href.startswith("http") else BASE_URL + href

        # ── Prix ──────────────────────────────────────────────────────────────
        prix = None
        price_el = el.find("span", class_="item-price")
        if price_el:
            prix = self._to_float(price_el.get_text())
        else:
            m = re.search(r"([\d][\d\s\u00a0\u202f\.]*)\s*€", text)
            if m:
                prix = self._to_float(m.group(1))

        # ── Localisation : span.h1 contient "Toulon (83000)" ──────────────────
        localisation = ""
        loc_el = el.find("span", class_="h1")
        if loc_el:
            localisation = loc_el.get_text(strip=True)
        else:
            # Fallback regex : "Ville (83000)"
            m = re.search(r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]*\s*\(\s*\d{5}\s*\))", text)
            if m:
                localisation = m.group(1).strip()
            else:
                m = re.search(r"\b(\d{5})\b", text)
                if m:
                    localisation = m.group(1)

        # ── Description : p.item-description ─────────────────────────────────
        desc_el = el.find("p", class_="item-description")
        if not desc_el:
            desc_el = el.find(class_=re.compile(r"desc|summary|body", re.I))
        description = desc_el.get_text(strip=True) if desc_el else ""

        # ── Surface : regex sur le texte complet ──────────────────────────────
        surface = None
        m = re.search(r"(\d+(?:[,.]\d+)?)\s*m²", text)
        if m:
            surface = self._to_float(m.group(1))

        # ── Nombre de pièces : regex ──────────────────────────────────────────
        nb_pieces = None
        m = re.search(r"(\d+)\s*pièce", text, re.I)
        if m:
            nb_pieces = int(m.group(1))
        else:
            m = re.search(r"\b(\d+)\s*[Pp]\b", text)
            if m and int(m.group(1)) <= 20:  # sanity check
                nb_pieces = int(m.group(1))

        # ── Type de bien : depuis l'URL (slug PAP) ────────────────────────────
        type_bien = self._normalize_type_bien(url)

        # ── Titre : reconstruit à partir des informations extraites ───────────
        parts = [type_bien or ""]
        if nb_pieces:
            parts.append(f"{nb_pieces} pièce{'s' if nb_pieces > 1 else ''}")
        if surface:
            parts.append(f"{int(surface)} m²")
        if localisation:
            parts.append(localisation)
        titre = " – ".join(filter(None, parts))

        return {
            "source": self.SOURCE,
            "type_bien": type_bien,
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
