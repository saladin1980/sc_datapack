"""
SC DataPack Pipeline — Main Runner
====================================
Zero configuration needed. Just place Data.p4k in this folder and run:

  python runner.py

scdatatools is installed automatically on first run.

Optional flags:
  python runner.py --skip-extract      # re-run reports only (already extracted)
  python runner.py --only ships        # run just one report
                                       # (ships / components / armor / weapons)
"""
import os
import sys
import time
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH, REPORTS_DIR

# Pipeline steps in order
STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py",         True),
    ("Ships",       SCRIPTS / "pipeline" / "ships_preview.py",      False),
    ("Components",  SCRIPTS / "pipeline" / "components_preview.py", False),
    ("Armor",       SCRIPTS / "pipeline" / "armor_preview.py",      False),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons_preview.py",    False),
]


# ── Setup checks ─────────────────────────────────────────────────────────────

def _check_p4k():
    if not P4K_PATH.exists():
        print(f"ERROR: Data.p4k not found at {P4K_PATH}")
        print(f"Place your Star Citizen Data.p4k in the repo root folder:")
        print(f"  {ROOT}")
        sys.exit(1)
    print(f"Data.p4k : {P4K_PATH}  ({P4K_PATH.stat().st_size / 1e9:.1f} GB)")
    sys.stdout.flush()


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
