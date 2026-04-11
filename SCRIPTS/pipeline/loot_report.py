"""Loot report — loot tables by location type, archetypes resolved to slot names."""
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION, REPORTS_DIR

DATA_BASE = Path(os.environ.get("SC_DATA_BASE", str(REPO_ROOT / "EXPLORER_Data")))

BASE_LOOT = DATA_BASE / "Data" / "Libs" / "foundry" / "records" / "lootgeneration"
LOC       = DATA_BASE / "Data" / "Localization" / "english" / "global.ini"
OUTPUT    = REPORTS_DIR / "loot_report.html"

# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------
def load_loc(path):
    loc = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.split(",")[0].strip().lstrip("@")
            loc[key.lower()] = val.strip()
    return loc

LOC_DATA = load_loc(LOC)
def loc(key):
    k = key.lstrip("@").lower()
    return LOC_DATA.get(k, key)

# ---------------------------------------------------------------------------
# Build archetype UUID -> name map
# ---------------------------------------------------------------------------
archetypes = {}  # id -> {name, entries}

for f in sorted((BASE_LOOT / "lootarchetypes").glob("*.xml")):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue
    aid = root.get("__id", "")
    if not aid:
        continue
    # Name from filename
    name = f.stem.replace("lootarchetype_", "").replace("_", " ").title()
    entries = []
    for entry in root.iter("LootArchetypeEntry_Primary"):
        ename = entry.get("name", "")
        weight = float(entry.get("weight", 1.0))
        # Try to resolve name from loc
        if ename and not ename.startswith("0") and len(ename) > 5 and "-" not in ename:
            entries.append({"name": ename, "weight": weight})
        else:
            entries.append({"name": name, "weight": weight})
    archetypes[aid] = {"name": name, "entries": entries}

# ---------------------------------------------------------------------------
# Build loot table UUID -> name + archetype refs
# ---------------------------------------------------------------------------
def parse_loot_table(f):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        return None
    tid = root.get("__id", "")
    name = f.stem.replace("_", " ").title()
    archs = []
    for wa in root.iter("WeightedLootArchetype"):
        arch_id = wa.get("archetype", "")
        weight  = float(wa.get("weight", 1.0))
        nr_max  = wa.find(".//numberOfResultsConstraints")
        max_r   = int(nr_max.get("maxResults", 0)) if nr_max is not None else 0
        archs.append({"id": arch_id, "weight": round(weight, 3), "max": max_r})
    return {"id": tid, "name": name, "archetypes": archs}

loot_tables = {}  # id -> table dict
for f in sorted((BASE_LOOT / "loottables").rglob("*.xml")):
    t = parse_loot_table(f)
    if t:
        loot_tables[t["id"]] = t

# Also index by filename stem for direct lookup
loot_by_name = {}
for f in sorted((BASE_LOOT / "loottables").rglob("*.xml")):
    t = parse_loot_table(f)
    if t:
        loot_by_name[f.stem.lower()] = t

# ---------------------------------------------------------------------------
# Location categories — map folder/name patterns to readable locations
# ---------------------------------------------------------------------------
LOCATION_GROUPS = {
    "UGF / Bunker":         ["ugf"],
    "Distribution Center":  ["distributioncenters", "dc_common", "dc_rare", "dc_uncommon"],
    "Derelict":             ["derelict"],
    "Contested Zone":       ["contestedzone", "loottable_b"],
    "Animals / NPC":        ["animals", "kopion", "npc"],
    "Armour Containers":    ["container_armour", "container_clothing", "container_undersuit"],
    "Weapons Containers":   ["container_weapons", "firepower"],
    "Medical Containers":   ["container_medical", "medical"],
    "Mining Containers":    ["container_mining", "v3loottable_mining", "miningderelict"],
    "Food & Harvestables":  ["container_food", "harvestable", "v3loottable_food", "v3loottable_harvestables"],
    "Generic Containers":   ["container_large_generic", "container_medium_generic", "container_small_generic",
                             "container_personal", "container_repair", "v3loottable_generic", "v3loottable_personal",
                             "v3loottable_repair"],
    "Actor / Event Drops":  ["v3loottable_actor", "v3loottable_event", "v3loottable_armour",
                             "v3loottable_weapons", "loottable_actor", "v3loottable_kaboos"],
    "General / Misc":       ["generalloot", "survival", "salvage", "scrap", "ammo", "armor",
                             "tools", "drugs", "prison", "military", "securityoutpost",
                             "antiquesandstuff", "contrabandpico", "v3loottable_medical"],
}

def get_location_group(stem):
    sl = stem.lower()
    # Also check parent folder name passed via f.parent.name
    for group, patterns in LOCATION_GROUPS.items():
        if any(p in sl for p in patterns):
            return group
    return "General / Misc"

def _infer_rarity(stem):
    sl = stem.lower()
    for r in ["legendary", "epic", "rare", "uncommon", "common"]:
        if r in sl: return r.title()
    return ""

tables_by_location = defaultdict(list)
for f in sorted((BASE_LOOT / "loottables").rglob("*.xml")):
    t = parse_loot_table(f)
    if not t: continue
    t["file"] = f.stem
    sl = f.stem.lower()
    for r in ["legendary","epic","rare","uncommon","common"]:
        if r in sl:
            t["rarity"] = r.title()
            break
    else:
        t["rarity"] = ""
    group = get_location_group(f.stem)
    tables_by_location[group].append(t)

# ---------------------------------------------------------------------------
# Resolve archetype IDs to human-readable names
# ---------------------------------------------------------------------------
def resolve_archetype(aid):
    arch = archetypes.get(aid)
    if not arch:
        return aid[:8] + "..."
    entries = arch["entries"]
    if entries:
        names = list({e["name"] for e in entries})
        return ", ".join(sorted(names)[:3]) + (" ..." if len(names) > 3 else "")
    return arch["name"]

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
RARITY_COLORS = {
    "Common": "#7A7A8A", "Uncommon": "#4ade9a", "Rare": "#8B6FE8",
    "Epic": "#a371f7", "Legendary": "#f0c040", "":" #4A4A5A",
}
GROUP_COLORS = {
    "UGF / Bunker": "#e85454",
    "Distribution Center": "#8B6FE8",
    "Derelict": "#9b77cf",
    "Contested Zone": "#e8a838",
    "Animals": "#54c87a",
    "Other": "#7A7A8A",
}

def rarity_badge(r):
    c = RARITY_COLORS.get(r, "#4A4A5A")
    if not r: return ""
    return f'<span style="background:{c}22;color:{c};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{r}</span>'

tab_buttons = ""
tab_panels  = ""
total_tables = sum(len(v) for v in tables_by_location.values())

for i, (group, tables) in enumerate(sorted(tables_by_location.items())):
    gcolor = GROUP_COLORS.get(group, "#7A7A8A")
    active = "active" if i == 0 else ""
    gid    = group.replace(" ", "_").replace("/", "")
    tab_buttons += f'<div class="tab {active}" onclick="showTab(\'{gid}\',this)">{group} ({len(tables)})</div>'

    rows = ""
    for t in sorted(tables, key=lambda x: x["file"]):
        arch_cells = ""
        for a in t["archetypes"]:
            resolved = resolve_archetype(a["id"])
            max_txt  = f' x{a["max"]}' if a["max"] else ""
            arch_cells += (
                f'<div style="margin:2px 0;font-size:12px">'
                f'<span style="color:#7A7A8A">{a["weight"]:.2f}</span> '
                f'<span style="color:#CCCCCC">{resolved}</span>'
                f'<span style="color:#7A7A8A">{max_txt}</span>'
                f'</div>'
            )
        rows += (
            f'<tr>'
            f'<td><strong>{t["name"]}</strong><br><span style="color:#4A4A5A;font-size:11px;font-family:Geist Mono,monospace">{t["file"]}</span></td>'
            f'<td>{rarity_badge(t["rarity"])}</td>'
            f'<td>{arch_cells or "<span style=color:#4A4A5A>—</span>"}</td>'
            f'</tr>'
        )

    tab_panels += f"""<div id="tab_{gid}" class="panel {active}">
      <div class="card-table">
        <table>
          <thead><tr>
            <th style="width:220px">Loot Table</th>
            <th style="width:100px">Rarity</th>
            <th>Archetype Entries (weight &bull; contents)</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>"""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC Loot Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%}}
body{{background:#13141A;color:#CCCCCC;font-family:'Outfit',sans-serif;font-size:14px;display:flex;flex-direction:column;min-height:100vh}}
.site-bar{{background:linear-gradient(to right,#1A1C26 0%,#15171D 100%);border-bottom:1px solid #3A3F56;height:52px;padding:0 32px;display:flex;align-items:center;gap:0;position:sticky;top:0;z-index:100;flex-shrink:0}}
.site-logo{{font-weight:800;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#FFFFFF;display:flex;align-items:center;gap:8px;flex-shrink:0}}
.site-logo::before{{content:'';display:block;width:8px;height:8px;background:#532CD8;border-radius:2px;transform:rotate(45deg)}}
.site-nav{{display:flex;gap:2px;margin-left:24px;flex:1}}
.site-nav a{{color:#7A7A8A;text-decoration:none;font-size:12px;font-weight:500;padding:5px 12px;border-radius:6px;transition:all .15s;white-space:nowrap}}
.site-nav a:hover{{color:#FFFFFF;background:rgba(255,255,255,.06)}}
.site-nav a.cur{{color:#FFFFFF;background:#532CD8}}
.site-ver{{font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#4A4A5A;font-family:'Geist Mono',monospace;flex-shrink:0}}
.page-header{{background:#15171D;border-bottom:1px solid #3A3F56;padding:22px 40px 18px;flex-shrink:0}}
.page-header h1{{font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-.01em}}
.page-header .sub{{color:#7A7A8A;font-size:13px;margin-top:4px}}
.note{{background:rgba(35,38,52,.8);border:1px solid #3A3F56;border-radius:8px;padding:12px 16px;margin-top:14px;font-size:12px;color:#7A7A8A;line-height:1.6}}
.tabs{{display:flex;border-bottom:1px solid #3A3F56;background:#15171D;padding:0 40px;overflow-x:auto;flex-shrink:0}}
.tab{{padding:11px 18px;cursor:pointer;color:#7A7A8A;font-size:13px;font-weight:500;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s;user-select:none}}
.tab:hover{{color:#FFFFFF}}
.tab.active{{color:#FFFFFF;border-bottom-color:#532CD8}}
.container{{max-width:1300px;margin:0 auto;padding:24px 40px;flex:1}}
.panel{{display:none}}.panel.active{{display:block}}
.card-table{{background:linear-gradient(168deg,#232634 0%,#191B25 77%);outline:0.5px solid #14141A;box-shadow:inset 0px 0.5px 0px #2B2E3B;border:1px solid #3A3F56;border-radius:10px;overflow:hidden;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse}}
table th{{background:rgba(21,23,29,.9);color:#7A7A8A;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:8px 14px;border-bottom:1px solid #3A3F56;text-align:left}}
table td{{padding:10px 14px;border-bottom:1px solid #252D3E;vertical-align:top}}
table tr:last-child td{{border-bottom:none}}
table tr:hover td{{background:rgba(35,38,52,.6)}}
</style>
</head>
<body>
<div class="site-bar">
  <div class="site-logo">Saladins Information</div>
  <nav class="site-nav">
    <a href="crafting_report.html">Crafting</a>
    <a href="mining_report.html">Mining</a>
    <a href="loot_report.html" class="cur">Loot Tables</a>
    <a href="crafting_calculator.html">Calculator</a>
  </nav>
  <div class="site-ver">SC {GAME_VERSION}</div>
</div>
<div class="page-header">
  <h1>Loot Tables Report</h1>
  <div class="sub">{total_tables} loot tables &bull; {len(archetypes)} archetypes resolved</div>
  <div class="note">
    <strong style="color:#f5a742">Note:</strong> Loot archetypes use a tag-based system — items are matched by UUID tags, not direct item references.
    Archetype names show the slot category (e.g. "Pistol Ammunition", "Scrip Merc"). Full item-level resolution requires
    tracing item tags through the EntityClassDefinition records.
  </div>
</div>
<div class="tabs">{tab_buttons}</div>
<div class="container">{tab_panels}</div>
<script>
function showTab(id,btn){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>{{t.classList.remove('active');t.style.borderBottomColor='';}});
  document.getElementById('tab_'+id).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"Written: {OUTPUT}")
print(f"Total loot tables: {total_tables}")
print(f"Total archetypes: {len(archetypes)}")
for group, tables in sorted(tables_by_location.items()):
    print(f"  {group}: {len(tables)} tables")

# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------
from pipeline.export_json import write_json

json_records = []
for group, tables in sorted(tables_by_location.items()):
    for t in tables:
        resolved_archs = []
        for arch_ref in t.get("archetypes", []):
            arch = archetypes.get(arch_ref["id"], {})
            resolved_archs.append({
                "name":       arch.get("name", arch_ref["id"][:8]),
                "weight":     arch_ref["weight"],
                "max_results":arch_ref["max"],
            })
        json_records.append({
            "file":       t["file"],
            "name":       t["name"],
            "category":   group,
            "rarity":     t.get("rarity", ""),
            "archetypes": resolved_archs,
        })

json_out = write_json(json_records, "loot_tables.json", extra_meta={
    "archetype_count": len(archetypes),
})
print(f"JSON   -> {json_out}  ({json_out.stat().st_size:,} bytes)")
