"""
Client HTTP pour FlareSolverr.

FlareSolverr est un proxy qui lance un navigateur headless (Chrome) pour
bypasser les protections Cloudflare et DDoS-Guard, puis retourne le HTML
rendu côté client.

Docs : https://github.com/FlareSolverr/FlareSolverr
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# URL par défaut (variable d'env possible pour docker-compose)
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")


class FlareSolverrClient:
    """
    Client pour l'API REST de FlareSolverr.

    Gère une session (cookies partagés entre les requêtes) pour améliorer
    le taux de succès contre les protections anti-bot.

    Usage typique :
        with FlareSolverrClient() as client:
            html = client.get("https://www.leboncoin.fr/...")
    """

    def __init__(self, host: str = FLARESOLVERR_URL, max_timeout: int = 60_000):
        """
        Args:
            host        : URL de FlareSolverr (ex. http://localhost:8191)
            max_timeout : Timeout max en millisecondes pour chaque requête
        """
        self.host = host.rstrip("/")
        self.max_timeout = max_timeout
        self.session_id: Optional[str] = None

    # ─── Requête interne ──────────────────────────────────────────────────────

    def _post(self, payload: dict) -> dict:
        """Envoie une commande à l'API FlareSolverr."""
        try:
            resp = requests.post(
                f"{self.host}/v1",
                json=payload,
                timeout=(self.max_timeout / 1000) + 15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Impossible de joindre FlareSolverr sur {self.host}.\n"
                "  → Lancez-le avec : docker-compose up flaresolverr -d"
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"FlareSolverr n'a pas répondu dans le délai imparti ({self.max_timeout}ms)."
            )

    # ─── Gestion de session ───────────────────────────────────────────────────

    def create_session(self) -> str:
        """
        Crée une session FlareSolverr.
        Les cookies sont partagés entre toutes les requêtes de la session.
        """
        data = self._post({"cmd": "sessions.create"})
        if data.get("status") != "ok":
            raise RuntimeError(f"Erreur création session FlareSolverr: {data}")
        self.session_id = data["session"]
        logger.info(f"[FlareSolverr] Session créée : {self.session_id}")
        return self.session_id

    def destroy_session(self):
        """Détruit la session courante et libère les ressources."""
        if self.session_id:
            try:
                self._post({"cmd": "sessions.destroy", "session": self.session_id})
                logger.info(f"[FlareSolverr] Session détruite : {self.session_id}")
            except Exception:
                pass  # Ignorer les erreurs à la fermeture
            finally:
                self.session_id = None

    # ─── Requête HTTP ─────────────────────────────────────────────────────────

    def get(self, url: str) -> str:
        """
        Récupère le HTML rendu d'une URL via FlareSolverr.

        FlareSolverr lance Chrome, résout les challenges Cloudflare, puis
        retourne le HTML complet après exécution du JavaScript.

        Args:
            url : URL à scraper

        Returns:
            HTML complet de la page après rendu

        Raises:
            RuntimeError : Si FlareSolverr retourne une erreur
        """
        payload: dict = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": self.max_timeout,
        }
        if self.session_id:
            payload["session"] = self.session_id

        logger.info(f"[FlareSolverr] GET → {url}")
        data = self._post(payload)

        if data.get("status") != "ok":
            raise RuntimeError(
                f"[FlareSolverr] Erreur [{data.get('status')}] : {data.get('message', data)}"
            )

        html: str = data["solution"]["response"]
        logger.debug(f"[FlareSolverr] Réponse reçue ({len(html):,} chars)")
        return html

    # ─── Context manager ──────────────────────────────────────────────────────

    def __enter__(self) -> "FlareSolverrClient":
        self.create_session()
        return self

    def __exit__(self, *_):
        self.destroy_session()
