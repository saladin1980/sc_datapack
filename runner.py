"""
SC DataPack Pipeline — Main Runner
====================================
Zero configuration needed. Just place Data.p4k in this folder and run:

  python runner.py

A virtual environment with all dependencies is created automatically on
first run (~1-2 min). Subsequent runs are instant.

Smart caching:
  - If version matches AND all HTML reports exist -> does nothing (instant)
  - If version matches but HTML reports are missing -> rebuilds reports only
  - If version has changed -> full extraction + reports

Optional flags:
  python runner.py --skip-extract      # re-run reports only (already extracted)
  python runner.py --force             # rebuild reports even if already up to date
  python runner.py --only ships        # run just one report
                                       # ships / components / armor / weapons / vehicles / items
"""
import sys
import time
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH, OUTPUT_DIR, REPORTS_DIR

VENV_DIR    = ROOT / "Tools" / "venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"  # Windows

# Report HTML files — shared by cache check and index generator
REPORT_FILES = [
    ("ships_preview.html",      "Ships",           "276 ships — full loadout, ports resolved, insurance times"),
    ("components_preview.html", "Components",      "1,791 equippable ship components by type"),
    ("armor_preview.html",      "Armor",           "2,208 player armor pieces — resistances, storage, signatures"),
    ("weapons_preview.html",    "Weapons",         "166 ship + 333 FPS weapons + 102 attachments"),
    ("groundvehicles.html",     "Ground Vehicles", "27 player ground vehicles — specs, dimensions, insurance"),
    ("items_preview.html",      "Items",           "501 consumables, food, melee, throwables, tools + chips"),
]

# Pipeline steps in order
STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py",         True),
    ("Ships",       SCRIPTS / "pipeline" / "ships_preview.py",      False),
    ("Components",  SCRIPTS / "pipeline" / "components_preview.py", False),
    ("Armor",       SCRIPTS / "pipeline" / "armor_preview.py",      False),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons_preview.py",    False),
    ("Vehicles",    SCRIPTS / "pipeline" / "groundvehicles_preview.py", False),
    ("Items",       SCRIPTS / "pipeline" / "items_preview.py",         False),
]


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _current_version():
    """Version string from build_manifest.id next to Data.p4k."""
    manifest = P4K_PATH.parent / "build_manifest.id"
    if manifest.exists():
        v = manifest.read_text(encoding="utf-8").strip()
        if v:
            return v
    return P4K_PATH.parent.name


def _cached_version():
    """Version string that was last extracted (from Data_Extraction/.version)."""
    vf = OUTPUT_DIR / ".version"
    return vf.read_text(encoding="utf-8").strip() if vf.exists() else None


def _all_reports_exist():
    """True only if every report HTML file is present."""
    return all((REPORTS_DIR / fn).exists() for fn, _, _ in REPORT_FILES)


# ── Venv bootstrap ────────────────────────────────────────────────────────────

def _ensure_venv():
    """Create Tools/venv with scdatatools if needed, then restart inside it."""
    if sys.prefix != sys.base_prefix:
        return  # already running inside a venv

    if not VENV_PYTHON.exists():
        print("First run: creating virtual environment in Tools/venv/ ...")
        sys.stdout.flush()
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        import venv as _venv
        _venv.create(str(VENV_DIR), with_pip=True)

        print("Installing dependencies (first run only, ~1-2 min) ...")
        sys.stdout.flush()

        # PyPI scdatatools 1.0.4 is broken on Python 3.12 (distutils removed,
        # old numpy pin). Install from GitLab HEAD with --ignore-requires-python,
        # then install all deps separately with no version pins so binary wheels
        # are used (avoids MSVC requirement for pycryptodome etc.)
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install",
             "git+https://gitlab.com/scmodding/frameworks/scdatatools.git",
             "--no-deps", "--ignore-requires-python", "--quiet"],
        )
        if result.returncode != 0:
            print("ERROR: Failed to install scdatatools from GitLab.")
            print("Check your internet connection and try again.")
            sys.exit(1)

        subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install",
             "fnvhash", "hexdump", "humanize", "numpy", "packaging",
             "pycryptodome", "pyquaternion", "pyrsi", "rich", "tqdm",
             "xxhash", "zstandard", "line_profiler", "Pillow",
             "python-nubia", "sentry-sdk",
             "--quiet"],
            check=True,
        )

        print("Setup complete.")
        sys.stdout.flush()

    # Restart this process with the venv Python
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv)
    sys.exit(result.returncode)


# ── Setup checks ─────────────────────────────────────────────────────────────

def _check_p4k():
    if not P4K_PATH.exists():
        print("ERROR: Data.p4k not found.")
        print("")
        print("To fix, copy .env.example to .env and set your path:")
        print("  SC_P4K_PATH=C:\\Program Files\\Roberts Space Industries\\StarCitizen\\LIVE\\Data.p4k")
        print("")
        print("Or place Data.p4k in the repo root folder:")
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


def _write_index():
    """Generate HTML/index.html linking to all reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    links = ""
    for filename, title, desc in REPORT_FILES:
        exists = (REPORTS_DIR / filename).exists()
        if exists:
            links += f'''
        <a href="{filename}" class="card">
            <div class="title">{title}</div>
            <div class="desc">{desc}</div>
        </a>'''
        else:
            links += f'''
        <div class="card disabled">
            <div class="title">{title}</div>
            <div class="desc">{desc} <em>(not yet generated)</em></div>
        </div>'''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SC DataPack Reports</title>
<style>
  body {{ font-family: sans-serif; background: #0f1117; color: #e0e0e0; margin: 0; padding: 40px 20px; }}
  h1 {{ color: #7eb8f7; margin-bottom: 6px; }}
  p  {{ color: #888; margin-top: 0; margin-bottom: 32px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; max-width: 900px; }}
  .card {{ display: block; background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 8px;
           padding: 20px 24px; text-decoration: none; color: inherit; transition: border-color .2s; }}
  .card:hover {{ border-color: #7eb8f7; }}
  .card.disabled {{ opacity: .4; cursor: default; }}
  .title {{ font-size: 1.2em; font-weight: 600; color: #7eb8f7; margin-bottom: 6px; }}
  .card.disabled .title {{ color: #888; }}
  .desc  {{ font-size: .9em; color: #aaa; line-height: 1.4; }}
</style>
</head>
<body>
<h1>SC DataPack Reports</h1>
<p>Star Citizen game data extracted from Data.p4k &mdash; open any report below.</p>
<div class="grid">{links}
</div>
</body>
</html>"""
    (REPORTS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"  Index    : {REPORTS_DIR / 'index.html'}")


def main():
    _ensure_venv()  # no-op if already in venv; creates + restarts if not

    args = sys.argv[1:]
    skip_extract = "--skip-extract" in args
    force        = "--force" in args
    only = None
    if "--only" in args:
        idx = args.index("--only")
        if idx + 1 < len(args):
            only = args[idx + 1].lower()

    _banner("SC DataPack Pipeline")
    _check_p4k()

    # ── Smart cache check ──────────────────────────────────────────────────────
    # Only applies to a normal full run (no --force / --only / --skip-extract)
    if not force and not only and not skip_extract:
        cur = _current_version()
        if cur and cur == _cached_version() and _all_reports_exist():
            print(f"\nAlready up to date (version {cur[:40]})")
            print(f"  All reports present in {REPORTS_DIR}")
            print("  Nothing to do. Use --force to rebuild anyway.")
            sys.stdout.flush()
            return
    # ──────────────────────────────────────────────────────────────────────────

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
    _write_index()
    _banner(f"All done in {total_elapsed/60:.1f} min")
    print(f"  Steps    : {', '.join(ran)}")
    print(f"  Reports  : {REPORTS_DIR}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
