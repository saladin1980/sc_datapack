"""
EXPLORER runner — full DataCore dump + snapshot + changelog.

Usage:
    python explorer_runner.py                  # extract + snapshot + changelog (if 2 snapshots)
    python explorer_runner.py --extract-only   # just extract, no snapshot
    python explorer_runner.py --snapshot-only  # snapshot from existing EXPLORER_Data
    python explorer_runner.py --changelog-only # diff two latest snapshots
    python explorer_runner.py --force          # re-extract even if version matches
    python explorer_runner.py --from 4.6.0-live.11319298 --to 4.7.0-live.99999999

This is completely separate from runner.py and the main pipeline.
Outputs go to EXPLORER_Data/, snapshots/, changelogs/.
The main pipeline in SCRIPTS/ is NOT touched.
"""
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent

# ── venv bootstrap (mirrors runner.py) ───────────────────────────────────────
VENV_DIR = REPO_ROOT / "Tools" / "venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"


def _ensure_venv():
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    if not VENV_PYTHON.exists():
        print("ERROR: venv creation failed.")
        sys.exit(1)

    # Re-launch inside venv if not already there
    if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        result = subprocess.run(
            [str(VENV_PYTHON)] + sys.argv,
            cwd=str(REPO_ROOT),
        )
        sys.exit(result.returncode)

    # Inside venv — ensure dependencies
    try:
        import scdatatools  # noqa: F401
    except ImportError:
        print("Installing scdatatools and dependencies...")
        subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install",
             "git+https://gitlab.com/scmodding/frameworks/scdatatools.git",
             "--no-deps", "--ignore-requires-python"],
            check=True
        )
        subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install",
             "fnvhash", "hexdump", "humanize", "numpy", "packaging",
             "pycryptodome", "pyquaternion", "pyrsi", "rich", "tqdm",
             "xxhash", "zstandard", "line_profiler", "Pillow",
             "python-nubia", "sentry-sdk"],
            check=True
        )
        print("Dependencies installed.")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Explorer: full DataCore dump + snapshot + changelog")
    parser.add_argument("--extract-only",   action="store_true", help="only extract, skip snapshot")
    parser.add_argument("--snapshot-only",  action="store_true", help="only snapshot, skip extract")
    parser.add_argument("--changelog-only", action="store_true", help="only changelog, skip extract+snapshot")
    parser.add_argument("--force",          action="store_true", help="force re-extraction")
    parser.add_argument("--from",   dest="v_old", default=None, help="old version for changelog")
    parser.add_argument("--to",     dest="v_new", default=None, help="new version for changelog")
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "EXPLORER" / "pipeline"))
    sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))

    # Step 1: Extract
    if not args.snapshot_only and not args.changelog_only:
        import full_extractor
        full_extractor.run(force=args.force)

    # Step 2: Snapshot
    if not args.extract_only and not args.changelog_only:
        import snapshot
        snapshot.run()

    # Step 3: Changelog (only if we have 2+ snapshots)
    if not args.extract_only and not args.snapshot_only:
        import changelog
        snapshots_dir = REPO_ROOT / "snapshots"
        snap_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir() and (d / "_manifest.json").exists()] \
            if snapshots_dir.exists() else []

        if len(snap_dirs) >= 2 or args.v_old:
            changelog.run(args.v_old, args.v_new)
        else:
            print(f"Only {len(snap_dirs)} snapshot(s) found — need 2 for changelog. Run again after 4.7 update.")


if __name__ == "__main__":
    _ensure_venv()
    main()
