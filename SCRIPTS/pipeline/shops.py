"""
shops.py -- Builds shop inventory HTML report + shops.json.

Reads Data/Scripts/ShopInventories/*.json (direct P4K files, not DataCore).
Cross-references item UUIDs with the DataCore UUID index to resolve class names
and display names, then outputs a searchable HTML report and shops.json.

Output schema (flat rows, one per shop x item):
  {shop_file, shop, location, class_name, name, category, buy_auec, sell_auec}

This is the join table for postgres: class_name links to ships/components/armor/
weapons/items/ground_vehicles tables.
"""

import sys
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import P4K_PATH, OUTPUT_DIR, REPORTS_DIR, GAME_VERSION

from pipeline.ships import build_uuid_index, build_localization_index
from pipeline.export_json import write_json, shops_to_records

RECORDS_DIR = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
SHOPINV_DIR = OUTPUT_DIR / "Data" / "Scripts" / "ShopInventories"
NULL_UUID   = "00000000-0000-0000-0000-000000000000"

# ── Shop name parsing ─────────────────────────────────────────────────────────

_CAMEL_RE = re.compile(
    r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-zA-Z])(?=[0-9])'
)

_LOC_OVERRIDES = {
    "area18":      "Area 18",
    "a18":         "Area 18",
    "portolisar":  "Port Olisar",
    "newbabbage":  "New Babbage",
    "grimhex":     "GrimHex",
    "lorville":    "Lorville",
    "levski":      "Levski",
    "reststop":    "Rest Stop",
    "truckstop":   "Truckstop",
}

def _camel_split(s: str) -> str:
    """GarrityDefense -> Garrity Defense,  Area18 -> Area 18"""
    return _CAMEL_RE.sub(' ', s)


def _parse_shop_filename(stem: str):
    """
    Return (shop_display_name, location_display_name) from filename stem.

    Patterns handled:
      Inv_GarrityDefense_PortOlisar          -> ("Garrity Defense", "Port Olisar")
      Inv_TammanyAndSons_Food_Lorville       -> ("Tammany And Sons Food", "Lorville")
      Inv_ShipWeapons_Centermass_Area18      -> ("Ship Weapons Centermass", "Area 18")
      Inv_LandingServices_rs_full_0001       -> ("Landing Services", "Rest Stop 0001")
      Inv_LiveFireWeapons_lt_a_small_base_b  -> ("Live Fire Weapons", "Small Base B")
      Inv_Admin_Small_Base_A                 -> ("Admin", "Small Base A")
      AnniversarySale_Day01_ANVL_2019        -> ("Anniversary Sale Day 01 ANVL 2019", "Event")
    """
    name = stem
    if name.startswith("Inv_"):
        name = name[4:]
    else:
        return _camel_split(name.replace("_", " ")), "Event"

    # Rest stop: *_rs_full_NNNN
    rs_match = re.search(r'_rs_full_(\d+)', name)
    if rs_match:
        num = rs_match.group(1)
        shop_raw = name[:name.find("_rs_")]
        shop = " ".join(_camel_split(p) for p in shop_raw.split("_"))
        return shop, f"Rest Stop {num}"

    # Small base outpost: *_lt_a_small_base_X  OR  *_Small_Base_X
    base_match = re.search(r'(?:_lt_a)?_[Ss]mall_[Bb]ase_([A-Za-z])', name)
    if base_match:
        letter = base_match.group(1).upper()
        shop_raw = name[:base_match.start()]
        shop = " ".join(_camel_split(p) for p in shop_raw.split("_") if p.lower() not in ("lt", "a"))
        return shop.strip(), f"Small Base {letter}"

    # Truckstop base variant: *_Truckstop_Base_X
    truck_match = re.search(r'_[Tt]ruckstop_[Bb]ase_([A-Za-z])', name)
    if truck_match:
        letter = truck_match.group(1).upper()
        shop_raw = name[:truck_match.start()]
        shop = " ".join(_camel_split(p) for p in shop_raw.split("_"))
        return shop.strip(), f"Truckstop Base {letter}"

    # Rest stop small variant: *_Reststop_Small_X  (no "Base" in name)
    rs_small_match = re.search(r'_[Rr]eststop_[Ss]mall_([A-Za-z])', name)
    if rs_small_match:
        letter = rs_small_match.group(1).upper()
        shop_raw = name[:rs_small_match.start()]
        shop = " ".join(_camel_split(p) for p in shop_raw.split("_"))
        return shop.strip(), f"Rest Stop Small {letter}"

    # Default: last underscore-part = location, rest = shop
    parts = name.split("_")
    loc_raw = parts[-1].lower()
    location = _LOC_OVERRIDES.get(loc_raw, _camel_split(parts[-1]))
    shop_parts = parts[:-1]
    if not shop_parts:
        return _camel_split(parts[-1]), "Unknown"
    shop = " ".join(_camel_split(p) for p in shop_parts)
    return shop, location


# ── Category from XML path ────────────────────────────────────────────────────

def _category_from_path(path: Path) -> str:
    p = str(path).lower().replace("\\", "/")
    if "/entities/spaceships/"       in p: return "Ship"
    if "/entities/groundvehicles/"   in p: return "Vehicle"
    if "/scitem/ships/"              in p: return "Ship Component"
    if "/weapons/ship/"              in p: return "Ship Weapon"
    if "/weapons/fps_modifiers/"     in p: return "Weapon Attachment"
    if "/weapons/fps/"               in p: return "FPS Weapon"
    if "/weapons/melee/"             in p: return "Melee Weapon"
    if "/weapons/throwable/"         in p: return "Throwable"
    if "/armor/pu_armor/"            in p: return "Armor"
    if "/starwear/helmet/"           in p: return "Helmet"
    if "/characters/human/clothing/" in p: return "Clothing"
    if "/consumables/"               in p: return "Consumable"
    if "/fps_devices/"               in p: return "Tool / Device"
    if "/carryables/"                in p: return "Carryable"
    if "/scitem/"                    in p: return "Item"
    return "Other"


# ── Name resolver ─────────────────────────────────────────────────────────────

def _resolve_name(xml_path: Path, loc_idx: dict) -> str:
    """Parse XML and resolve display name from localization index."""
    if not xml_path or not xml_path.exists():
        return ""
    try:
        root = ET.parse(str(xml_path)).getroot()
        for elem in root.iter():
            tag = elem.tag
            if "Localization" in tag:
                n = elem.get("Name", "")
                if n and n.startswith("@") and n != "@LOC_UNINITIALIZED":
                    return loc_idx.get(n[1:].lower(), "")
            for attr in ("displayName", "vehicleName"):
                v = elem.get(attr, "")
                if v and v.startswith("@") and v != "@LOC_UNINITIALIZED":
                    return loc_idx.get(v[1:].lower(), "")
    except Exception:
        pass
    return ""


# ── P4K extraction (inline fallback if extractor.py hasn't run it yet) ────────

def _ensure_shop_inventories():
    """Extract ShopInventories from P4K if not already present in Data_Extraction/."""
    existing = list(SHOPINV_DIR.glob("*.json")) if SHOPINV_DIR.exists() else []
    if existing:
        print(f"ShopInventories: {len(existing)} files cached")
        sys.stdout.flush()
        return

    print("ShopInventories not yet extracted — pulling from P4K (fast, ~1 MB)...")
    sys.stdout.flush()
    try:
        from scdatatools.sc import StarCitizen
    except ImportError:
        print("ERROR: scdatatools not installed. Run runner.py to set up the environment.")
        sys.exit(1)

    sc = StarCitizen(P4K_PATH.parent)
    shop_files = [
        f for f in sc.p4k.filelist
        if "Scripts/ShopInventories" in f.filename
        and not f.filename.endswith("/")
    ]
    print(f"  Found {len(shop_files)} files in P4K")
    sys.stdout.flush()

    SHOPINV_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0
    for info in shop_files:
        try:
            sc.p4k._extract_member(info, OUTPUT_DIR)
        except Exception as e:
            errors += 1
            print(f"  ERROR extracting {info.filename}: {e}")

    extracted = len(list(SHOPINV_DIR.glob("*.json")))
    print(f"  Extracted {extracted} files ({errors} errors)")
    sys.stdout.flush()


# ── Data builder ──────────────────────────────────────────────────────────────

def build_shop_data(uuid_idx: dict, loc_idx: dict) -> list:
    """
    Parse all ShopInventory JSON files.
    Returns flat list of dicts with shop, location, class_name, name, category, prices.
    """
    rows = []
    json_files = sorted(SHOPINV_DIR.glob("*.json"))
    print(f"Parsing {len(json_files)} shop files...")
    sys.stdout.flush()

    unresolved = 0
    empty = 0

    for json_path in json_files:
        stem = json_path.stem
        shop, location = _parse_shop_filename(stem)

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        inventory = data.get("Collection", {}).get("Inventory", [])
        if not inventory:
            empty += 1
            continue

        for entry in inventory:
            ids = entry.get("ID", {}).get("ID", [])
            if not ids:
                continue
            uuid = ids[0]
            buy  = round(entry.get("BuyPrice",  0))
            sell = round(entry.get("SellPrice", 0))

            uuid_entry = uuid_idx.get(uuid)
            if uuid_entry:
                xml_path   = uuid_entry["path"]
                class_name = xml_path.stem
                name       = _resolve_name(xml_path, loc_idx) or class_name
                category   = _category_from_path(xml_path)
            else:
                unresolved += 1
                continue  # skip commodity/resource UUIDs not in DataCore extraction

            rows.append({
                "shop_file":  stem,
                "shop":       shop,
                "location":   location,
                "class_name": class_name,
                "name":       name,
                "category":   category,
                "buy_auec":   buy,
                "sell_auec":  sell,
            })

    print(f"  {len(rows):,} entries — {unresolved} unresolved UUIDs, {empty} empty shops")
    sys.stdout.flush()
    return rows


# ── HTML generation ───────────────────────────────────────────────────────────

def _build_html(rows: list) -> str:
    from collections import Counter
    locations  = sorted({r["location"]  for r in rows})
    categories = sorted({r["category"]  for r in rows})
    shops_list = sorted({r["shop"]      for r in rows})
    cat_counts = Counter(r["category"]  for r in rows)
    loc_counts = Counter(r["location"]  for r in rows)

    loc_opts  = "\n".join(
        f'<option value="{l}">{l} ({loc_counts[l]:,})</option>' for l in locations
    )
    cat_opts  = "\n".join(
        f'<option value="{c}">{c} ({cat_counts[c]:,})</option>' for c in categories
    )

    # Build table rows
    trs = []
    for r in rows:
        buy  = f"{r['buy_auec']:,}"  if r["buy_auec"]  else "—"
        sell = f"{r['sell_auec']:,}" if r["sell_auec"] else "—"
        cn   = r["class_name"] or ""
        trs.append(
            f'<tr data-loc="{r["location"]}" data-cat="{r["category"]}" '
            f'data-shop="{r["shop"]}">'
            f'<td>{r["shop"]}</td>'
            f'<td>{r["location"]}</td>'
            f'<td>{r["name"] or cn}</td>'
            f'<td><span class="badge cat-{r["category"].lower().replace(" ", "-").replace("/", "")}">'
            f'{r["category"]}</span></td>'
            f'<td class="num">{buy}</td>'
            f'<td class="num">{sell}</td>'
            f'<td class="cls">{cn}</td>'
            f'</tr>'
        )
    rows_html = "\n".join(trs)

    total_shops = len(shops_list)
    total_items = len({r["class_name"] for r in rows if r["class_name"]})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SC DataPack — Shop Inventories</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #1a1a1a; color: #e0e0e0; font: 14px/1.4 'Segoe UI', sans-serif; }}
header {{ background: #111; border-bottom: 1px solid #333; padding: 14px 20px; position: sticky; top: 0; z-index: 10; }}
header h1 {{ font-size: 1.2rem; color: #c8b08a; display: inline; }}
header .sub {{ color: #888; font-size: .85rem; margin-left 8px; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 20px; background: #222; border-bottom: 1px solid #333; }}
.controls input, .controls select {{
  background: #2a2a2a; border: 1px solid #444; border-radius: 4px;
  color: #e0e0e0; padding: 5px 10px; font-size: .85rem;
}}
.controls input {{ width: 240px; }}
.controls select {{ min-width: 160px; }}
.controls label {{ color: #aaa; font-size: .8rem; align-self: center; }}
#count {{ color: #888; font-size: .8rem; align-self: center; margin-left: auto; }}
.wrap {{ overflow-x: auto; padding: 0 0 40px; }}
table {{ width: 100%; border-collapse: collapse; font-size: .82rem; }}
thead th {{
  background: #111; color: #c8b08a; text-align: left;
  padding: 8px 10px; border-bottom: 2px solid #444;
  position: sticky; top: 52px; cursor: pointer; user-select: none;
}}
thead th:hover {{ color: #e0c898; }}
thead th.sorted-asc::after  {{ content: ' ↑'; }}
thead th.sorted-desc::after {{ content: ' ↓'; }}
tbody tr {{ border-bottom: 1px solid #2a2a2a; }}
tbody tr:hover {{ background: #222; }}
td {{ padding: 6px 10px; vertical-align: middle; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; color: #b0d0a0; }}
td.cls {{ font-family: monospace; font-size: .75rem; color: #777; }}
.badge {{
  display: inline-block; padding: 2px 7px; border-radius: 10px;
  font-size: .72rem; font-weight: 600; letter-spacing: .03em;
}}
.badge.cat-ship             {{ background: #1a3a5a; color: #70b0e0; }}
.badge.cat-vehicle          {{ background: #2a2a1a; color: #c0b060; }}
.badge.cat-shipcomponent    {{ background: #1a2a3a; color: #60a0c0; }}
.badge.cat-shipweapon       {{ background: #2a1a3a; color: #a070c0; }}
.badge.cat-fpsweapon        {{ background: #3a1a1a; color: #e07070; }}
.badge.cat-weaponattachment {{ background: #3a2a1a; color: #c09060; }}
.badge.cat-armor            {{ background: #1a3a2a; color: #60c090; }}
.badge.cat-helmet           {{ background: #1a3a2a; color: #60c090; }}
.badge.cat-clothing         {{ background: #3a1a3a; color: #c060c0; }}
.badge.cat-consumable       {{ background: #2a3a1a; color: #a0c060; }}
.badge.cat-tool/device, .badge.cat-tooldevice {{ background: #2a3a3a; color: #60c0c0; }}
.badge.cat-carryable        {{ background: #3a3a1a; color: #c0c060; }}
.badge.cat-meleweapon, .badge.cat-meleeweapon {{ background: #3a1a1a; color: #e07070; }}
.badge.cat-throwable        {{ background: #3a2a1a; color: #e09060; }}
.badge.cat-unknown          {{ background: #2a2a2a; color: #777; }}
.badge.cat-item             {{ background: #2a2a2a; color: #aaa; }}
.badge.cat-other            {{ background: #2a2a2a; color: #666; }}
footer {{ text-align: center; color: #555; font-size: .78rem; padding: 16px; }}
</style>
</head>
<body>
<header>
  <h1>SC DataPack &mdash; Shop Inventories</h1>
  <span class="sub">&nbsp;&nbsp;{GAME_VERSION} &mdash; {total_shops:,} shops &mdash; {total_items:,} unique items &mdash; {len(rows):,} inventory entries</span>
</header>
<div class="controls">
  <label>Location</label>
  <select id="fLoc">
    <option value="">All locations</option>
    {loc_opts}
  </select>
  <label>Category</label>
  <select id="fCat">
    <option value="">All categories</option>
    {cat_opts}
  </select>
  <label>Search</label>
  <input id="fSearch" type="search" placeholder="shop, item, class name...">
  <span id="count"></span>
</div>
<div class="wrap">
<table id="tbl">
<thead>
<tr>
  <th onclick="sortBy(0)">Shop</th>
  <th onclick="sortBy(1)">Location</th>
  <th onclick="sortBy(2)">Item</th>
  <th onclick="sortBy(3)">Category</th>
  <th onclick="sortBy(4)">Buy (aUEC)</th>
  <th onclick="sortBy(5)">Sell (aUEC)</th>
  <th onclick="sortBy(6)">class_name</th>
</tr>
</thead>
<tbody id="tbody">
{rows_html}
</tbody>
</table>
</div>
<footer>SC DataPack &mdash; {GAME_VERSION} &mdash; shops.json available in reports/JSON/</footer>
<script>
const tbody = document.getElementById('tbody');
const allRows = Array.from(tbody.querySelectorAll('tr'));
const fLoc = document.getElementById('fLoc');
const fCat = document.getElementById('fCat');
const fSearch = document.getElementById('fSearch');
const countEl = document.getElementById('count');
let sortCol = -1, sortAsc = true;

function applyFilters() {{
  const loc = fLoc.value;
  const cat = fCat.value;
  const q   = fSearch.value.toLowerCase();
  let vis = 0;
  allRows.forEach(r => {{
    const show = (!loc || r.dataset.loc === loc)
              && (!cat || r.dataset.cat === cat)
              && (!q   || r.textContent.toLowerCase().includes(q));
    r.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  countEl.textContent = vis.toLocaleString() + ' rows';
}}

function sortBy(col) {{
  const ths = document.querySelectorAll('thead th');
  ths.forEach((th, i) => th.className = i === col ? (sortAsc ? 'sorted-asc' : 'sorted-desc') : '');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const isNum = col >= 4 && col <= 5;
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.replace(/,/g,'').trim() || '';
    const bv = b.cells[col]?.textContent.replace(/,/g,'').trim() || '';
    if (isNum) {{
      const an = parseFloat(av) || 0, bn = parseFloat(bv) || 0;
      return sortAsc ? an - bn : bn - an;
    }}
    return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
  if (sortCol === col) sortAsc = !sortAsc; else {{ sortCol = col; sortAsc = true; }}
  applyFilters();
}}

fLoc.addEventListener('change', applyFilters);
fCat.addEventListener('change', applyFilters);
fSearch.addEventListener('input', applyFilters);
applyFilters();
</script>
</body>
</html>"""


# ── Runner ────────────────────────────────────────────────────────────────────

def run():
    import time
    t0 = time.time()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_html = REPORTS_DIR / "shops.html"

    print("=== Shops ===")
    sys.stdout.flush()

    # Ensure ShopInventories are on disk
    _ensure_shop_inventories()

    # Build indexes
    print("Building localization index...")
    sys.stdout.flush()
    loc_idx = build_localization_index()

    print("Building UUID index...")
    sys.stdout.flush()
    uuid_idx = build_uuid_index()

    # Build data
    rows = build_shop_data(uuid_idx, loc_idx)

    # HTML
    html = _build_html(rows)
    out_html.write_text(html, encoding="utf-8")
    print(f"HTML: {out_html} ({len(html)//1024}KB)")
    sys.stdout.flush()

    # JSON
    records   = shops_to_records(rows)
    shops_set = {r["shop_file"] for r in rows}
    items_set = {r["class_name"] for r in rows if r["class_name"]}
    out_json  = write_json(records, "shops.json", extra_meta={
        "shops":        len(shops_set),
        "unique_items": len(items_set),
    })
    print(f"JSON: {out_json} ({out_json.stat().st_size//1024}KB)")
    sys.stdout.flush()

    print(f"Done in {time.time()-t0:.0f}s")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
