from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class Person:
    first_name: str
    last_name: str = ""

    @staticmethod
    def from_api(data: Mapping[str, Any]) -> "Person":
        # Tolérant si ton API renvoie encore prenom/nom
        first = (data.get("first_name") or data.get("prenom") or "") if data else ""
        last = (data.get("last_name") or data.get("nom") or "") if data else ""
        return Person(first_name=str(first), last_name=str(last))