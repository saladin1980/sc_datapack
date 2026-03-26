"""
EXPLORER — Full extractor.

Extracts EVERYTHING:
  1. All P4K files (~1.28M files, ~150GB) -> EXPLORER_OUTPUT_DIR/
  2. All DataCore records (~108K XML) -> EXPLORER_OUTPUT_DIR/Data/Libs/foundry/records/

Does NOT write to the main pipeline's Data_Extraction/ folder — completely separate.
Output: EXPLORER_OUTPUT_DIR/ (repo_root/EXPLORER_Data/)
"""
import re
import sys
import time
from pathlib import Path

# Repo root is 3 levels up: EXPLORER/pipeline/full_extractor.py
REPO_ROOT = Path(__file__).parent.parent.parent

sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import P4K_PATH, GAME_VERSION

EXPLORER_OUTPUT_DIR = REPO_ROOT / "EXPLORER_Data"
EXPLORER_LOGS_DIR   = EXPLORER_OUTPUT_DIR / "logs"

# ── XML sanitization ──────────────────────────────────────────────────────────
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


def _extract_all_p4k(sc, error_log):
    """Extract every file in the P4K archive (~1.28M files, ~150GB)."""
    all_files = [f for f in sc.p4k.filelist if not f.filename.endswith("/")]
    total = len(all_files)
    print(f"Extracting all {total:,} P4K files (~150GB, this will take a while)...")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, info in enumerate(all_files, 1):
        try:
            sc.p4k._extract_member(info, EXPLORER_OUTPUT_DIR)
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR P4K: {info.filename}: {e}\n")

        if i % 10000 == 0 or i == total:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total - i) / rate if rate > 0 else 0
            print(f"  P4K {i:,}/{total:,}  ({rate:.0f}/s, ETA {eta/60:.1f}m)")
            sys.stdout.flush()

    return total, errors, time.time() - start


def _dump_all_datacore_records(sc, error_log):
    """Dump ALL DataCore records — no prefix filter."""
    print("Loading DataCore (Game2.dcb) ... (~75s)")
    sys.stdout.flush()
    t = time.time()
    dc = sc.datacore
    total_records = len(dc.records)
    print(f"DataCore loaded in {time.time() - t:.0f}s: {total_records:,} records total")
    print(f"Dumping all {total_records:,} records...")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, record in enumerate(dc.records, 1):
        try:
            xml = _sanitize_xml(dc.dump_record_xml(record))
            rel = record.filename[len("libs/"):] if record.filename.lower().startswith("libs/") else record.filename
            out = EXPLORER_OUTPUT_DIR / "Data" / "Libs" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(xml, encoding="utf-8")
        except Exception as e:
            errors += 1
            with open(str(error_log), "a", encoding="utf-8") as f:
                f.write(f"ERROR DC: {record.filename}: {e}\n")

        if i % 5000 == 0 or i == total_records:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (total_records - i) / rate if rate > 0 else 0
            print(f"  DC  {i:,}/{total_records:,}  ({rate:.0f}/s, ETA {eta/60:.1f}m)")
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
    print(f"NOTE     : Full extraction ~150GB + DataCore XML. Ensure you have 200GB+ free.")
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

    # Step 1: All P4K files
    p4k_total, p4k_errors, p4k_elapsed = _extract_all_p4k(sc, error_log)
    print(f"P4K extraction  : {p4k_total:,} files ({p4k_errors} errors, {p4k_elapsed/60:.1f}m)")
    sys.stdout.flush()

    # Step 2: DataCore records (XML on top of the extracted P4K)
    rec_total, rec_errors, rec_elapsed = _dump_all_datacore_records(sc, error_log)

    version_file.write_text(version)

    total_errors = p4k_errors + rec_errors
    print(f"\n--- Extraction complete ---")
    print(f"  Version    : {GAME_VERSION}")
    print(f"  P4K files  : {p4k_total:,} ({p4k_elapsed/60:.1f}m)")
    print(f"  DC records : {rec_total:,} ({rec_elapsed/60:.1f}m)")
    print(f"  Errors     : {total_errors}")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
