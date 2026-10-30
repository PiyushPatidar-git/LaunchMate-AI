import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

class Settings:
    @property
    def nebius_key(self): return os.getenv("NEBIUS_API_KEY", "").strip()
    @property
    def nebius_url(self): return os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/").strip()
    @property
    def model(self): return os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b").strip()
    @property
    def tavily_key(self): return os.getenv("TAVILY_API_KEY", "").strip()
    @property
    def timeout(self): return float(os.getenv("REQUEST_TIMEOUT", "60"))
    @property
    def db_url(self): return os.getenv("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'launchmate.db').as_posix()}")

settings = Settings()
