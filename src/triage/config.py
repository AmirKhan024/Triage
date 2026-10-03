"""Configuration management for Issue Triage Agent."""

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
RESULTS_DIR = ROOT_DIR / "results"

# Thresholds & Rules parameters (Section 14)
T_HIGH: float = float(os.getenv("T_HIGH", "0.85"))
C_MIN: float = float(os.getenv("C_MIN", "0.5"))
MIN_BODY_CHARS: int = int(os.getenv("MIN_BODY_CHARS", "30"))
MAX_BODY_CHARS: int = int(os.getenv("MAX_BODY_CHARS", "6000"))
MAX_COMMENT_CHARS: int = int(os.getenv("MAX_COMMENT_CHARS", "1200"))
TOP_K: int = int(os.getenv("TOP_K", "5"))
BOOTSTRAP_SAMPLES: int = int(os.getenv("BOOTSTRAP_SAMPLES", "1000"))

# Execution & Safety
ACTION_MODE: str = os.getenv("ACTION_MODE", "log")
DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
REPO_ALLOWLIST: list[str] = [
    r.strip() for r in os.getenv("REPO_ALLOWLIST", "").split(",") if r.strip()
]

# LLM & Database
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql://triage_user:triage_pass@localhost:5432/triage_db"
)
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "triage.sqlite")
