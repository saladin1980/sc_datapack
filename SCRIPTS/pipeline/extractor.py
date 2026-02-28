"""
Phase 1: Selective extraction from Data.p4k into Data_Extraction/.

Extracts only the paths the pipeline needs (~2.4 GB, ~10-15 min):
  Data/Libs/Foundry/    - all XML item/ship/component records
  Data/Localization/    - global.ini display name strings

Uses scdatatools to open the P4K and extract by path prefix.
Uses unforge.exe to convert any CryXML binary files to plain XML after.

Skips extraction if Data_Extraction/.version already matches current version.
"""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import P4K_PATH, OUTPUT_DIR, LOGS_DIR, UNFORGE_EXE

# Only extract what the pipeline actually needs
EXTRACT_PREFIXES = [
    "Data/Libs/Foundry",
    "Data/Localization",
]


def _detect_version():
    """Read build_manifest.id if present, fall back to parent folder name."""
    manifest = P4K_PATH.parent / "build_manifest.id"
    if manifest.exists():
        version = manifest.read_text(encoding="utf-8").strip()
        if version:
            return version
    return P4K_PATH.parent.name


def _ensure_scdatatools():
    """Install scdatatools if not present."""
    try:
        import scdatatools  # noqa: F401
        return True
    except ImportError:
        pass

    print("scdatatools not found — installing...")
    sys.stdout.flush()

    # Pre-install numpy to avoid version pin conflicts
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "numpy>=1.24.3", "--quiet"],
        capture_output=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "scdatatools", "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: Failed to install scdatatools:\n{result.stderr}")
        sys.exit(1)

    print("scdatatools installed.")
    sys.stdout.flush()
    return True


def _selective_extract(version, error_log):
    """Extract only EXTRACT_PREFIXES from the P4K using scdatatools."""
    from scdatatools.sc import StarCitizen

    print("Opening P4K index (~30s)...")
    sys.stdout.flush()
    sc = StarCitizen(P4K_PATH.parent)

    # Filter file list by prefix
    to_extract = [
        info for info in sc.p4k.filelist
        if any(info.filename.startswith(p) for p in EXTRACT_PREFIXES)
    ]
    total = len(to_extract)
    print(f"Files to extract : {total:,}")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, info in enumerate(to_extract, 1):
        try:
            sc.p4k._extract_member(info, OUTPUT_DIR)
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {info.filename}: {e}\n")

        if i % 2000 == 0 or i == total:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta  = (total - i) / rate if rate > 0 else 0
            print(f"  {i:,}/{total:,}  ({rate:.0f}/s, ETA {eta/60:.1f}m)")
            sys.stdout.flush()

    elapsed = time.time() - start
    return total, errors, elapsed


def run():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    error_log = LOGS_DIR / "extraction_errors.log"

    version = _detect_version()

    version_file = OUTPUT_DIR / ".version"
    if version_file.exists() and version_file.read_text().strip() == version:
        print(f"Already extracted version {version}, skipping.")
        return

    print(f"Version  : {version}")
    print(f"P4K      : {P4K_PATH}")
    print(f"Output   : {OUTPUT_DIR}")
    print(f"Paths    : {', '.join(EXTRACT_PREFIXES)}")
    print(f"Note     : Selective extract (~10-15 min, ~2.4 GB)")
    sys.stdout.flush()

    _ensure_scdatatools()

    total, errors, elapsed = _selective_extract(version, error_log)

    # ── Convert any CryXML binary files to plain XML ──────────────────────────
    if UNFORGE_EXE.exists():
        print(f"\nConverting CryXML files...")
        sys.stdout.flush()
        forge_result = subprocess.run(
            [str(UNFORGE_EXE), str(OUTPUT_DIR)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if forge_result.returncode != 0:
            print(f"WARNING: unforge exited {forge_result.returncode}")
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"--- unforge stderr ---\n{forge_result.stderr}\n")
        else:
            print(f"CryXML conversion done.")
        sys.stdout.flush()
    else:
        print(f"WARNING: unforge.exe not found at {UNFORGE_EXE} — skipping CryXML conversion")

    version_file.write_text(version)

    print(f"\n--- Extraction complete ---")
    print(f"  Version   : {version}")
    print(f"  Extracted : {total:,} files")
    print(f"  Errors    : {errors}")
    print(f"  Elapsed   : {elapsed/60:.1f} min")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
