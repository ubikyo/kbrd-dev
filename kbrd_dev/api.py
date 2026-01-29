import os
from typing import Optional

import requests

from .models import Person


class KbrdApi:
    """
    Client HTTP vers kbrd-api. Renvoie des modèles (Person), pas des dict bruts.
    """
    def __init__(self, base_url: Optional[str] = None, timeout: float = 1.0):
        self.base_url = (base_url or os.environ.get("KBRD_API_URL", "http://127.0.0.1:81")).rstrip("/")
        self.timeout = timeout

    def get_last_person(self) -> Optional[Person]:
        """
        Endpoint attendu: GET /api/person/last
        Réponse: {"first_name":"...", "last_name":"..."} (ou prenom/nom).
        """
        url = f"{self.base_url}/api/person/last"
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json() if r.content else {}
        except Exception:
            return None

        if not data:
            return None

        p = Person.from_api(data)
        return p if p.first_name else None
