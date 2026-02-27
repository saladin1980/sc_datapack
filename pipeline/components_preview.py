"""
Component reference page generator.
Scans ships/ component XMLs, extracts stats for every equippable item,
outputs a searchable/filterable self-contained HTML page.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR

# Reuse index builders + helpers from ships_preview
from pipeline.ships_preview import (
    build_uuid_index,
    build_classname_index,
    build_localization_index,
    build_manufacturer_index,
    parse_component_stats,
    _get_attach_def,
    _get_display_name,
    _fmt,
    _stats_badge,
)

RECORDS_DIR    = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
SCITEM_DIR     = RECORDS_DIR / "entities" / "scitem"
SHIPS_COMP_DIR = SCITEM_DIR / "ships"

MFR_NAMES = {
    "AEGS": "Aegis",   "ANVL": "Anvil",    "BEHR": "Behring",
    "BASL": "Basilisk","CGPO": "CIG",       "JUST": "JUST",
    "ACOM": "Acom",    "AMRS": "Amrs",      "GATS": "Gatso",
    "KRIG": "Kruger",  "MISC": "MISC",      "ORIG": "Origin",
    "RSI":  "RSI",     "DRAK": "Drake",     "CRUS": "Crusader",
    "CNOU": "C. Outland","XNAA": "Xenotech","TALN": "Talon",
    "TMBL": "Tumbril", "ARGO": "Argo",      "VANDUUL": "Vanduul",
    "KLWE": "Klaus&Werner","MNVR": "Musashi","BANU": "Banu",
    "VOLT": "Volt",    "GRYO": "Greycat",   "SBER": "Sber",
    "CRSD": "Crossfire","LNDR": "Lander",
}

# ── Category definitions ───────────────────────────────────────────────────────

# AttachDef.Type → (icon, section label, css slug)
TYPE_META = {
    # ── Defence ───────────────────────────────────────────────────────────────
    "Shield":               ("🛡",  "Shields",                    "shield"),
    "ShieldController":     ("🛡",  "Shield Controllers",         "shield"),
    # ── Power / Thermal ───────────────────────────────────────────────────────
    "PowerPlant":           ("⚡",  "Power Plants",               "power"),
    "Cooler":               ("❄",   "Coolers",                    "cooler"),
    # ── Quantum ───────────────────────────────────────────────────────────────
    "QuantumDrive":         ("🌌",  "Quantum Drives",             "quantum"),
    "Quantum Interdiction Generator": ("🌌", "Quantum Interdiction", "qi"),
    "QuantumCalibrationComputer":     ("🌌", "QT Calibration",    "qtc"),
    # ── Fuel ──────────────────────────────────────────────────────────────────
    "FuelTank":             ("⛽",  "Hydrogen Fuel Tanks",        "fuel"),
    "QuantumFuelTank":      ("⚗",   "Quantum Fuel Tanks",        "qfuel"),
    # ── Weapons (ship) ────────────────────────────────────────────────────────
    "WeaponGun":            ("⚔",   "Weapons (Ballistic / Energy)", "weapon"),
    "WeaponMining":         ("⛏",   "Mining Lasers",              "mining"),
    "WeaponTractorBeam":    ("🤝",  "Tractor Beams",              "util"),
    "WeaponDefensive":      ("🛡",   "Countermeasures",           "cm"),
    "MissileLauncher":      ("🚀",  "Missile Launchers",          "missile"),
    "Missile":              ("🚀",  "Missiles",                   "missile"),
    "Turret":               ("⚔",   "Turrets",                   "turret"),
    "TurretBase":           ("⚔",   "Turret Bases",              "turret"),
    # ── Salvage ───────────────────────────────────────────────────────────────
    "SalvageField":         ("🔧",  "Salvage (Field)",            "salvage"),
    # ── Cargo / Storage ───────────────────────────────────────────────────────
    "CargoGrid":            ("📦",  "Cargo Grids",                "cargo"),
    "Cargo":                ("📦",  "Cargo / Storage",            "cargo"),
    # ── Ship internals ────────────────────────────────────────────────────────
    "DockingCollar":        ("🔗",  "Docking Collars",            "misc"),
    "Emp":                  ("⚡",  "EMP",                        "emp"),
    "Misc":                 ("⚙",   "Misc Ship Systems",         "misc"),
    # ── Catch-all ─────────────────────────────────────────────────────────────
    "Other":                ("⚙",   "Other",                     "other"),
}

SECTION_ORDER = [
    "Shield", "ShieldController",
    "PowerPlant", "Cooler",
    "QuantumDrive", "Quantum Interdiction Generator", "QuantumCalibrationComputer",
    "FuelTank", "QuantumFuelTank",
    "WeaponGun", "WeaponMining", "WeaponTractorBeam",
    "WeaponDefensive", "MissileLauncher", "Missile", "Turret", "TurretBase",
    "SalvageField",
    "CargoGrid", "Cargo",
    "DockingCollar", "Emp", "Misc",
    "Other",
]

# Dirs/names to skip entirely
SKIP_DIRS   = {"paints", "seataccess", "seat", "dashboard", "displays",
               "access", "airlocks", "door", "interior", "lootcrate",
               "ship_armor"}
# FPS / personal gear — not ship components
SKIP_TYPES  = {"", "Paint", "Parachute", "UNDEFINED", "FoodDrink",
               "Clothing", "Helmet", "Backpack", "Undersuit",
               "Armor", "WeaponPersonal", "WeaponAttachment",
               "Usable", "Commodity", "Gadget", "Medical",
               "GrapplingHook", "Flashlight", "AttachedPart",
               "PersonalStorage",
               # Ship systems excluded from listing (unnamed / no useful stats)
               "MainThruster", "ManneuverThruster", "VtolThruster",
               "FuelIntake",
               "Radar", "Scanner",
               "LifeSupportGenerator", "GravityGenerator",
               "SelfDestruct",
               "Relay",
               }
# All *Controller types are also skipped, except ShieldController
# (checked dynamically in scan_all_components)

# ── Scanner ────────────────────────────────────────────────────────────────────

def scan_all_components(uuid_idx, cls_idx, loc_idx, mfr_idx):
    """Walk ships/ (and weapons subdir if present), return list of component dicts."""
    components = []
    scan_dirs  = [SHIPS_COMP_DIR]
    weapons_dir = SCITEM_DIR / "weapons"
    if weapons_dir.exists():
        scan_dirs.append(weapons_dir)
    missiles_dir = SCITEM_DIR / "missiles"
    if missiles_dir.exists():
        scan_dirs.append(missiles_dir)

    total_xml = sum(len(list(d.rglob("*.xml"))) for d in scan_dirs)
    print(f"  Scanning {total_xml:,} XMLs in {len(scan_dirs)} dirs...")

    processed = 0
    for scan_dir in scan_dirs:
        for xml_file in scan_dir.rglob("*.xml"):
            # Skip by directory name
            parts_lc = {p.lower() for p in xml_file.parts}
            if parts_lc & SKIP_DIRS:
                continue
            # Skip templates and suffixed test variants
            stem_lc = xml_file.stem.lower()
            if any(s in stem_lc for s in ("_template", "_test", "_placeholder")):
                continue

            try:
                root = ET.parse(xml_file).getroot()
            except Exception:
                processed += 1
                continue

            # Must be an EntityClassDefinition
            if not root.tag.startswith("EntityClassDefinition."):
                processed += 1
                continue

            class_name = root.tag.split(".", 1)[1]
            typ, sub_typ, size, grade = _get_attach_def(root)

            # Skip unwanted types; all *Controller except ShieldController also skipped
            if typ in SKIP_TYPES or (typ.endswith("Controller") and typ != "ShieldController"):
                processed += 1
                continue

            # Manufacturer from AttachDef.Manufacturer UUID
            mfr_code = ""
            for elem in root.iter():
                if "AttachDef" in elem.tag or elem.tag == "AttachDef":
                    mfr_uuid = elem.get("Manufacturer","")
                    if mfr_uuid:
                        mfr_code = mfr_idx.get(mfr_uuid,"")
                    break
            mfr_display = MFR_NAMES.get(mfr_code, mfr_code) if mfr_code else ""

            display_name = _get_display_name(root, loc_idx)

            # Get stats using the shared parser
            cstats = parse_component_stats(xml_file, uuid_idx, loc_idx)
            stats  = cstats.get("stats", [])

            # Normalise type to one of our known buckets
            bucket = typ if typ in TYPE_META else "Other"

            components.append({
                "class":        class_name,
                "display_name": display_name or class_name,
                "type":         typ,
                "sub_type":     sub_typ,
                "size":         size,
                "grade":        grade,
                "mfr":          mfr_display,
                "stats":        stats,
                "bucket":       bucket,
                "path":         str(xml_file.relative_to(RECORDS_DIR)),
            })
            processed += 1
            if processed % 500 == 0:
                print(f"    {processed:,}/{total_xml:,}...", flush=True)

    return components

# ── HTML generator ─────────────────────────────────────────────────────────────

def generate_html(components):
    by_bucket = defaultdict(list)
    for c in components:
        by_bucket[c["bucket"]].append(c)

    # Sort each bucket: size asc, then grade asc, then name
    for bucket in by_bucket:
        by_bucket[bucket].sort(key=lambda c: (
            int(c["size"]) if c["size"].isdigit() else 99,
            int(c["grade"]) if c["grade"].isdigit() else 99,
            c["display_name"].lower(),
        ))

    total = len(components)

    # ── Tab nav ───────────────────────────────────────────────────────────────
    tabs_html = '<button class="tab active" onclick="showAll(this)">All</button>\n'
    for bucket in SECTION_ORDER:
        comps = by_bucket.get(bucket, [])
        if not comps:
            continue
        icon, label, css = TYPE_META.get(bucket, ("⚙", bucket, "other"))
        count = len(comps)
        tabs_html += f'<button class="tab" onclick="showCat(this,\'{bucket}\')">{icon} {label} <span class="tab-count">{count}</span></button>\n'

    # ── Sections ──────────────────────────────────────────────────────────────
    sections_html = ""
    for bucket in SECTION_ORDER:
        comps = by_bucket.get(bucket, [])
        if not comps:
            continue
        icon, label, css = TYPE_META.get(bucket, ("⚙", bucket, "other"))

        rows = ""
        for c in comps:
            sg    = f"S{c['size']}" if c.get("size") else ""
            sg   += f" G{c['grade']}" if c.get("grade") else ""
            dname = c["display_name"]
            # Search text embedded as data attr for JS filtering
            search_text = f"{dname} {c['class']} {c['mfr']} {c['sub_type']}".lower()
            rows += f"""<tr data-search="{search_text}">
              <td class="td-name">
                <span class="item-name">{dname}</span>
                <code class="cls cls-{css}">{c['class']}</code>
              </td>
              <td class="td-mfr">{c['mfr'] or '—'}</td>
              <td class="td-sg td-center">{sg or '—'}</td>
              <td class="td-sub">{c['sub_type'] or '—'}</td>
              <td class="td-stats">{_stats_badge(c['stats'])}</td>
            </tr>"""

        sections_html += f"""
  <div class="cat-section" data-cat="{bucket}">
    <h3 class="sec-head">{icon} {label} <span class="sec-count">{len(comps)}</span></h3>
    <table class="comp-table" id="tbl-{bucket}">
      <thead>
        <tr>
          <th onclick="sortTable('tbl-{bucket}',0)" class="th-sort">Component ▲</th>
          <th onclick="sortTable('tbl-{bucket}',1)" class="th-sort">Mfr</th>
          <th onclick="sortTable('tbl-{bucket}',2)" class="th-sort">S/G</th>
          <th onclick="sortTable('tbl-{bucket}',3)" class="th-sort">Subtype</th>
          <th>Stats</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SC DataPack - Component Reference</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:'Segoe UI',sans-serif; font-size:13px; line-height:1.5; padding:20px 24px; }}
h1   {{ color:#58a6ff; font-size:22px; margin-bottom:2px; }}
.subtitle {{ color:#8b949e; font-size:12px; margin-bottom:16px; }}

/* ── Search ── */
.search-bar {{ display:flex; gap:10px; align-items:center; margin-bottom:14px; }}
#search {{ background:#161b22; border:1px solid #30363d; border-radius:6px; color:#e6edf3;
           padding:6px 12px; font-size:13px; width:320px; outline:none; }}
#search:focus {{ border-color:#58a6ff; }}
#search-count {{ color:#8b949e; font-size:12px; }}

/* ── Tabs ── */
.tabs {{ display:flex; flex-wrap:wrap; gap:4px; margin-bottom:16px; }}
.tab {{ background:#161b22; border:1px solid #30363d; border-radius:20px; padding:3px 10px;
        color:#8b949e; font-size:11px; cursor:pointer; transition:all 0.15s; white-space:nowrap; }}
.tab:hover {{ background:#1c2128; color:#c9d1d9; }}
.tab.active {{ background:#1f3d5a; border-color:#58a6ff; color:#58a6ff; }}
.tab-count {{ background:#21262d; border-radius:10px; padding:0 5px; font-size:10px;
              color:#8b949e; margin-left:3px; }}

/* ── Sections ── */
.cat-section {{ margin-bottom:28px; }}
.cat-section.hidden {{ display:none; }}
.sec-head {{ color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px;
             margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid #21262d; }}
.sec-count {{ background:#21262d; border-radius:10px; padding:1px 7px; font-size:10px;
              color:#6e7681; margin-left:6px; vertical-align:middle; }}

/* ── Table ── */
.comp-table {{ width:100%; border-collapse:collapse; font-size:12px; table-layout:fixed; }}
.comp-table th {{ background:#0d1117; color:#8b949e; text-align:left; padding:5px 8px;
                  font-weight:500; border-bottom:1px solid #30363d; white-space:nowrap; }}
.comp-table td {{ padding:4px 8px; border-bottom:1px solid #21262d; vertical-align:middle; }}
.comp-table tr:last-child td {{ border-bottom:none; }}
.comp-table tr:hover td {{ background:#1c2128; }}
.comp-table tr.row-hidden {{ display:none; }}
.th-sort {{ cursor:pointer; user-select:none; }}
.th-sort:hover {{ color:#e6edf3; }}

/* Column widths */
.td-name  {{ width:32%; }}
.td-mfr   {{ width:8%; color:#8b949e; }}
.td-sg    {{ width:7%; }}
.td-sub   {{ width:10%; color:#8b949e; font-size:11px; }}
.td-stats {{ width:43%; }}
.td-center {{ text-align:center; }}

/* ── Name / code ── */
.item-name {{ display:block; color:#e6edf3; font-weight:600; font-size:12px; line-height:1.3; }}
code.cls {{ display:block; background:#1c2128; border:1px solid #30363d; border-radius:3px;
            padding:1px 4px; font-size:10px; font-family:Consolas,monospace;
            margin-top:1px; word-break:break-all; }}
code.cls-shield   {{ color:#58a6ff; }}
code.cls-power    {{ color:#e3b341; }}
code.cls-cooler   {{ color:#79c0ff; }}
code.cls-quantum  {{ color:#bc8cff; }}
code.cls-fuel     {{ color:#7ee787; }}
code.cls-qfuel    {{ color:#56d364; }}
code.cls-intake   {{ color:#7ee787; }}
code.cls-thruster {{ color:#ffa198; }}
code.cls-radar    {{ color:#a5d6ff; }}
code.cls-weapon   {{ color:#ff7b72; }}
code.cls-turret   {{ color:#d2a8ff; }}
code.cls-missile  {{ color:#ffa657; }}
code.cls-mining   {{ color:#e3b341; }}
code.cls-salvage  {{ color:#f0883e; }}
code.cls-util     {{ color:#8b949e; }}
code.cls-cm       {{ color:#58a6ff; }}
code.cls-misc     {{ color:#8b949e; }}
code.cls-qi       {{ color:#bc8cff; }}
code.cls-other    {{ color:#8b949e; }}
code.cls-armor    {{ color:#c9d1d9; }}
code.cls-storage  {{ color:#7ee787; }}
code.cls-emp      {{ color:#e3b341; }}
code.cls-qtc      {{ color:#bc8cff; }}

/* ── Badges ── */
.badge {{ display:inline-flex; background:#21262d; border:1px solid #30363d; border-radius:4px;
          padding:1px 0; font-size:11px; vertical-align:middle; margin:1px 2px 1px 0; }}
.badge .bl {{ padding:0 4px; color:#8b949e; border-right:1px solid #30363d; }}
.badge .bv {{ padding:0 5px; color:#e6edf3; }}
.muted {{ color:#484f58; }}
</style>
</head>
<body>
<h1>&#x1F4E6; SC DataPack — Component Reference</h1>
<p class="subtitle">{total:,} equippable components extracted from game data — all sizes &amp; grades</p>

<div class="search-bar">
  <input id="search" type="text" placeholder="Search name, class, manufacturer..." oninput="filterRows(this.value)">
  <span id="search-count"></span>
</div>

<div class="tabs">
{tabs_html}
</div>

{sections_html}

<script>
// ── Category filter ───────────────────────────────────────────────────────────
let activeCat = null;
function showAll(btn) {{
  activeCat = null;
  document.querySelectorAll('.cat-section').forEach(s => s.classList.remove('hidden'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  filterRows(document.getElementById('search').value);
}}
function showCat(btn, cat) {{
  activeCat = cat;
  document.querySelectorAll('.cat-section').forEach(s => {{
    s.classList.toggle('hidden', s.dataset.cat !== cat);
  }});
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  filterRows(document.getElementById('search').value);
}}

// ── Search filter ─────────────────────────────────────────────────────────────
function filterRows(q) {{
  q = q.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('.cat-section').forEach(section => {{
    if (activeCat && section.dataset.cat !== activeCat) return;
    let sectionVisible = 0;
    section.querySelectorAll('tbody tr').forEach(row => {{
      const match = !q || row.dataset.search.includes(q);
      row.classList.toggle('row-hidden', !match);
      if (match) sectionVisible++;
    }});
    visible += sectionVisible;
    // Update section count badge to show filtered count
    const badge = section.querySelector('.sec-count');
    if (badge) badge.textContent = q ? sectionVisible : section.querySelectorAll('tbody tr').length;
  }});
  const el = document.getElementById('search-count');
  if (q) el.textContent = visible + ' matching';
  else el.textContent = '';
}}

// ── Column sort ───────────────────────────────────────────────────────────────
const _sortState = {{}};
function sortTable(tblId, col) {{
  const tbl  = document.getElementById(tblId);
  const tbody = tbl.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc  = !_sortState[tblId + col];
  _sortState[tblId + col] = asc;
  rows.sort((a, b) => {{
    const av = a.cells[col]?.innerText.trim() || '';
    const bv = b.cells[col]?.innerText.trim() || '';
    const an = parseFloat(av); const bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>"""


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Building indexes...")
    uuid_idx = build_uuid_index()
    cls_idx  = build_classname_index()
    mfr_idx  = build_manufacturer_index(uuid_idx)
    loc_idx  = build_localization_index()

    print("\nScanning components...")
    components = scan_all_components(uuid_idx, cls_idx, loc_idx, mfr_idx)

    by_type = defaultdict(int)
    for c in components:
        by_type[c["type"]] += 1
    print(f"\n  {len(components):,} components found:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t or '(blank)':<35s} {n:4d}")

    print("\nGenerating HTML...")
    html = generate_html(components)
    out  = REPORTS_DIR / "components_preview.html"
    out.write_text(html, encoding="utf-8")
    print(f"Done. Report -> {out}")
    return out


if __name__ == "__main__":
    run()
