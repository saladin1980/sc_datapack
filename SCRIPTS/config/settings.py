"""
SC DataPack Pipeline — Settings
================================
All paths default to locations relative to the repo root.
Zero configuration needed if Data.p4k is placed in the repo root folder,
OR if Star Citizen is installed at the default RSI Launcher path.

Override any path by setting it in a .env file at the repo root
(copy .env.example to .env). Env vars also work if set in the shell.
"""
import os
import sys
from pathlib import Path

# Repo root = three levels up from SCRIPTS/config/settings.py
REPO_ROOT = Path(__file__).parent.parent.parent

# Default Star Citizen install location (RSI Launcher)
_SC_DEFAULT = Path(r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k")


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
OUTPUT_DIR  = Path(os.environ.get("SC_OUTPUT_DIR",  str(REPO_ROOT / "Data_Extraction")))
REPORTS_DIR = Path(os.environ.get("SC_REPORTS_DIR", str(REPO_ROOT / "HTML")))
LOGS_DIR    = Path(os.environ.get("SC_LOGS_DIR",    str(REPO_ROOT / "Data_Extraction" / "logs")))

# Auto-detect: if configured path doesn't exist, try the default SC install
if not P4K_PATH.exists() and _SC_DEFAULT.exists():
    P4K_PATH = _SC_DEFAULT


# ── Game version string ───────────────────────────────────────────────────────
def _read_game_version():
    """
    Parse build_manifest.id next to Data.p4k and return the public version
    string shown in the RSI Launcher, e.g. "4.6.0-live.11319298".

    Format: {branch}-{tag}.{P4changelist}
      branch:  "sc-alpha-4.6.0" -> strip "sc-alpha-" -> "4.6.0"
      tag:     "public"         -> "live"
      cl:      "11319298"

    Falls back to the raw Version field ("4.6.172.47106") if parsing fails,
    or "unknown" if the manifest is missing entirely.
    """
    import json
    manifest = P4K_PATH.parent / "build_manifest.id"
    if not manifest.exists():
        return "unknown"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8")).get("Data", {})
        branch = data.get("Branch", "")          # "sc-alpha-4.6.0"
        tag    = data.get("Tag", "")             # "public"
        cl     = data.get("RequestedP4ChangeNum", "")  # "11319298"

        # Strip known prefix from branch
        for prefix in ("sc-alpha-", "sc-"):
            if branch.startswith(prefix):
                branch = branch[len(prefix):]
                break

        tag_label = "live" if tag == "public" else tag

        if branch and cl:
            return f"{branch}-{tag_label}.{cl}"
        # Fallback to raw Version field
        return data.get("Version", "unknown")
    except Exception:
        return "unknown"


GAME_VERSION = _read_game_version()
