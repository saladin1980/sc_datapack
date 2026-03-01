"""
Ground vehicles reference page generator.
Parses ground vehicle XMLs from the DataCore extraction,
outputs a self-contained searchable/filterable HTML page.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR

# Reuse localization helper from ships_preview
from pipeline.ships_preview import build_localization_index

RECORDS_DIR = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
GV_DIR      = RECORDS_DIR / "entities" / "groundvehicles"

# ── Manufacturer display names ─────────────────────────────────────────────────
MFR_NAMES = {
    "AEGS": "Aegis Dynamics",       "ANVL": "Anvil Aerospace",
    "ARGO": "Argo Astronautics",    "BANU": "Banu",
    "CNOU": "Consolidated Outland", "CRUS": "Crusader Industries",
    "DRAK": "Drake Interplanetary", "ESPR": "Esperia",
    "GRIN": "Greycat Industrial",   "KRIG": "Kruger Intergalactic",
    "MISC": "MISC",                 "MRAI": "Mirai",
    "ORIG": "Origin Jumpworks",     "RSI":  "Roberts Space Industries",
    "TMBL": "Tumbril",              "XIAN": "Aopoa",
}

# ── Movement class mapping ─────────────────────────────────────────────────────
MOVEMENT_LABELS = {
    "ArcadeWheeled": "Wheeled",
    "ArcadeTracked":  "Tracked",
    "ArcadeHover":    "Hover",
    "ArcadeVTOL":     "VTOL",
    "Wheeled":        "Wheeled",
    "Tracked":        "Tracked",
    "Hover":          "Hover",
}

# ── Skip filter ────────────────────────────────────────────────────────────────
_SKIP_PATTERNS = (
    "_ai_", "_unmanned_", "_indestructible", "nocrimesagainst",
    "_pu_ai_", "_ea_", "_raceannouncer", "_prison",
)

def _should_skip(stem):
    s = stem.lower()
    return any(p in s for p in _SKIP_PATTERNS)


# ── Lightweight manufacturer index ────────────────────────────────────────────
def build_mfr_index():
    """Build {uuid -> manufacturer_code} from scitemmanufacturer XMLs."""
    index = {}
    mfr_dir = RECORDS_DIR / "scitemmanufacturer"
    if not mfr_dir.exists():
        print("  WARNING: scitemmanufacturer dir not found")
        return index
    for xml_file in mfr_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            # DataCore dump uses __id; old extraction uses __ref
            uid = root.get("__id") or root.get("__ref")
            code = root.get("Code") or root.get("code") or xml_file.stem.upper()
            if uid:
                index[uid] = code
        except Exception:
            pass
    print(f"  {len(index):,} manufacturer UUIDs indexed")
    return index


# ── Localization helpers ───────────────────────────────────────────────────────
def _resolve_loc(key_raw, loc_idx):
    """Strip '@' prefix and look up in localization index. Returns '' on miss."""
    if not key_raw or not key_raw.startswith("@"):
        return key_raw or ""
    key = key_raw[1:].lower()
    val = loc_idx.get(key, "")
    if "PLACEHOLDER" in val.upper() or "UNINITIALIZED" in val.upper():
        return ""
    return val.replace("\\n", " ").replace("\\t", " ").strip()


def _clean_loc_fallback(key_raw, prefix):
    """Strip '@' + known prefix, replace underscores, title-case as fallback."""
    if not key_raw:
        return ""
    s = key_raw.lstrip("@")
    for p in prefix:
        s = s.replace(p, "")
    return s.replace("_", " ").strip().title()


# ── Vehicle parser ─────────────────────────────────────────────────────────────
def parse_vehicle(path, mfr_idx, loc_idx):
    """Parse one ground vehicle XML. Returns info dict or None on error."""
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        print(f"  PARSE ERROR {path.name}: {e}")
        return None

    info = {
        "file":     path.stem,
        "name":     "",
        "mfr":      "",
        "mfr_code": "",
        "career":   "",
        "role":     "",
        "crew":     0,
        "hull_hp":  0,
        "ins_wait": 0.0,
        "ins_fee":  0,
        "bbox_x":   0.0,
        "bbox_y":   0.0,
        "bbox_z":   0.0,
        "movement": "",
        "weapons":  0,
    }

    # ── VehicleComponentParams ────────────────────────────────────────────────
    for el in root.iter():
        pt = el.get("__polymorphicType", "")
        if "VehicleComponentParams" not in el.tag and "VehicleComponentParams" not in pt:
            continue

        # Name (loc key like @vehicle_NameTMBL_Cyclone)
        vn_raw = el.get("vehicleName", "")
        info["name"] = _resolve_loc(vn_raw, loc_idx) or \
                       _clean_loc_fallback(vn_raw, ("vehicle_name", "vehicle_Name"))

        # Career / role
        vc_raw = el.get("vehicleCareer", "")
        vr_raw = el.get("vehicleRole", "")
        info["career"] = _resolve_loc(vc_raw, loc_idx) or \
                         _clean_loc_fallback(vc_raw, ("vehicle_focus_", "vehicle_career_"))
        info["role"]   = _resolve_loc(vr_raw, loc_idx) or \
                         _clean_loc_fallback(vr_raw, ("vehicle_class_", "vehicle_role_"))

        # Crew
        try:
            info["crew"] = int(el.get("crewSize", 0))
        except (ValueError, TypeError):
            pass

        # Hull HP
        try:
            info["hull_hp"] = int(float(el.get("vehicleHullDamageNormalizationValue", 0)))
        except (ValueError, TypeError):
            pass

        # Movement class
        mv = el.get("movementClass", "")
        info["movement"] = MOVEMENT_LABELS.get(mv, mv.replace("Arcade", "") if mv else "")

        # Manufacturer UUID
        mfr_uuid = el.get("manufacturer", "")
        if mfr_uuid and mfr_uuid != "00000000-0000-0000-0000-000000000000":
            code = mfr_idx.get(mfr_uuid, "")
            info["mfr_code"] = code
            info["mfr"] = MFR_NAMES.get(code, code)

        # Bounding box (direct child of VehicleComponentParams)
        for sub in el:
            if "maxBoundingBoxSize" in sub.tag or sub.tag == "maxBoundingBoxSize":
                try:
                    info["bbox_x"] = float(sub.get("x", 0))
                    info["bbox_y"] = float(sub.get("y", 0))
                    info["bbox_z"] = float(sub.get("z", 0))
                except (ValueError, TypeError):
                    pass
                break
        break  # only first VehicleComponentParams

    # Bounding box fallback via full iter
    if info["bbox_x"] == 0.0 and info["bbox_y"] == 0.0:
        for el in root.iter():
            if el.tag == "maxBoundingBoxSize" or "maxBoundingBoxSize" in el.tag:
                try:
                    info["bbox_x"] = float(el.get("x", 0))
                    info["bbox_y"] = float(el.get("y", 0))
                    info["bbox_z"] = float(el.get("z", 0))
                except (ValueError, TypeError):
                    pass
                break

    # Name fallback from root tag: EntityClassDefinition.TMBL_Cyclone
    if not info["name"]:
        tag = root.tag
        if "." in tag:
            cls = tag.split(".", 1)[1]   # e.g. TMBL_Cyclone
            info["name"] = cls.replace("_", " ")

    # ── Insurance ─────────────────────────────────────────────────────────────
    for el in root.iter():
        if el.tag == "shipInsuranceParams" or "shipInsuranceParams" in el.tag:
            try:
                info["ins_wait"] = float(el.get("baseWaitTimeMinutes", 0))
            except (ValueError, TypeError):
                pass
            try:
                info["ins_fee"] = int(float(el.get("baseExpeditingFee", 0)))
            except (ValueError, TypeError):
                pass
            break

    # ── Weapon hardpoints from loadout ─────────────────────────────────────────
    weapon_count = 0
    for el in root.iter():
        if el.tag != "SItemPortLoadoutEntryParams" and \
           "SItemPortLoadoutEntryParams" not in el.tag:
            continue
        port = el.get("itemPortName", "").lower()
        if any(k in port for k in ("weapon", "gun", "turret", "rack")):
            weapon_count += 1
    info["weapons"] = weapon_count

    return info


# ── Scanner ────────────────────────────────────────────────────────────────────
def scan_all_vehicles():
    if not GV_DIR.exists():
        print(f"  WARNING: groundvehicles dir not found: {GV_DIR}")
        return []
    paths = sorted(f for f in GV_DIR.glob("*.xml") if not _should_skip(f.stem))
    return paths


# ── HTML helpers ───────────────────────────────────────────────────────────────
CAREER_COLORS = {
    "combat":           "#c0392b",
    "ground combat":    "#c0392b",
    "exploration":      "#2980b9",
    "transport":        "#27ae60",
    "transporter":      "#27ae60",
    "support":          "#8e44ad",
    "mining":           "#e67e22",
    "industrial":       "#7f8c8d",
    "racing":           "#f39c12",
    "competition":      "#f39c12",
    "ground":           "#546e7a",
    "utility":          "#546e7a",
}

def _career_color(career):
    return CAREER_COLORS.get(career.lower(), "#5b9cf6")


def _badge(text, color):
    if not text:
        return ""
    return f'<span class="badge" style="background:{color}">{text}</span>'


def _kv(k, v):
    if v == "" or v is None:
        return ""
    return f'<span class="k">{k}</span><span class="v">{v}</span>'


def vehicle_to_html(v):
    name   = v["name"] or v["file"]
    mfr    = v["mfr"] or v["mfr_code"] or "Unknown"
    career = v["career"]
    role   = v["role"]

    career_badge = _badge(career, _career_color(career)) if career else ""
    role_text    = f" &middot; {role}" if role else ""

    # Specs section
    spec_rows = ""
    if v["crew"]:
        spec_rows += _kv("Crew", str(v["crew"]))
    if v["hull_hp"]:
        spec_rows += _kv("Hull HP", f'{v["hull_hp"]:,}')
    if v["movement"]:
        spec_rows += _kv("Drive", v["movement"])
    if v["weapons"] > 0:
        spec_rows += _kv("Weapon ports", str(v["weapons"]))
    specs_html = (
        f'<div class="stat-section">'
        f'<div class="stat-title">Specifications</div>'
        f'<div class="kv-grid">{spec_rows}</div></div>'
    ) if spec_rows else ""

    # Dimensions section
    dims_html = ""
    if v["bbox_x"] or v["bbox_y"] or v["bbox_z"]:
        bx = f'{v["bbox_x"]:g}'
        by = f'{v["bbox_y"]:g}'
        bz = f'{v["bbox_z"]:g}'
        dims_html = (
            f'<div class="stat-section">'
            f'<div class="stat-title">Dimensions (m)</div>'
            f'<div class="kv-grid">'
            f'{_kv("W", bx)}'
            f'{_kv("L", by)}'
            f'{_kv("H", bz)}'
            f'</div></div>'
        )

    # Insurance section
    ins_rows = ""
    if v["ins_wait"]:
        ins_rows += _kv("Wait", f'{v["ins_wait"]:.1f} min')
    if v["ins_fee"]:
        ins_rows += _kv("Expedite", f'{v["ins_fee"]:,} aUEC')
    ins_html = (
        f'<div class="stat-section">'
        f'<div class="stat-title">Insurance</div>'
        f'<div class="kv-grid">{ins_rows}</div></div>'
    ) if ins_rows else ""

    body = specs_html + dims_html + ins_html
    if not body:
        body = '<div class="no-stats">No stats found</div>'

    mfr_key    = v["mfr_code"].lower() if v["mfr_code"] else "unknown"
    career_key = career.lower().replace(" ", "") if career else "unknown"

    return (
        f'<div class="item-card" '
        f'data-mfr="{mfr_key}" data-career="{career_key}" data-name="{name.lower()}">\n'
        f'  <div class="card-header">\n'
        f'    <div class="card-title-row">'
        f'<span class="item-name">{name}</span>{career_badge}</div>\n'
        f'    <div class="card-meta">{mfr}{role_text}</div>\n'
        f'  </div>\n'
        f'  <div class="card-body">{body}</div>\n'
        f'</div>'
    )


# ── HTML page ──────────────────────────────────────────────────────────────────
def generate_html(vehicles):
    valid  = [v for v in vehicles if v]
    count  = len(valid)
    cards  = "\n".join(vehicle_to_html(v) for v in valid)

    # Manufacturer tabs
    mfr_counts = Counter(v["mfr"] or "Unknown" for v in valid)
    mfr_tabs = (
        f'<button class="tab mfr-tab active" data-mfr="all" onclick="setMfrTab(this)">'
        f'All <span class="tc">{count}</span></button>\n'
    )
    for mfr, c in sorted(mfr_counts.items()):
        code = next((v["mfr_code"].lower() for v in valid
                     if (v["mfr"] or "Unknown") == mfr), "unknown")
        mfr_tabs += (
            f'<button class="tab mfr-tab" data-mfr="{code}" onclick="setMfrTab(this)">'
            f'{mfr} <span class="tc">{c}</span></button>\n'
        )

    # Career tabs
    career_counts = Counter(v["career"] for v in valid if v["career"])
    career_tabs = (
        f'<button class="tab career-tab active" data-career="all" onclick="setCareerTab(this)">'
        f'All Careers <span class="tc">{count}</span></button>\n'
    )
    for career, c in sorted(career_counts.items()):
        ckey  = career.lower().replace(" ", "")
        color = _career_color(career)
        career_tabs += (
            f'<button class="tab career-tab" data-career="{ckey}" '
            f'style="--cc:{color}" onclick="setCareerTab(this)">'
            f'{career} <span class="tc">{c}</span></button>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SC Ground Vehicles</title>
<style>
  :root {{
    --bg:     #0d0f14;
    --card:   #161922;
    --border: #2a2f3d;
    --text:   #e8ecf0;
    --muted:  #8892a4;
    --accent: #5b9cf6;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font:14px/1.5 "Inter","Segoe UI",sans-serif; }}
  h1 {{ font-size:1.6rem; font-weight:700; letter-spacing:-.02em; }}
  header {{ padding:20px 24px 12px; border-bottom:1px solid var(--border); }}
  header .sub {{ color:var(--muted); font-size:.85rem; margin-top:4px; }}
  .controls {{ display:flex; flex-direction:column; border-bottom:1px solid var(--border); }}
  .filter-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px;
                 padding:10px 24px; border-bottom:1px solid var(--border); }}
  .filter-row:last-child {{ border-bottom:none; }}
  .filter-label {{ font-size:.7rem; font-weight:700; letter-spacing:.06em;
                   text-transform:uppercase; color:var(--muted); min-width:60px; }}
  .tabs {{ display:flex; flex-wrap:wrap; gap:6px; flex:1; }}
  .tab {{ background:var(--card); border:1px solid var(--border); border-radius:6px;
          color:var(--muted); cursor:pointer; font-size:.8rem; padding:5px 12px;
          transition:all .15s; }}
  .tab:hover {{ border-color:var(--accent); color:var(--text); }}
  .tab.active {{ background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }}
  .career-tab.active {{ background:var(--cc,var(--accent)); border-color:var(--cc,var(--accent)); }}
  .tc {{ opacity:.7; font-weight:400; }}
  #search-box {{ background:var(--card); border:1px solid var(--border); border-radius:6px;
                 color:var(--text); font-size:.85rem; padding:6px 12px; width:220px; }}
  #search-box:focus {{ outline:none; border-color:var(--accent); }}
  #vis-count {{ color:var(--muted); font-size:.8rem; white-space:nowrap; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr));
           gap:14px; padding:18px 24px; }}
  .item-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px;
                overflow:hidden; transition:border-color .15s; }}
  .item-card:hover {{ border-color:var(--accent); }}
  .card-header {{ padding:12px 14px 10px; border-bottom:1px solid var(--border); }}
  .card-title-row {{ display:flex; align-items:flex-start; gap:6px; flex-wrap:wrap; margin-bottom:4px; }}
  .item-name {{ font-weight:600; font-size:.9rem; line-height:1.3; flex:1; min-width:0;
                overflow-wrap:break-word; }}
  .badge {{ font-size:.7rem; font-weight:700; border-radius:4px; padding:2px 7px;
            color:#fff; white-space:nowrap; align-self:flex-start; }}
  .card-meta {{ font-size:.75rem; color:var(--muted); }}
  .card-body {{ padding:10px 14px 12px; display:flex; flex-direction:column; gap:10px; }}
  .stat-section {{ display:flex; flex-direction:column; gap:4px; }}
  .stat-title {{ font-size:.7rem; font-weight:700; letter-spacing:.05em;
                 text-transform:uppercase; color:var(--muted); margin-bottom:2px; }}
  .kv-grid {{ display:grid; grid-template-columns:auto 1fr; gap:2px 14px; }}
  .k {{ font-size:.8rem; color:var(--muted); }}
  .v {{ font-size:.8rem; font-weight:500; }}
  .no-stats {{ font-size:.8rem; color:var(--muted); font-style:italic; }}
</style>
</head>
<body>
<header>
  <h1>Ground Vehicles</h1>
  <div class="sub">Star Citizen &mdash; {count} vehicles &middot; SC 4.6.172</div>
</header>
<div class="controls">
  <div class="filter-row">
    <span class="filter-label">Maker</span>
    <div class="tabs">{mfr_tabs}</div>
  </div>
  <div class="filter-row">
    <span class="filter-label">Career</span>
    <div class="tabs">{career_tabs}</div>
  </div>
  <div class="filter-row">
    <span class="filter-label">Search</span>
    <input id="search-box" type="search" placeholder="vehicle name...">
    <span id="vis-count"></span>
  </div>
</div>
<div class="grid" id="grid">
{cards}
</div>
<script>
var allCards = Array.from(document.querySelectorAll('.item-card'));
var activeMfr = 'all', activeCareer = 'all', searchVal = '';
function setMfrTab(btn) {{
  document.querySelectorAll('.mfr-tab').forEach(function(b) {{ b.classList.remove('active'); }});
  btn.classList.add('active');
  activeMfr = btn.dataset.mfr;
  applyFilters();
}}
function setCareerTab(btn) {{
  document.querySelectorAll('.career-tab').forEach(function(b) {{ b.classList.remove('active'); }});
  btn.classList.add('active');
  activeCareer = btn.dataset.career;
  applyFilters();
}}
document.getElementById('search-box').addEventListener('input', function() {{
  searchVal = this.value.toLowerCase();
  applyFilters();
}});
function applyFilters() {{
  var vis = 0;
  allCards.forEach(function(c) {{
    var m = activeMfr    === 'all' || c.dataset.mfr    === activeMfr;
    var r = activeCareer === 'all' || c.dataset.career === activeCareer;
    var s = !searchVal   || c.dataset.name.indexOf(searchVal) !== -1;
    var show = m && r && s;
    c.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById('vis-count').textContent =
    vis + ' vehicle' + (vis !== 1 ? 's' : '');
}}
applyFilters();
</script>
</body>
</html>"""


# ── Entry point ────────────────────────────────────────────────────────────────
def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Ground Vehicles: loading indexes...")
    sys.stdout.flush()
    loc_idx = build_localization_index()
    mfr_idx = build_mfr_index()

    paths = scan_all_vehicles()
    print(f"  {len(paths)} vehicle XMLs (after filtering NPC/AI variants)")
    sys.stdout.flush()

    if not paths:
        print("  ERROR: no ground vehicle XMLs found. Run extractor.py first.")
        sys.exit(1)

    vehicles = []
    for path in paths:
        v = parse_vehicle(path, mfr_idx, loc_idx)
        if v:
            vehicles.append(v)

    vehicles.sort(key=lambda v: (v["mfr"], v["name"]))

    print(f"  Parsed: {len(vehicles)} vehicles")
    sys.stdout.flush()

    out  = REPORTS_DIR / "groundvehicles.html"
    html = generate_html(vehicles)
    out.write_text(html, encoding="utf-8")
    sz   = len(html)
    print(f"  Written: {out.name} ({sz:,} bytes)")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
