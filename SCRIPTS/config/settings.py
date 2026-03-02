"""
SC DataPack Pipeline — Settings (Docker)
=========================================
Designed for the self-contained Docker image.

Default paths assume a single /data volume mount:
  /data/Data.p4k           -- source P4K (drop file here)
  /data/build_manifest.id  -- optional game manifest (for version string)
  /data/JSON/              -- JSON output lands here
  /work/extraction         -- intermediate DataCore XML (container-local, ephemeral)

Override any path via environment variables or a .env file next to entrypoint.py.
"""
import os
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


# ── Paths ─────────────────────────────────────────────────────────────────────
P4K_PATH    = Path(os.environ.get("SC_P4K_PATH",    "/data/Data.p4k"))
OUTPUT_DIR  = Path(os.environ.get("SC_OUTPUT_DIR",  "/work/extraction"))
REPORTS_DIR = Path(os.environ.get("SC_REPORTS_DIR", "/data"))
LOGS_DIR    = Path(os.environ.get("SC_LOGS_DIR",    "/data/logs"))


# ── Game version string ───────────────────────────────────────────────────────
def _read_game_version():
    """
    Return the game version string for display in reports and logs.

    Priority:
      1. build_manifest.id next to Data.p4k (present in a full SC install)
         Formatted as RSI Launcher displays: "4.6.0-live.11319298"
           branch "sc-alpha-4.6.0" -> "4.6.0"
           tag    "public"         -> "live"
           cl     "11319298"
      2. Raw Version field from manifest if branch/cl parsing fails
      3. Data.p4k modification date as "p4k-YYYY-MM-DD" — covers the case
         where only Data.p4k was copied to the repo root with no manifest
    """
    import json, datetime
    manifest = P4K_PATH.parent / "build_manifest.id"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8")).get("Data", {})
            branch = data.get("Branch", "")
            tag    = data.get("Tag", "")
            cl     = data.get("RequestedP4ChangeNum", "")

            for prefix in ("sc-alpha-", "sc-"):
                if branch.startswith(prefix):
                    branch = branch[len(prefix):]
                    break

            tag_label = "live" if tag == "public" else tag

            if branch and cl:
                return f"{branch}-{tag_label}.{cl}"
            v = data.get("Version", "")
            if v:
                return v
        except Exception:
            pass

    # No manifest — use Data.p4k modification date as a human-readable fallback
    try:
        mtime = P4K_PATH.stat().st_mtime
        date  = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        return f"p4k-{date}"
    except Exception:
        return "unknown"


GAME_VERSION = _read_game_version()
