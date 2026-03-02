"""
SC DataPack Pipeline — Docker Entrypoint
=========================================
Runs the full extraction + JSON export pipeline inside the container.

Input:  /input/Data.p4k             (mount: -v /path/to/Data.p4k:/input/Data.p4k:ro)
        /input/build_manifest.id    (optional — provides game version string)
Output: /output/JSON/               (mount: -v /path/to/output:/output)

Optional flags:
  python entrypoint.py --skip-extract   skip P4K extraction, run report scripts only
"""
import sys
import time
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH, REPORTS_DIR

STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py"),
    ("Shops",       SCRIPTS / "pipeline" / "shops.py"),
    ("Ships",       SCRIPTS / "pipeline" / "ships.py"),
    ("Components",  SCRIPTS / "pipeline" / "components.py"),
    ("Armor",       SCRIPTS / "pipeline" / "armor.py"),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons.py"),
    ("Vehicles",    SCRIPTS / "pipeline" / "groundvehicles.py"),
    ("Items",       SCRIPTS / "pipeline" / "items.py"),
]


def _banner(text):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")
    sys.stdout.flush()


def _check_p4k():
    if not P4K_PATH.exists():
        print(f"ERROR: Data.p4k not found at {P4K_PATH}")
        print("")
        print("Mount your Data.p4k file:")
        print("  docker run -v /path/to/Data.p4k:/input/Data.p4k:ro ...")
        sys.exit(1)
    size_gb = P4K_PATH.stat().st_size / 1e9
    print(f"Data.p4k : {P4K_PATH}  ({size_gb:.1f} GB)")
    sys.stdout.flush()


def _run_step(name, script):
    _banner(name)
    t = time.time()
    result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
    elapsed = time.time() - t
    if result.returncode != 0:
        print(f"\nFAILED: {name} exited with code {result.returncode}")
        sys.exit(1)
    print(f"\nDone: {name} ({elapsed:.0f}s)")
    sys.stdout.flush()


def main():
    skip_extract = "--skip-extract" in sys.argv[1:]

    _banner("SC DataPack Pipeline")
    _check_p4k()

    total_start = time.time()

    for name, script in STEPS:
        if name == "Extraction" and skip_extract:
            print(f"\nSkipping: {name} (--skip-extract)")
            continue
        _run_step(name, script)

    json_dir = REPORTS_DIR / "JSON"
    total_elapsed = time.time() - total_start
    _banner(f"All done in {total_elapsed / 60:.1f} min")
    print(f"  JSON     : {json_dir}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
