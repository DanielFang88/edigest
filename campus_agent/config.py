from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ed_api_token: str
    openrouter_api_key: str
    openrouter_model: str
    database_path: Path


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            # Existing shell variables win, which is useful for cron/systemd.
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return Settings(
        ed_api_token=os.getenv("ED_API_TOKEN", "").strip(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini").strip(),
        database_path=root / "data" / "campus_agent.sqlite3",
    )
