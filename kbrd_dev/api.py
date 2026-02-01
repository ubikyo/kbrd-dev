from typing import Optional
import requests

from .config import Config
from .models import Person

class KbrdApi:
    """
    Client HTTP vers kbrd-api. Renvoie des modèles (Person).
    """
    def __init__(self, config: Optional[Config] = None, timeout: float = 1.0):
        self.config = config or Config()
        self.base_url = self.config.api_url.rstrip("/")
        self.timeout = timeout

    def get_last_person(self) -> Optional[Person]:
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
