"""
EXPLORER — Full DataCore extractor.

Dumps ALL DataCore records (no prefix filter) to disk as sanitized XML.
Also extracts localization and shop inventory files from P4K (same as main pipeline).

Output: EXPLORER_OUTPUT_DIR / Data / Libs / foundry / records / ...
        EXPLORER_OUTPUT_DIR / Data / Localization / ... / global.ini
        EXPLORER_OUTPUT_DIR / Data / Scripts / ShopInventories / *.json

Does NOT write to the main pipeline's Data_Extraction/ folder — completely separate.
"""
import re
import sys
import time
from pathlib import Path

# Repo root is 3 levels up: EXPLORER/pipeline/full_extractor.py
REPO_ROOT = Path(__file__).parent.parent.parent

# Re-use shared settings for P4K_PATH and GAME_VERSION only.
# Output dir is overridden here so we never touch main pipeline output.
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import P4K_PATH, GAME_VERSION

# Explorer output: repo_root/EXPLORER_Data/
EXPLORER_OUTPUT_DIR = REPO_ROOT / "EXPLORER_Data"
EXPLORER_LOGS_DIR   = EXPLORER_OUTPUT_DIR / "logs"

# ── XML sanitization (identical to main extractor) ───────────────────────────
_INVALID_ATTR = re.compile(r'\s+(?:[0-9][^\s=]*)?\s*=\s*"[^"]*"')
_EMPTY_ELEM   = re.compile(r"[ \t]*< +/>[ \t]*\n?")
_EMPTY_TAG    = re.compile(r"[ \t]*<>[^<]*</>[ \t]*\n?")


def _sanitize_xml(xml_str: str) -> str:
    xml_str = _INVALID_ATTR.sub("", xml_str)
    xml_str = _EMPTY_ELEM.sub("", xml_str)
    xml_str = _EMPTY_TAG.sub("", xml_str)
    return xml_str


def _detect_version():
    manifest = P4K_PATH.parent / "build_manifest.id"
    if manifest.exists():
        version = manifest.read_text(encoding="utf-8").strip()
        if version:
            return version
    try:
        stat = P4K_PATH.stat()
        return f"p4k-{stat.st_size}-{int(stat.st_mtime)}"
    except Exception:
        return P4K_PATH.parent.name


def _extract_localization(sc, error_log):
    ini_files = [f for f in sc.p4k.filelist if "global.ini" in f.filename]
    print(f"Extracting {len(ini_files)} global.ini files...")
    sys.stdout.flush()
    errors = 0
    for info in ini_files:
        try:
            sc.p4k._extract_member(info, EXPLORER_OUTPUT_DIR)
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {info.filename}: {e}\n")
    return len(ini_files), errors


def _extract_shop_inventories(sc, error_log):
    shop_files = [
        f for f in sc.p4k.filelist
        if "Scripts/ShopInventories" in f.filename
        and not f.filename.endswith("/")
    ]
    print(f"Extracting {len(shop_files)} ShopInventory files...")
    sys.stdout.flush()
    errors = 0
    for info in shop_files:
        try:
            sc.p4k._extract_member(info, EXPLORER_OUTPUT_DIR)
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {info.filename}: {e}\n")
    return len(shop_files), errors


def _dump_all_datacore_records(sc, error_log):
    """Dump ALL DataCore records — no prefix filter."""
    print("Loading DataCore (Game2.dcb) ... (~75s)")
    sys.stdout.flush()
    t = time.time()
    dc = sc.datacore
    total_records = len(dc.records)
    print(f"DataCore loaded in {time.time() - t:.0f}s: {total_records:,} records total")
    sys.stdout.flush()

    print(f"Dumping all {total_records:,} records (~30-60 min)...")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, record in enumerate(dc.records, 1):
        try:
            xml = _sanitize_xml(dc.dump_record_xml(record))
            # record.filename: "libs/foundry/records/entities/spaceships/aegs_gladius.xml"
            rel = record.filename[len("libs/"):] if record.filename.lower().startswith("libs/") else record.filename
            out = EXPLORER_OUTPUT_DIR / "Data" / "Libs" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(xml, encoding="utf-8")
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR: {record.filename}: {e}\n")

        if i % 5000 == 0 or i == total_records:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total_records - i) / rate if rate > 0 else 0
            print(f"  {i:,}/{total_records:,}  ({rate:.0f}/s, ETA {eta/60:.1f}m)")
            sys.stdout.flush()

    return total_records, errors, time.time() - start


def run(force=False):
    EXPLORER_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    EXPLORER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    error_log = EXPLORER_LOGS_DIR / "extraction_errors.log"
    version = _detect_version()

    version_file = EXPLORER_OUTPUT_DIR / ".version"
    if not force and version_file.exists() and version_file.read_text().strip() == version:
        print(f"Already extracted version {GAME_VERSION}, skipping. Use --force to re-extract.")
        return

    print(f"Version  : {GAME_VERSION}")
    print(f"P4K      : {P4K_PATH}")
    print(f"Output   : {EXPLORER_OUTPUT_DIR}")
    sys.stdout.flush()

    try:
        import scdatatools  # noqa: F401
    except ImportError:
        print("ERROR: scdatatools not found. Run explorer_runner.py to set up the environment.")
        sys.exit(1)

    from scdatatools.sc import StarCitizen

    print("Opening P4K index...")
    sys.stdout.flush()
    sc = StarCitizen(P4K_PATH.parent)

    loc_total, loc_errors = _extract_localization(sc, error_log)
    print(f"Localization    : {loc_total} files ({loc_errors} errors)")
    sys.stdout.flush()

    shop_total, shop_errors = _extract_shop_inventories(sc, error_log)
    print(f"ShopInventories : {shop_total} files ({shop_errors} errors)")
    sys.stdout.flush()

    rec_total, rec_errors, rec_elapsed = _dump_all_datacore_records(sc, error_log)

    version_file.write_text(version)

    total_errors = loc_errors + shop_errors + rec_errors
    print(f"\n--- Extraction complete ---")
    print(f"  Version         : {GAME_VERSION}")
    print(f"  Localization    : {loc_total} files")
    print(f"  ShopInventories : {shop_total} files")
    print(f"  Records         : {rec_total:,} XML files")
    print(f"  Errors          : {total_errors}")
    print(f"  Elapsed         : {rec_elapsed / 60:.1f} min (DataCore dump)")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
