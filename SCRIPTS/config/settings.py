"""
SC DataPack Pipeline — Settings
================================
All paths default to locations relative to the repo root.
Zero configuration needed if Data.p4k is placed in the repo root folder.

Override any path by setting it in a .env file at the repo root
(copy .env.example to .env). Env vars also work if set in the shell.
"""
import os
import sys
from pathlib import Path

# Repo root = three levels up from SCRIPTS/config/settings.py
REPO_ROOT = Path(__file__).parent.parent.parent


# ── Load .env from repo root (optional) ──────────────────────────────────────
def _load_env():
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

_load_env()


# ── Paths — all default to repo-relative locations ───────────────────────────
P4K_PATH    = Path(os.environ.get("SC_P4K_PATH",    str(REPO_ROOT / "Data.p4k")))
UNP4K_EXE   = Path(os.environ.get("SC_UNP4K_EXE",   str(REPO_ROOT / "Tools" / "unp4k-suite" / "unp4k.exe")))
UNFORGE_EXE = Path(os.environ.get("SC_UNFORGE_EXE", str(REPO_ROOT / "Tools" / "unp4k-suite" / "unforge.exe")))
OUTPUT_DIR  = Path(os.environ.get("SC_OUTPUT_DIR",  str(REPO_ROOT / "Data_Extraction")))
REPORTS_DIR = Path(os.environ.get("SC_REPORTS_DIR", str(REPO_ROOT / "HTML")))
LOGS_DIR    = Path(os.environ.get("SC_LOGS_DIR",    str(REPO_ROOT / "Data_Extraction" / "logs")))
