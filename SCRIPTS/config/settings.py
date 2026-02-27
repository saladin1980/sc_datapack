"""
SC DataPack Pipeline — Settings
================================
All paths are configured via environment variables or a .env file in the
repository root. Copy .env.example to .env and fill in your paths.

No values are hardcoded here — this file works on any machine.
"""
import os
import sys
from pathlib import Path

# ── Load .env from repo root ──────────────────────────────────────────────────
def _load_env():
    repo_root = Path(__file__).parent.parent.parent  # SCRIPTS/config/ -> root
    env_file = repo_root / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)

_load_env()

# ── Required — must be set in .env or environment ────────────────────────────
def _require(key):
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: {key} is not set.")
        print("Copy .env.example to .env and fill in your paths.")
        sys.exit(1)
    return Path(val)

P4K_PATH  = _require("SC_P4K_PATH")
UNP4K_EXE = _require("SC_UNP4K_EXE")

# ── Optional — default to siblings of Data.p4k ───────────────────────────────
_base = P4K_PATH.parent

OUTPUT_DIR  = Path(os.environ.get("SC_OUTPUT_DIR",  str(_base / "Data_Extraction")))
REPORTS_DIR = Path(os.environ.get("SC_REPORTS_DIR", str(_base / "HTML")))
LOGS_DIR    = Path(os.environ.get("SC_LOGS_DIR",    str(_base / "Data_Extraction" / "logs")))
