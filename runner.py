"""
SC DataPack Pipeline — Main Runner
====================================
Zero configuration needed. Just place Data.p4k in this folder and run:

  python runner.py

A virtual environment with all dependencies is created automatically on
first run (~1-2 min). Subsequent runs are instant.

Optional flags:
  python runner.py --skip-extract      # re-run reports only (already extracted)
  python runner.py --only ships        # run just one report
                                       # (ships / components / armor / weapons / vehicles)
"""
import sys
import time
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"

sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH, REPORTS_DIR

VENV_DIR    = ROOT / "Tools" / "venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"  # Windows

# Pipeline steps in order
STEPS = [
    ("Extraction",  SCRIPTS / "pipeline" / "extractor.py",         True),
    ("Ships",       SCRIPTS / "pipeline" / "ships_preview.py",      False),
    ("Components",  SCRIPTS / "pipeline" / "components_preview.py", False),
    ("Armor",       SCRIPTS / "pipeline" / "armor_preview.py",      False),
    ("Weapons",     SCRIPTS / "pipeline" / "weapons_preview.py",    False),
    ("Vehicles",    SCRIPTS / "pipeline" / "groundvehicles_preview.py", False),
]


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
    reports = [
        ("ships_preview.html",      "Ships",      "276 ships — full loadout, every port resolved with stats"),
        ("components_preview.html", "Components", "2,500+ equippable ship components by type"),
        ("armor_preview.html",      "Armor",      "2,200+ player armor pieces — resistances, storage, signatures"),
        ("weapons_preview.html",    "Weapons",    "600+ ship weapons, FPS weapons, and attachments"),
    ]
    links = ""
    for filename, title, desc in reports:
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
    _write_index()
    _banner(f"All done in {total_elapsed/60:.1f} min")
    print(f"  Steps    : {', '.join(ran)}")
    print(f"  Reports  : {REPORTS_DIR}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
