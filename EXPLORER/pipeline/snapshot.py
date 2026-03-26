"""
EXPLORER — Snapshot builder.

Reads all dumped XML records from EXPLORER_Data/ and groups them by record type
(the folder directly under records/). Outputs one JSON file per type into:

    snapshots/{version}/
        entities_spaceships.json
        entities_scitem.json
        entities_groundvehicles.json
        scitemmanufacturer.json
        damage.json
        ammoparams.json
        ... (one file per record folder)
        _manifest.json   <- total counts + timestamp

Each JSON file is a flat list of record objects:
    [
      {
        "path": "libs/foundry/records/entities/spaceships/aegs_gladius.xml",
        "attrs": { ...all XML attributes from root element... },
        "children_count": 12
      },
      ...
    ]

The snapshot is intentionally lightweight — it captures enough to detect changes
between versions without storing full XML content. The full XMLs remain on disk
in EXPLORER_Data/ for deep inspection.
"""
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.parent
RECORDS_ROOT = REPO_ROOT / "EXPLORER_Data" / "Data" / "Libs" / "foundry" / "records"
SNAPSHOTS_DIR = REPO_ROOT / "snapshots"

sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION


def _record_type(path: Path) -> str:
    """
    Convert a record path to a safe snapshot filename key.
    e.g. RECORDS_ROOT/entities/spaceships/foo.xml  ->  "entities_spaceships"
         RECORDS_ROOT/damage/bar.xml                ->  "damage"
    """
    rel = path.relative_to(RECORDS_ROOT)
    parts = rel.parts[:-1]  # drop filename
    return "_".join(parts) if parts else "root"


def _parse_record(xml_path: Path) -> dict | None:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        return {
            "path": xml_path.relative_to(REPO_ROOT / "EXPLORER_Data" / "Data" / "Libs").as_posix(),
            "tag":  root.tag,
            "attrs": dict(root.attrib),
            "children_count": len(list(root)),
        }
    except ET.ParseError:
        return None


def run(version: str | None = None):
    if not RECORDS_ROOT.exists():
        print("ERROR: EXPLORER_Data not found. Run explorer_runner.py --extract first.")
        sys.exit(1)

    version = version or GAME_VERSION
    snap_dir = SNAPSHOTS_DIR / version
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Check if snapshot already exists
    manifest_path = snap_dir / "_manifest.json"
    if manifest_path.exists():
        print(f"Snapshot already exists for {version}. Skipping.")
        return str(snap_dir)

    print(f"Building snapshot for {version}...")
    sys.stdout.flush()

    # Collect all XML files grouped by type
    buckets: dict[str, list] = {}
    all_xml = list(RECORDS_ROOT.rglob("*.xml"))
    total = len(all_xml)
    print(f"Found {total:,} XML records to snapshot...")
    sys.stdout.flush()

    start = time.time()
    errors = 0

    for i, xml_path in enumerate(all_xml, 1):
        rec_type = _record_type(xml_path)
        record = _parse_record(xml_path)
        if record:
            buckets.setdefault(rec_type, []).append(record)
        else:
            errors += 1

        if i % 10000 == 0 or i == total:
            print(f"  {i:,}/{total:,}")
            sys.stdout.flush()

    # Write one JSON per type
    type_counts = {}
    for rec_type, records in sorted(buckets.items()):
        out = snap_dir / f"{rec_type}.json"
        out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        type_counts[rec_type] = len(records)
        print(f"  {rec_type}: {len(records):,} records")
        sys.stdout.flush()

    # Manifest
    manifest = {
        "version":    version,
        "generated":  datetime.now(timezone.utc).isoformat(),
        "total":      total,
        "errors":     errors,
        "elapsed_s":  round(time.time() - start, 1),
        "types":      type_counts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nSnapshot complete: {snap_dir}")
    print(f"  {total:,} records, {errors} parse errors, {len(type_counts)} types")
    sys.stdout.flush()
    return str(snap_dir)


if __name__ == "__main__":
    run()
