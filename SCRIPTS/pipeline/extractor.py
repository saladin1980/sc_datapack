"""
Phase 1: Extract game data from Data.p4k into Data_Extraction/.

Two data sources are used:
  1. P4K direct files (extracted with scdatatools):
       Data/Localization/*/global.ini   - display name strings (~12 files, instant)

  2. DataCore binary (parsed in-memory, dumped as XML):
       Data/Game2.dcb -> records/entities/spaceships/   - ship definitions
                      -> records/entities/scitem/        - items/components/weapons
                      -> records/scitemmanufacturer/     - manufacturer names
                      -> records/damage/                 - damage tables
                      -> records/ammoparams/             - ammo params
       (~24,667 records, ~10-15 min total)

Skips extraction if Data_Extraction/.version already matches current version.
"""
import re
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import P4K_PATH, OUTPUT_DIR, LOGS_DIR

# ── XML sanitization ──────────────────────────────────────────────────────────
# DataCore XML can contain invalid constructs that ET cannot parse:
#   1. UUID-as-attribute-names  (e.g. 6bd01ea7-...="value") — attr names must start with letter
#   2. Empty element names      (e.g. < />)                  — from null list entries
# Strip both so standard xml.etree.ElementTree can parse the output files.
_UUID_ATTR = re.compile(
    r'\s+[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}="[^"]*"',
    re.IGNORECASE,
)
_EMPTY_ELEM = re.compile(r'[ \t]*< +/>[ \t]*\n?')


def _sanitize_xml(xml_str: str) -> str:
    xml_str = _UUID_ATTR.sub("", xml_str)
    xml_str = _EMPTY_ELEM.sub("", xml_str)
    return xml_str

# DataCore record prefixes to dump (DataCore internal paths, lowercase, no "Data/" prefix)
RECORD_PREFIXES = [
    "libs/foundry/records/entities/spaceships/",
    "libs/foundry/records/entities/scitem/",
    "libs/foundry/records/scitemmanufacturer/",
    "libs/foundry/records/damage/",
    "libs/foundry/records/ammoparams/",
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

    print("scdatatools not found - installing...")
    sys.stdout.flush()

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


def _extract_localization(sc, error_log):
    """Extract global.ini files directly from P4K."""
    ini_files = [f for f in sc.p4k.filelist if "global.ini" in f.filename]
    print(f"Extracting {len(ini_files)} global.ini files...")
    sys.stdout.flush()

    errors = 0
    for info in ini_files:
        try:
            sc.p4k._extract_member(info, OUTPUT_DIR)
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {info.filename}: {e}\n")

    return len(ini_files), errors


def _dump_datacore_records(sc, error_log):
    """Parse Game2.dcb from P4K and dump needed records to disk as plain XML."""
    print("Loading DataCore (Game2.dcb) ... (~75s)")
    sys.stdout.flush()
    t = time.time()
    dc = sc.datacore
    print(f"DataCore loaded in {time.time() - t:.0f}s: {len(dc.records):,} records total")
    sys.stdout.flush()

    # Filter to only records the pipeline scripts need
    needed = [
        r for r in dc.records
        if any(r.filename.lower().startswith(p) for p in RECORD_PREFIXES)
    ]
    total = len(needed)
    print(f"Records to dump : {total:,} (~10-15 min)")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, record in enumerate(needed, 1):
        try:
            xml = _sanitize_xml(dc.dump_record_xml(record))
            # record.filename: "libs/foundry/records/entities/spaceships/aegs_gladius.xml"
            # Strip "libs/" -> "foundry/records/..."
            # Output: OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records" / ...
            rel = record.filename[len("libs/"):]
            out = OUTPUT_DIR / "Data" / "Libs" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(xml, encoding="utf-8")
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {record.filename}: {e}\n")

        if i % 2000 == 0 or i == total:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f"  {i:,}/{total:,}  ({rate:.0f}/s, ETA {eta/60:.1f}m)")
            sys.stdout.flush()

    return total, errors, time.time() - start


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
    sys.stdout.flush()

    _ensure_scdatatools()

    from scdatatools.sc import StarCitizen

    print("Opening P4K index...")
    sys.stdout.flush()
    sc = StarCitizen(P4K_PATH.parent)

    # Step 1: Localization files from P4K
    loc_total, loc_errors = _extract_localization(sc, error_log)
    print(f"Localization : {loc_total} files ({loc_errors} errors)")
    sys.stdout.flush()

    # Step 2: DataCore records -> individual XML files
    rec_total, rec_errors, rec_elapsed = _dump_datacore_records(sc, error_log)

    version_file.write_text(version)

    total_errors = loc_errors + rec_errors
    print(f"\n--- Extraction complete ---")
    print(f"  Version      : {version}")
    print(f"  Localization : {loc_total} files")
    print(f"  Records      : {rec_total:,} XML files")
    print(f"  Errors       : {total_errors}")
    print(f"  Elapsed      : {rec_elapsed / 60:.1f} min (DataCore dump)")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
