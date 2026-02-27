"""
SC DataPack Pipeline — Main Runner
====================================
Runs the full pipeline: extraction then all report scripts.

Usage:
  python runner.py                  # full run (extract + all reports)
  python runner.py --skip-extract   # reports only (data already extracted)
  python runner.py --only ships     # run just one report (ships/components/armor/weapons)

Requirements:
  - .env file in this folder (copy .env.example and fill in your paths)
  - unp4k.exe installed (see Tools/README.md)
  - Python 3.12+ with venv active (see DOCS/README.md)
"""
import sys
import time
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

# Pipeline steps in order
STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py",          True),
    ("Ships",       SCRIPTS / "pipeline" / "ships_preview.py",       False),
    ("Components",  SCRIPTS / "pipeline" / "components_preview.py",  False),
    ("Armor",       SCRIPTS / "pipeline" / "armor_preview.py",       False),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons_preview.py",     False),
]


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
    return elapsed


def main():
    args = sys.argv[1:]
    skip_extract = "--skip-extract" in args
    only = None
    if "--only" in args:
        idx = args.index("--only")
        if idx + 1 < len(args):
            only = args[idx + 1].lower()

    # Validate .env exists
    if not (ROOT / ".env").exists():
        print("ERROR: .env file not found.")
        print(f"Copy .env.example to .env and fill in your paths.")
        sys.exit(1)

    total_start = time.time()
    ran = []

    for name, script, is_extract in STEPS:
        if is_extract and skip_extract:
            print(f"Skipping: {name} (--skip-extract)")
            continue
        if only and name.lower() != only and not is_extract:
            continue
        if only and is_extract:
            continue  # --only skips extraction too
        _run_step(name, script)
        ran.append(name)

    total_elapsed = time.time() - total_start
    _banner(f"All done in {total_elapsed/60:.1f} min")
    print(f"  Steps run : {', '.join(ran)}")

    # Show where reports landed
    try:
        sys.path.insert(0, str(SCRIPTS))
        from config.settings import REPORTS_DIR
        print(f"  Reports   : {REPORTS_DIR}")
    except Exception:
        pass

    sys.stdout.flush()


if __name__ == "__main__":
    main()
