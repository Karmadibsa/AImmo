"""
Scraper pour SeLoger.com.

SeLoger est une application React/Next.js avec une protection Cloudflare forte.
FlareSolverr est indispensable pour ce site.

Stratégies de parsing (par ordre de priorité) :
  1. __NEXT_DATA__ JSON (chemin : props.pageProps.classifieds ou variantes)
  2. JSON-LD Schema.org (RealEstateListing)
  3. HTML sémantique (fallback data-testid + regex)

Pagination : paramètre `page` dans la query string.
URL exemple :
  https://www.seloger.com/classified-search?...&page=2
"""

import json
import logging
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup

from scraping.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.seloger.com"


class SeLogerScraper(BaseScraper):
    SOURCE = "seloger"

    # ─── Point d'entrée parsing ───────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        # Stratégie 1 : __NEXT_DATA__
        results = self._parse_next_data(html)
        if results:
            logger.debug(f"[SELOGER] __NEXT_DATA__ → {len(results)} annonces")
            return results

        # Stratégie 2 : JSON-LD
        results = self._parse_jsonld(html)
        if results:
            logger.debug(f"[SELOGER] JSON-LD → {len(results)} annonces")
            return results

        # Stratégie 3 : HTML sémantique
        results = self._parse_html(html)
        if results:
            logger.debug(f"[SELOGER] HTML → {len(results)} annonces")
            return results

        logger.warning("[SELOGER] Aucune annonce parsée — vérifiez la structure HTML")
        return []

    # ─── Stratégie 1 : __NEXT_DATA__ ─────────────────────────────────────────

    def _parse_next_data(self, html: str) -> list[dict]:
        """Extrait les annonces du JSON __NEXT_DATA__ de Next.js."""
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return []

        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError as e:
            logger.debug(f"[SELOGER] Erreur JSON __NEXT_DATA__: {e}")
            return []

        page_props = data.get("props", {}).get("pageProps", {})

        # Différents chemins selon la version du site SeLoger
        ads = (
            page_props.get("classifieds")
            or page_props.get("listings")
            or page_props.get("ads")
            or (page_props.get("searchResults") or {}).get("classifieds")
            or (page_props.get("initialData") or {}).get("classifieds")
            or (page_props.get("searchData") or {}).get("listings")
            or (page_props.get("data") or {}).get("classifieds")
        )

        if not ads or not isinstance(ads, list):
            logger.debug("[SELOGER] Chemin classifieds non trouvé dans __NEXT_DATA__")
            return []

        return [self._normalize_classified(ad) for ad in ads if isinstance(ad, dict)]

    def _normalize_classified(self, ad: dict) -> dict:
        """Normalise une annonce brute SeLoger en listing standard."""

        # ── Prix ──────────────────────────────────────────────────────────────
        # SeLoger imbrique le prix dans plusieurs structures possibles
        pricing = ad.get("pricing") or ad.get("price") or {}
        if isinstance(pricing, dict):
            prix = self._to_float(pricing.get("price") or pricing.get("value"))
        else:
            prix = self._to_float(pricing)
        if prix is None:
            # Chemin alternatif
            prix = self._to_float(
                (ad.get("listingDetail") or {}).get("pricing", {}).get("price")
            )

        # ── Surface ───────────────────────────────────────────────────────────
        surface = self._to_float(
            ad.get("surface")
            or ad.get("livingArea")
            or ad.get("livingAreaValue")
            or (ad.get("listingDetail") or {}).get("surface")
        )

        # ── Pièces ────────────────────────────────────────────────────────────
        nb_pieces = self._to_int(
            ad.get("rooms")
            or ad.get("roomsQuantity")
            or ad.get("nbRooms")
            or (ad.get("listingDetail") or {}).get("rooms")
        )

        # ── Localisation ──────────────────────────────────────────────────────
        loc = ad.get("location") or ad.get("address") or {}
        if isinstance(loc, dict):
            localisation = " ".join(
                filter(
                    None,
                    [
                        loc.get("city") or loc.get("locality") or loc.get("cityName"),
                        loc.get("postalCode") or loc.get("zipCode"),
                    ],
                )
            ).strip()
        else:
            localisation = str(loc) if loc else ""

        # ── URL ───────────────────────────────────────────────────────────────
        url = str(ad.get("url") or ad.get("listingUrl") or ad.get("id") or "")
        if url and not url.startswith("http"):
            url = BASE_URL + url

        # ── Titre ─────────────────────────────────────────────────────────────
        titre = str(
            ad.get("title") or ad.get("name") or ad.get("label") or ""
        ).strip()

        # Si pas de titre, on le construit à partir du type de bien
        if not titre:
            type_bien = ad.get("propertyType") or ad.get("estateType") or ""
            pieces_str = f"{nb_pieces} pièces" if nb_pieces else ""
            surface_str = f"{int(surface)}m²" if surface else ""
            titre = " – ".join(filter(None, [type_bien, pieces_str, surface_str]))

        return {
            "source": self.SOURCE,
            "titre": titre,
            "prix": prix,
            "surface": surface,
            "nb_pieces": nb_pieces,
            "localisation": localisation,
            "description": str(ad.get("description") or ad.get("body") or "").strip(),
            "url": url,
        }

    # ─── Stratégie 2 : JSON-LD ───────────────────────────────────────────────

    def _parse_jsonld(self, html: str) -> list[dict]:
        """Cherche des données JSON-LD (Schema.org) dans la page."""
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
                if t in ("RealEstateListing", "Product", "Offer", "ApartmentComplex"):
                    offers = item.get("offers", {})
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    floor_size = item.get("floorSize") or {}
                    address = item.get("address") or {}

                    url = item.get("url", "")
                    if url and not url.startswith("http"):
                        url = BASE_URL + url

                    results.append(
                        {
                            "source": self.SOURCE,
                            "titre": str(item.get("name", "")).strip(),
                            "prix": self._to_float(
                                (offers or {}).get("price") if isinstance(offers, dict) else offers
                            ),
                            "surface": self._to_float(
                                floor_size.get("value") if isinstance(floor_size, dict) else floor_size
                            ),
                            "nb_pieces": self._to_int(item.get("numberOfRooms")),
                            "localisation": (
                                address.get("addressLocality", "")
                                if isinstance(address, dict)
                                else str(address)
                            ),
                            "description": str(item.get("description", "")).strip(),
                            "url": url,
                        }
                    )

        return results

    # ─── Stratégie 3 : HTML ───────────────────────────────────────────────────

    def _parse_html(self, html: str) -> list[dict]:
        """
        Fallback HTML pour SeLoger.
        SeLoger utilise des data-testid et des classes CSS générées (CSS Modules).
        On cherche les cartes d'annonces via plusieurs sélecteurs possibles.
        """
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Sélecteurs possibles pour les cartes d'annonces SeLoger
        cards = (
            soup.select("[data-testid*='result-item']")
            or soup.select("[data-testid*='listing']")
            or soup.select("[data-testid*='classified']")
            or soup.select("article[class*='Card']")
            or soup.select("article[class*='Classified']")
            or soup.select("[class*='listing-item']")
            or soup.select("[class*='card-classified']")
            or soup.select("[class*='annonce']")
            or soup.select("li[class*='item']")
        )

        if not cards:
            logger.debug("[SELOGER] Aucune carte d'annonce trouvée en HTML")

        for card in cards:
            try:
                text = card.get_text(" ", strip=True)

                # Prix
                prix = None
                m = re.search(
                    r"([\d][\d\s\u00a0\u202f]*)\s*€",
                    text.replace("\u202f", "").replace("\xa0", " "),
                )
                if m:
                    prix = self._to_float(m.group(1))

                # Surface
                surface = None
                m = re.search(r"([\d][,.\d]*)\s*m²", text)
                if m:
                    surface = self._to_float(m.group(1))

                # Pièces
                nb_pieces = None
                m = re.search(r"(\d+)\s*pièce", text, re.I)
                if m:
                    nb_pieces = int(m.group(1))

                # URL
                link = card.find("a", href=True)
                url = ""
                if link:
                    href = link["href"]
                    url = href if href.startswith("http") else BASE_URL + href

                # Titre
                title_el = (
                    card.find("h2")
                    or card.find("h3")
                    or card.find(class_=re.compile(r"title|titre", re.I))
                )
                titre = title_el.get_text(strip=True) if title_el else ""

                # Localisation (code postal ou ville)
                localisation = ""
                m = re.search(r"\b(\d{5})\b", text)
                if m:
                    localisation = m.group(1)

                # On ne garde que les cartes avec des données pertinentes
                if prix or surface:
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
                logger.debug(f"[SELOGER] Erreur parsing card: {e}")

        return results

    # ─── Pagination ───────────────────────────────────────────────────────────

    def _next_page(self, current_url: str, page_num: int) -> Optional[str]:
        """SeLoger : incrémente le paramètre `page` dans la query string."""
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs["page"] = [str(page_num + 1)]
        parts = []
        for k, vs in qs.items():
            for v in vs:
                parts.append(f"{k}={v}")
        return urlunparse(parsed._replace(query="&".join(parts)))
