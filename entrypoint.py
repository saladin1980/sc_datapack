"""
SC DataPack Pipeline — Docker Watchdog
=======================================
Runs continuously. Watches /data/Data.p4k for changes and re-runs
the full extraction + JSON export pipeline whenever a new version is detected.

Single volume mount:
  /data/              -- drop Data.p4k (and optionally build_manifest.id) here
  /data/JSON/         -- output JSON files appear here after each run

Usage:
  docker run -v /path/to/folder:/data sc-datapack

Optional flags:
  python entrypoint.py --run-once        run once and exit (no watch loop)
  python entrypoint.py --skip-extract    skip P4K extraction on the next run
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

# File that persists the last-processed mtime across container restarts
_MTIME_FILE = P4K_PATH.parent / ".last_mtime"

# How often to poll for a changed Data.p4k (seconds)
_POLL_INTERVAL = 300  # 5 minutes


def _banner(text):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")
    sys.stdout.flush()


def _log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
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


def _run_pipeline(skip_extract=False):
    total_start = time.time()
    for name, script in STEPS:
        if name == "Extraction" and skip_extract:
            _log(f"Skipping: {name} (--skip-extract)")
            continue
        _run_step(name, script)

    json_dir = REPORTS_DIR / "JSON"
    total_elapsed = time.time() - total_start
    _banner(f"All done in {total_elapsed / 60:.1f} min")
    _log(f"JSON output : {json_dir}")


def _get_mtime():
    """Return current Data.p4k mtime as a string, or None if file missing."""
    try:
        return str(P4K_PATH.stat().st_mtime)
    except FileNotFoundError:
        return None


def _read_last_mtime():
    try:
        return _MTIME_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def _write_mtime(mtime):
    _MTIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MTIME_FILE.write_text(mtime, encoding="utf-8")


def main():
    args = sys.argv[1:]
    run_once     = "--run-once"     in args
    skip_extract = "--skip-extract" in args

    _banner("SC DataPack — Watchdog")
    _log(f"Watching : {P4K_PATH}")
    _log(f"Output   : {REPORTS_DIR / 'JSON'}")
    if run_once:
        _log("Mode     : run-once")
    else:
        _log(f"Mode     : watch (poll every {_POLL_INTERVAL}s)")

    while True:
        mtime = _get_mtime()

        if mtime is None:
            _log(f"Waiting for Data.p4k at {P4K_PATH} ...")
            time.sleep(30)
            continue

        last_mtime = _read_last_mtime()

        if mtime != last_mtime:
            _log("Data.p4k changed — starting pipeline ...")
            _run_pipeline(skip_extract=skip_extract)
            _write_mtime(mtime)
            _log("Pipeline complete. Watching for next change.")
        else:
            _log("Data.p4k unchanged — nothing to do.")

        if run_once:
            break

        time.sleep(_POLL_INTERVAL)


if __name__ == "__main__":
    main()
