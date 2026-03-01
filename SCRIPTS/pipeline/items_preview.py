"""
Items reference page generator.
Covers player-usable items NOT handled by other reports:
  - Consumables (medical, stims, food/drink)
  - Melee weapons
  - Throwables (grenades)
  - FPS deployable devices (mines, explosives)
  - Carryable tools (tractor beams, multi-tools from carryables/1h)

Outputs a self-contained searchable/filterable HTML page.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR, GAME_VERSION

from pipeline.ships_preview import build_localization_index
from pipeline.groundvehicles_preview import build_mfr_index

RECORDS_DIR = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
SCITEM_DIR  = RECORDS_DIR / "entities" / "scitem"

# ── Source paths and their category labels ────────────────────────────────────
SOURCES = [
    # (path,                                   category,     include_types filter or None=all)
    (SCITEM_DIR / "consumables",               "Consumable", None),
    (SCITEM_DIR / "fps_devices",               "Deployable", None),
    (SCITEM_DIR / "weapons" / "melee",         "Melee",      None),
    (SCITEM_DIR / "weapons" / "throwable",     "Throwable",  None),
    # carryables/1h: filter for consumable/tool types, skip pure furniture
    (SCITEM_DIR / "carryables" / "1h",         "Consumable", {"FPS_Consumable", "Drink", "Food",
                                                               "Gadget", "Misc"}),
    (SCITEM_DIR / "carryables" / "2h",         "Consumable", {"FPS_Consumable", "Drink", "Food",
                                                               "Gadget", "Misc"}),
]

# ── Manufacturer display names (same as other scripts) ───────────────────────
MFR_NAMES = {
    "AEGS": "Aegis Dynamics",       "ANVL": "Anvil Aerospace",
    "ARGO": "Argo Astronautics",    "BANU": "Banu",
    "BEHR": "Behring",              "CNOU": "Consolidated Outland",
    "CRUS": "Crusader Industries",  "DRAK": "Drake Interplanetary",
    "ESPR": "Esperia",              "GRIN": "Greycat Industrial",
    "KRIG": "Kruger Intergalactic", "KLWE": "Klaus & Werner",
    "MISC": "MISC",                 "ORIG": "Origin Jumpworks",
    "RSI":  "Roberts Space Industries",
    "TMBL": "Tumbril",              "CRFL": "CureLife",
    "CRLF": "CureLife",             "TALN": "Talon",
    "ACOM": "Acom",                 "BASL": "Basilisk",
    "AMRS": "Amrs",
}

# ── Skip patterns ─────────────────────────────────────────────────────────────
_SKIP_PATTERNS = (
    "_template", "_nodraw", "_dummy", "_test", "_debug",
    "_npc_", "_ai_", "_s42_",
)

def _should_skip(stem, loc_name):
    s = stem.lower()
    if any(p in s for p in _SKIP_PATTERNS):
        return True
    if not loc_name:
        return True   # no resolved name = dev/placeholder item
    return False


# ── Type → display category mapping ──────────────────────────────────────────
TYPE_CATEGORY = {
    "FPS_Consumable": "Medical / Stim",
    "Drink":          "Food & Drink",
    "Food":           "Food & Drink",
    "WeaponPersonal": "Melee / Throwable",
    "FPS_Deployable": "Deployable",
    "Gadget":         "Tool / Gadget",
    "Misc":           "Misc",
}

SUBTYPE_REFINE = {
    "MedPack":    "Medical / Stim",
    "Medical":    "Medical / Stim",
    "OxygenCap":  "Medical / Stim",
    "Grenade":    "Throwable",
    "Melee":      "Melee",
    "Knife":      "Melee",
    "Tool":       "Tool / Gadget",
    "Gadget":     "Tool / Gadget",
    "Can":        "Food & Drink",
    "Bottle":     "Food & Drink",
    "Small":      "Deployable",
}

def _display_category(item_type, subtype):
    if subtype in SUBTYPE_REFINE:
        return SUBTYPE_REFINE[subtype]
    return TYPE_CATEGORY.get(item_type, item_type or "Other")


# ── Parser ────────────────────────────────────────────────────────────────────
def parse_item(path, category_hint, mfr_idx, loc_idx):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None

    info = {
        "file":      path.stem,
        "name":      "",
        "type":      "",
        "subtype":   "",
        "tags":      "",
        "size":      "",
        "grade":     "",
        "micro_scu": 0,
        "mfr":       "",
        "mfr_code":  "",
        "category":  category_hint,
        "display_cat": "",
    }

    # AttachDef
    for el in root.iter():
        if "AttachDef" not in el.tag and el.tag != "AttachDef":
            continue
        info["type"]    = el.get("Type", "")
        info["subtype"] = el.get("SubType", "")
        info["size"]    = el.get("Size", "")
        info["grade"]   = el.get("Grade", "")
        info["tags"]    = el.get("Tags", "")

        # Manufacturer
        mfr_uuid = el.get("Manufacturer", "")
        if mfr_uuid and mfr_uuid != "00000000-0000-0000-0000-000000000000":
            code = mfr_idx.get(mfr_uuid, "")
            info["mfr_code"] = code
            info["mfr"] = MFR_NAMES.get(code, code)

        # microSCU
        for sub in el.iter():
            v = sub.get("microSCU")
            if v:
                try:
                    info["micro_scu"] = int(v)
                except (ValueError, TypeError):
                    pass
                break

        # Name from Localization child
        for sub in el.iter():
            if "Localization" in sub.tag:
                k = sub.get("Name", "")
                if k and k.startswith("@") and k not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                    key = k[1:].lower()
                    val = loc_idx.get(key, "")
                    if val and "PLACEHOLDER" not in val.upper() and "UNINITIALIZED" not in val.upper():
                        info["name"] = val.replace("\\n", " ").strip()
                break
        break

    # Fallback name from SCItemPurchasableParams.displayName
    if not info["name"]:
        for el in root.iter():
            dn = el.get("displayName", "")
            if dn and dn.startswith("@") and dn not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                val = loc_idx.get(dn[1:].lower(), "")
                if val and "PLACEHOLDER" not in val.upper():
                    info["name"] = val.replace("\\n", " ").strip()
                    break

    info["display_cat"] = _display_category(info["type"], info["subtype"])
    return info


# ── Scanner ───────────────────────────────────────────────────────────────────
def scan_all_items(mfr_idx, loc_idx):
    seen_names = set()
    items = []

    for src_path, cat_hint, type_filter in SOURCES:
        if not src_path.exists():
            print(f"  WARNING: not found: {src_path}")
            continue
        for f in sorted(src_path.rglob("*.xml")):
            v = parse_item(f, cat_hint, mfr_idx, loc_idx)
            if not v:
                continue
            if _should_skip(f.stem, v["name"]):
                continue
            # Apply type filter for carryables
            if type_filter and v["type"] not in type_filter:
                continue
            # Deduplicate by name (skip identical-named duplicates)
            key = v["name"].lower().strip()
            if key and key in seen_names:
                continue
            if key:
                seen_names.add(key)
            items.append(v)

    return items


# ── HTML helpers ───────────────────────────────────────────────────────────────
CAT_COLORS = {
    "Medical / Stim": "#8e44ad",
    "Food & Drink":   "#27ae60",
    "Melee":          "#c0392b",
    "Throwable":      "#e67e22",
    "Deployable":     "#c0392b",
    "Tool / Gadget":  "#2980b9",
    "Misc":           "#546e7a",
    "Other":          "#546e7a",
}

def _cat_color(cat):
    return CAT_COLORS.get(cat, "#546e7a")

def _badge(text, color):
    if not text:
        return ""
    return f'<span class="badge" style="background:{color}">{text}</span>'

def _kv(k, v):
    if not v and v != 0:
        return ""
    return f'<span class="k">{k}</span><span class="v">{v}</span>'


def item_to_html(v):
    name    = v["name"] or v["file"]
    mfr     = v["mfr"] or v["mfr_code"] or "Unknown"
    dcat    = v["display_cat"]
    subtype = v["subtype"]
    tags    = v["tags"]

    cat_badge  = _badge(dcat, _cat_color(dcat))
    sub_text   = f" &middot; {subtype}" if subtype and subtype not in dcat else ""

    stats = ""
    if v["size"]:
        stats += _kv("Size", v["size"])
    if v["grade"]:
        stats += _kv("Grade", v["grade"])
    if v["micro_scu"]:
        stats += _kv("microSCU", f'{v["micro_scu"]:,}')
    if tags:
        # Show first 2 tags max
        tag_list = [t.strip() for t in tags.split() if t.strip()][:2]
        stats += _kv("Tags", " · ".join(tag_list))

    stats_html = (
        f'<div class="kv-grid">{stats}</div>'
    ) if stats else '<div class="no-stats">—</div>'

    cat_key = dcat.lower().replace(" ", "").replace("/", "")
    mfr_key = v["mfr_code"].lower() if v["mfr_code"] else "unknown"

    return (
        f'<div class="item-card" '
        f'data-cat="{cat_key}" data-mfr="{mfr_key}" data-name="{name.lower()}">\n'
        f'  <div class="card-header">\n'
        f'    <div class="card-title-row">'
        f'<span class="item-name">{name}</span>{cat_badge}</div>\n'
        f'    <div class="card-meta">{mfr}{sub_text}</div>\n'
        f'  </div>\n'
        f'  <div class="card-body">{stats_html}</div>\n'
        f'</div>'
    )


def generate_html(items):
    valid = [v for v in items if v and v["name"]]
    count = len(valid)
    cards = "\n".join(item_to_html(v) for v in valid)

    # Category tabs
    cat_counts = Counter(v["display_cat"] for v in valid)
    cat_tabs = (
        f'<button class="tab cat-tab active" data-cat="all" onclick="setCatTab(this)">'
        f'All <span class="tc">{count}</span></button>\n'
    )
    for cat in ["Medical / Stim", "Food & Drink", "Melee", "Throwable",
                "Deployable", "Tool / Gadget", "Misc", "Other"]:
        c = cat_counts.get(cat, 0)
        if not c:
            continue
        ckey  = cat.lower().replace(" ", "").replace("/", "")
        color = _cat_color(cat)
        cat_tabs += (
            f'<button class="tab cat-tab" data-cat="{ckey}" '
            f'style="--cc:{color}" onclick="setCatTab(this)">'
            f'{cat} <span class="tc">{c}</span></button>\n'
        )

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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SC Items Reference</title>
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
  .cat-tab.active {{ background:var(--cc,var(--accent)); border-color:var(--cc,var(--accent)); }}
  .tc {{ opacity:.7; font-weight:400; }}
  #search-box {{ background:var(--card); border:1px solid var(--border); border-radius:6px;
                 color:var(--text); font-size:.85rem; padding:6px 12px; width:220px; }}
  #search-box:focus {{ outline:none; border-color:var(--accent); }}
  #vis-count {{ color:var(--muted); font-size:.8rem; white-space:nowrap; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr));
           gap:12px; padding:18px 24px; }}
  .item-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px;
                overflow:hidden; transition:border-color .15s; }}
  .item-card:hover {{ border-color:var(--accent); }}
  .card-header {{ padding:10px 14px 8px; border-bottom:1px solid var(--border); }}
  .card-title-row {{ display:flex; align-items:flex-start; gap:6px; flex-wrap:wrap; margin-bottom:3px; }}
  .item-name {{ font-weight:600; font-size:.88rem; line-height:1.3; flex:1; min-width:0;
                overflow-wrap:break-word; }}
  .badge {{ font-size:.68rem; font-weight:700; border-radius:4px; padding:2px 6px;
            color:#fff; white-space:nowrap; align-self:flex-start; }}
  .card-meta {{ font-size:.73rem; color:var(--muted); }}
  .card-body {{ padding:8px 14px 10px; }}
  .kv-grid {{ display:grid; grid-template-columns:auto 1fr; gap:2px 14px; }}
  .k {{ font-size:.78rem; color:var(--muted); }}
  .v {{ font-size:.78rem; font-weight:500; }}
  .no-stats {{ font-size:.78rem; color:var(--muted); font-style:italic; }}
</style>
</head>
<body>
<header>
  <h1>Items Reference</h1>
  <div class="sub">Star Citizen &mdash; {count} items &middot; {GAME_VERSION}
    &middot; Consumables · Melee · Throwables · Deployables · Tools</div>
</header>
<div class="controls">
  <div class="filter-row">
    <span class="filter-label">Category</span>
    <div class="tabs">{cat_tabs}</div>
  </div>
  <div class="filter-row">
    <span class="filter-label">Maker</span>
    <div class="tabs">{mfr_tabs}</div>
  </div>
  <div class="filter-row">
    <span class="filter-label">Search</span>
    <input id="search-box" type="search" placeholder="item name...">
    <span id="vis-count"></span>
  </div>
</div>
<div class="grid" id="grid">
{cards}
</div>
<script>
var allCards = Array.from(document.querySelectorAll('.item-card'));
var activeCat = 'all', activeMfr = 'all', searchVal = '';
function setCatTab(btn) {{
  document.querySelectorAll('.cat-tab').forEach(function(b) {{ b.classList.remove('active'); }});
  btn.classList.add('active');
  activeCat = btn.dataset.cat;
  applyFilters();
}}
function setMfrTab(btn) {{
  document.querySelectorAll('.mfr-tab').forEach(function(b) {{ b.classList.remove('active'); }});
  btn.classList.add('active');
  activeMfr = btn.dataset.mfr;
  applyFilters();
}}
document.getElementById('search-box').addEventListener('input', function() {{
  searchVal = this.value.toLowerCase();
  applyFilters();
}});
function applyFilters() {{
  var vis = 0;
  allCards.forEach(function(c) {{
    var cat = activeCat === 'all' || c.dataset.cat === activeCat;
    var mfr = activeMfr === 'all' || c.dataset.mfr === activeMfr;
    var s   = !searchVal || c.dataset.name.indexOf(searchVal) !== -1;
    var show = cat && mfr && s;
    c.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById('vis-count').textContent =
    vis + ' item' + (vis !== 1 ? 's' : '');
}}
applyFilters();
</script>
</body>
</html>"""


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Items: loading indexes...")
    sys.stdout.flush()
    loc_idx = build_localization_index()
    mfr_idx = build_mfr_index()

    print("  Scanning item XMLs...")
    sys.stdout.flush()
    items = scan_all_items(mfr_idx, loc_idx)
    items.sort(key=lambda v: (v["display_cat"], v["name"].lower()))

    valid = [v for v in items if v["name"]]
    print(f"  {len(valid)} items (after dedup + name filter)")
    sys.stdout.flush()

    # Print category breakdown
    for cat, c in sorted(Counter(v["display_cat"] for v in valid).items()):
        print(f"    {cat}: {c}")
    sys.stdout.flush()

    out  = REPORTS_DIR / "items_preview.html"
    html = generate_html(items)
    out.write_text(html, encoding="utf-8")
    print(f"  Written: {out.name} ({len(html):,} bytes)")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
