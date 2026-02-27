"""
SC DataPack Pipeline — Main Runner
====================================
Zero configuration needed. Just place Data.p4k in this folder and run:

  python runner.py

unp4k is downloaded automatically on first run if not already present.

Optional flags:
  python runner.py --skip-extract      # re-run reports only (already extracted)
  python runner.py --only ships        # run just one report
                                       # (ships / components / armor / weapons)
"""
import json
import os
import sys
import time
import urllib.request
import zipfile
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH, UNP4K_EXE, REPORTS_DIR

# Pipeline steps in order
STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py",         True),
    ("Ships",       SCRIPTS / "pipeline" / "ships_preview.py",      False),
    ("Components",  SCRIPTS / "pipeline" / "components_preview.py", False),
    ("Armor",       SCRIPTS / "pipeline" / "armor_preview.py",      False),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons_preview.py",    False),
]

UNFORGE_API = "https://api.github.com/repos/dolkensp/unp4k/releases/latest"


# ── Setup checks ─────────────────────────────────────────────────────────────

def _check_p4k():
    if not P4K_PATH.exists():
        print(f"ERROR: Data.p4k not found at {P4K_PATH}")
        print(f"Place your Star Citizen Data.p4k in the repo root folder:")
        print(f"  {ROOT}")
        sys.exit(1)
    print(f"Data.p4k : {P4K_PATH}  ({P4K_PATH.stat().st_size / 1e9:.1f} GB)")
    sys.stdout.flush()


def _ensure_unp4k():
    if UNP4K_EXE.exists():
        print(f"unp4k    : {UNP4K_EXE}  (found)")
        sys.stdout.flush()
        return

    print("unp4k    : not found — downloading latest release from GitHub...")
    sys.stdout.flush()

    try:
        req = urllib.request.Request(UNFORGE_API,
                                     headers={"User-Agent": "sc-datapack-pipeline"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            release = json.loads(resp.read())

        # Find the zip asset
        zip_asset = next(
            (a for a in release["assets"] if a["name"].endswith(".zip")),
            None
        )
        if not zip_asset:
            print("ERROR: No zip asset found in latest unp4k release.")
            sys.exit(1)

        zip_url  = zip_asset["browser_download_url"]
        zip_name = zip_asset["name"]
        zip_path = ROOT / "Tools" / zip_name

        zip_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Downloading {zip_name} ...")
        sys.stdout.flush()
        urllib.request.urlretrieve(zip_url, zip_path)

        print(f"  Extracting to Tools\\unp4k-suite\\ ...")
        sys.stdout.flush()
        dest = ROOT / "Tools" / "unp4k-suite"
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)

        zip_path.unlink()  # remove zip after extraction

        if not UNP4K_EXE.exists():
            print(f"ERROR: unp4k.exe not found after extraction at {UNP4K_EXE}")
            print(f"Check Tools\\unp4k-suite\\ contents and set SC_UNP4K_EXE in .env if needed.")
            sys.exit(1)

        print(f"  unp4k ready: {UNP4K_EXE}")
        sys.stdout.flush()

    except Exception as e:
        print(f"ERROR: Failed to download unp4k: {e}")
        print(f"Download manually from https://github.com/dolkensp/unp4k/releases")
        print(f"and place unp4k.exe at: {UNP4K_EXE}")
        sys.exit(1)


# ── Pipeline runner ───────────────────────────────────────────────────────────

def _banner(text):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")
    sys.stdout.flush()


def _run_step(name, script):
    _banner(name)
    t = time.time()
    result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
    elapsed = time.time() - t
    if result.returncode != 0:
        print(f"\nFAILED: {name} exited with code {result.returncode}")
        print(f"Fix the error above and re-run.")
        sys.exit(1)
    print(f"\nDone: {name} ({elapsed:.0f}s)")
    sys.stdout.flush()


def main():
    args = sys.argv[1:]
    skip_extract = "--skip-extract" in args
    only = None
    if "--only" in args:
        idx = args.index("--only")
        if idx + 1 < len(args):
            only = args[idx + 1].lower()

    _banner("SC DataPack Pipeline")
    _check_p4k()
    _ensure_unp4k()

    total_start = time.time()
    ran = []

    for name, script, is_extract in STEPS:
        if is_extract and skip_extract:
            print(f"\nSkipping: {name} (--skip-extract)")
            continue
        if only and is_extract:
            continue
        if only and name.lower() != only:
            continue
        _run_step(name, script)
        ran.append(name)

    total_elapsed = time.time() - total_start
    _banner(f"All done in {total_elapsed/60:.1f} min")
    print(f"  Steps    : {', '.join(ran)}")
    print(f"  Reports  : {REPORTS_DIR}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
