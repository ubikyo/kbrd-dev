from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 81

    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"
