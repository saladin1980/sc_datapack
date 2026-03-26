"""
EXPLORER — Changelog generator.

Compares two version snapshots and produces a diff JSON:

    changelogs/{v_old}-to-{v_new}.json

Structure:
    {
      "from_version": "4.6.0-live.11319298",
      "to_version":   "4.7.0-live.12345678",
      "generated":    "2026-04-01T12:00:00+00:00",
      "summary": {
        "added":   150,
        "removed": 12,
        "changed": 87
      },
      "changes": {
        "entities_spaceships": {
          "added":   [...],   each entry: {"path": ..., "attrs": ..., "children_count": ...}
          "removed": [...],
          "changed": [        each entry: {"path": ..., "before": {attrs}, "after": {attrs}, "attr_diff": {key: [old, new]}}
        },
        ...
      }
    }

Records are matched by their "path" field (DataCore filename).
"changed" means the root element attributes or children_count differ.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT      = Path(__file__).parent.parent.parent
SNAPSHOTS_DIR  = REPO_ROOT / "snapshots"
CHANGELOGS_DIR = REPO_ROOT / "changelogs"


def _load_snapshot(snap_dir: Path) -> dict[str, dict]:
    """
    Load all type JSON files from a snapshot directory.
    Returns: { record_path -> record_dict }
    """
    records = {}
    for json_file in snap_dir.glob("*.json"):
        if json_file.name == "_manifest.json":
            continue
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for rec in data:
            records[rec["path"]] = rec
    return records


def _diff_records(old: dict, new: dict, rec_type_filter: str | None = None) -> dict:
    """
    Compare two flat record dicts keyed by path.
    Returns change buckets grouped by record type.
    """
    old_paths = set(old.keys())
    new_paths = set(new.keys())

    added_paths   = new_paths - old_paths
    removed_paths = old_paths - new_paths
    shared_paths  = old_paths & new_paths

    # Group by type (first 1-2 path components after "foundry/records/")
    def _type(path: str) -> str:
        parts = path.split("/")
        # path: "foundry/records/entities/spaceships/foo.xml"
        try:
            idx = parts.index("records")
            type_parts = parts[idx+1:-1]  # drop "records" prefix and filename
            return "_".join(type_parts) if type_parts else "root"
        except ValueError:
            return "unknown"

    changes: dict[str, dict] = {}

    def _bucket(rec_type: str) -> dict:
        if rec_type not in changes:
            changes[rec_type] = {"added": [], "removed": [], "changed": []}
        return changes[rec_type]

    for path in sorted(added_paths):
        _bucket(_type(path))["added"].append(new[path])

    for path in sorted(removed_paths):
        _bucket(_type(path))["removed"].append(old[path])

    for path in sorted(shared_paths):
        old_rec = old[path]
        new_rec = new[path]
        old_attrs = old_rec.get("attrs", {})
        new_attrs = new_rec.get("attrs", {})
        old_cc = old_rec.get("children_count", 0)
        new_cc = new_rec.get("children_count", 0)

        if old_attrs != new_attrs or old_cc != new_cc:
            # Build per-attribute diff
            all_keys = set(old_attrs) | set(new_attrs)
            attr_diff = {
                k: [old_attrs.get(k), new_attrs.get(k)]
                for k in sorted(all_keys)
                if old_attrs.get(k) != new_attrs.get(k)
            }
            if old_cc != new_cc:
                attr_diff["__children_count"] = [old_cc, new_cc]
            _bucket(_type(path))["changed"].append({
                "path":      path,
                "attr_diff": attr_diff,
            })

    return changes


def _find_two_latest() -> tuple[str, str] | None:
    """Find the two most recent snapshot versions by folder name."""
    snap_dirs = sorted(
        [d for d in SNAPSHOTS_DIR.iterdir() if d.is_dir() and (d / "_manifest.json").exists()]
    )
    if len(snap_dirs) < 2:
        return None
    return snap_dirs[-2].name, snap_dirs[-1].name


def run(v_old: str | None = None, v_new: str | None = None):
    if not SNAPSHOTS_DIR.exists():
        print("ERROR: No snapshots directory found. Run explorer_runner.py --snapshot first.")
        sys.exit(1)

    # Auto-detect versions if not provided
    if v_old is None or v_new is None:
        pair = _find_two_latest()
        if pair is None:
            print("Need at least 2 snapshots to generate a changelog.")
            print(f"Available: {[d.name for d in SNAPSHOTS_DIR.iterdir() if d.is_dir()]}")
            sys.exit(1)
        v_old, v_new = pair
        print(f"Auto-detected versions: {v_old} -> {v_new}")
    sys.stdout.flush()

    old_dir = SNAPSHOTS_DIR / v_old
    new_dir = SNAPSHOTS_DIR / v_new

    for d, v in [(old_dir, v_old), (new_dir, v_new)]:
        if not d.exists():
            print(f"ERROR: Snapshot not found: {d}")
            sys.exit(1)

    print(f"Loading snapshot: {v_old}...")
    old_records = _load_snapshot(old_dir)
    print(f"  {len(old_records):,} records")
    print(f"Loading snapshot: {v_new}...")
    new_records = _load_snapshot(new_dir)
    print(f"  {len(new_records):,} records")
    sys.stdout.flush()

    print("Diffing...")
    changes = _diff_records(old_records, new_records)

    # Summary counts
    total_added   = sum(len(v["added"])   for v in changes.values())
    total_removed = sum(len(v["removed"]) for v in changes.values())
    total_changed = sum(len(v["changed"]) for v in changes.values())

    CHANGELOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CHANGELOGS_DIR / f"{v_old}-to-{v_new}.json"

    result = {
        "from_version": v_old,
        "to_version":   v_new,
        "generated":    datetime.now(timezone.utc).isoformat(),
        "summary": {
            "added":   total_added,
            "removed": total_removed,
            "changed": total_changed,
        },
        "changes": changes,
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nChangelog: {out_path}")
    print(f"  Added:   {total_added:,}")
    print(f"  Removed: {total_removed:,}")
    print(f"  Changed: {total_changed:,}")
    sys.stdout.flush()
    return str(out_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate changelog between two snapshots")
    parser.add_argument("--from", dest="v_old", help="old version (auto-detect if omitted)")
    parser.add_argument("--to",   dest="v_new", help="new version (auto-detect if omitted)")
    args = parser.parse_args()
    run(args.v_old, args.v_new)
