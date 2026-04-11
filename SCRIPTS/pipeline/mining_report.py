"""Mining report — mineable elements, rock compositions, FPS minables, location data."""
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION, REPORTS_DIR

DATA_BASE = Path(os.environ.get("SC_DATA_BASE", str(REPO_ROOT / "EXPLORER_Data")))

BASE   = DATA_BASE / "Data" / "Libs" / "foundry" / "records" / "mining"
LOC    = DATA_BASE / "Data" / "Localization" / "english" / "global.ini"
OUTPUT = REPORTS_DIR / "mining_report.html"

# ---------------------------------------------------------------------------
# Localization helpers
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

def clean_name(raw):
    """Turn a filename or loc key into a readable name."""
    raw = raw.lstrip("@")
    raw = re.sub(r"items_commodities_|minableelement_fps_|minableelement_groundvehicle_|minableelement_ship_", "", raw, flags=re.I)
    raw = raw.replace("_raw", "").replace("_ore", "").replace("_deposit", "").replace("_", " ")
    return raw.strip().title()

# ---------------------------------------------------------------------------
# Parse mineable elements
# ---------------------------------------------------------------------------
def parse_element(f):
    root = ET.parse(f).getroot()
    attrs = root.attrib
    name_raw = attrs.get("__type", f.stem)
    # Try localization via depositName (not on elements, just use filename)
    name = clean_name(f.stem.replace("minableelement_fps_", "").replace("minableelement_groundvehicle_", ""))
    # Determine type from path
    if "fps" in f.stem:
        kind = "FPS"
    elif "groundvehicle" in f.stem:
        kind = "Vehicle"
    elif "template" in f.stem or "test" in f.stem:
        return None
    else:
        kind = "Ship"

    return {
        "id":          attrs.get("__id", ""),
        "name":        name,
        "kind":        kind,
        "resistance":  round(float(attrs.get("elementResistance", 0)), 3),
        "instability": round(float(attrs.get("elementInstability", 0)), 1),
        "explosion":   round(float(attrs.get("elementExplosionMultiplier", 1)), 1),
        "optimal_mid": round(float(attrs.get("elementOptimalWindowMidpoint", 0.5)), 2),
        "optimal_thin":round(float(attrs.get("elementOptimalWindowThinness", 2)), 2),
    }

elements = {}  # id -> element dict
for f in sorted((BASE / "mineableelements").glob("*.xml")):
    e = parse_element(f)
    if e:
        elements[e["id"]] = e

# ---------------------------------------------------------------------------
# Parse rock composition presets
# ---------------------------------------------------------------------------
def parse_composition(f, rock_type):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        return None
    attrs = root.attrib
    deposit_name_raw = attrs.get("depositName", f.stem)
    name = loc(deposit_name_raw) if deposit_name_raw.startswith("@") else clean_name(f.stem)
    min_elements = int(attrs.get("minimumDistinctElements", 1))

    parts = []
    for part in root.iter("MineableCompositionPart"):
        eid = part.get("mineableElement", "")
        el  = elements.get(eid)
        el_name = el["name"] if el else eid[:8]
        parts.append({
            "element":     el_name,
            "min_pct":     round(float(part.get("minPercentage", 0)), 1),
            "max_pct":     round(float(part.get("maxPercentage", 0)), 1),
            "probability": round(float(part.get("probability", 1)), 2),
            "quality":     round(float(part.get("qualityScale", 1)), 2),
        })
    if not parts:
        return None
    return {
        "name":      name,
        "rock_type": rock_type,
        "min_dist":  min_elements,
        "parts":     parts,
    }

rock_compositions = {
    "Asteroid (Ship)": [],
    "Surface (Ship)":  [],
    "FPS Deposit":     [],
    "Vehicle Deposit": [],
    "Surface Deposit": [],
}

for f in sorted((BASE / "rockcompositionpresets/asteroidshipmining").glob("*.xml")):
    if "template" in f.stem: continue
    c = parse_composition(f, "Asteroid (Ship)")
    if c: rock_compositions["Asteroid (Ship)"].append(c)

for f in sorted((BASE / "rockcompositionpresets/surfaceshipmining").glob("*.xml")):
    if "template" in f.stem: continue
    c = parse_composition(f, "Surface (Ship)")
    if c: rock_compositions["Surface (Ship)"].append(c)

for f in sorted((BASE / "rockcompositionpresets").glob("fps_composition_*.xml")):
    if "template" in f.stem: continue
    c = parse_composition(f, "FPS Deposit")
    if c: rock_compositions["FPS Deposit"].append(c)

for f in sorted((BASE / "rockcompositionpresets").glob("groundvehicle_composition_*.xml")):
    if "template" in f.stem: continue
    c = parse_composition(f, "Vehicle Deposit")
    if c: rock_compositions["Vehicle Deposit"].append(c)

# ---------------------------------------------------------------------------
# Extract location guide from localization (Journal entry + planet descriptions)
# ---------------------------------------------------------------------------
journal_raw = LOC_DATA.get("journal_general_mining_compendium_content", "")
location_guide = {}  # element_name -> locations string
if journal_raw:
    # Parse the journal: lines like "Quantainium - Found in All Deposits (Rare)"
    for line in journal_raw.replace("\\n", "\n").splitlines():
        line = line.strip()
        if " - " in line:
            el, _, locs = line.partition(" - ")
            location_guide[el.strip().lower()] = locs.strip()

# Planet/moon descriptions
planet_mineables = {}  # body_name -> {ship: [], hand: [], harvestable: []}
for key, val in LOC_DATA.items():
    if key.startswith("stanton") and "_desc" in key:
        body = key.replace("_desc", "").replace("stanton", "Stanton").upper()
        val_clean = val.replace("\\n", "\n")
        ship, hand = [], []
        section = None
        for line in val_clean.splitlines():
            l = line.strip()
            if "Potential Ship Mineables" in l: section = "ship"
            elif "Potential Hand Mineables" in l: section = "hand"
            elif "Potential Harvestables" in l or "Potential Creatures" in l: section = None
            elif section and l and not l.startswith("Potential"):
                if section == "ship": ship.append(l)
                elif section == "hand": hand.append(l)
        if ship or hand:
            planet_mineables[body] = {"ship": ship, "hand": hand}

# ---------------------------------------------------------------------------
# Build element rarity tiers (infer from folder names in asteroid presets)
# ---------------------------------------------------------------------------
RARITY_MAP = {"common": "Common", "uncommon": "Uncommon", "rare": "Rare",
              "epic": "Epic", "legendary": "Legendary"}

def infer_rarity(name):
    n = name.lower()
    for k, v in RARITY_MAP.items():
        if k in n:
            return v
    return "Unknown"

# Build rarity lookup from asteroid ship mining preset filenames
asteroid_rarity = {}
for f in (BASE / "rockcompositionpresets/asteroidshipmining").glob("*.xml"):
    if "template" in f.stem: continue
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue
    for part in root.iter("MineableCompositionPart"):
        eid = part.get("mineableElement", "")
        el = elements.get(eid)
        if el:
            rarity = infer_rarity(f.stem)
            asteroid_rarity[el["name"]] = rarity

# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------
def rarity_badge(r):
    colors = {"Common": "#7A7A8A", "Uncommon": "#4ade9a", "Rare": "#8B6FE8",
              "Epic": "#a371f7", "Legendary": "#f0c040", "Unknown": "#4A4A5A"}
    c = colors.get(r, "#4A4A5A")
    return f'<span style="background:{c}22;color:{c};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{r}</span>'

def kind_badge(k):
    colors = {"Ship": "#9b77cf", "FPS": "#7ecfb3", "Vehicle": "#e8a838"}
    c = colors.get(k, "#7A7A8A")
    return f'<span style="background:{c}22;color:{c};padding:2px 6px;border-radius:6px;font-size:11px">{k}</span>'

def pct_bar(minp, maxp):
    mid = (minp + maxp) / 2
    width = max(4, int(mid * 1.2))
    return (f'<div style="display:inline-block;background:#3A3F56;border-radius:3px;width:80px;height:8px;vertical-align:middle;margin:0 6px">'
            f'<div style="background:#8B6FE8;height:8px;border-radius:3px;width:{width}px"></div></div>'
            f'{minp:.1f}–{maxp:.1f}%')

# Elements table
el_rows = ""
for el in sorted(elements.values(), key=lambda x: (x["kind"], x["name"])):
    rarity = asteroid_rarity.get(el["name"], "Unknown")
    loc_hint = location_guide.get(el["name"].lower(), "")
    loc_cell = f'<span style="color:#7A7A8A;font-size:12px">{loc_hint}</span>' if loc_hint else '<span style="color:#4A4A5A">—</span>'
    el_rows += f"""
    <tr>
      <td><strong>{el['name']}</strong></td>
      <td>{kind_badge(el['kind'])}</td>
      <td>{rarity_badge(rarity)}</td>
      <td style="color:#f5a742">{el['resistance']}</td>
      <td style="color:#f85149">{el['instability']:.0f}</td>
      <td style="color:#e8a838">{el['explosion']:.1f}x</td>
      <td style="color:#7A7A8A;font-size:11px">{el['optimal_mid']:.2f} / {el['optimal_thin']:.2f}</td>
      <td>{loc_cell}</td>
    </tr>"""

# Rock compositions
comp_sections = ""
for rock_type, comps in rock_compositions.items():
    if not comps: continue
    rows = ""
    for c in sorted(comps, key=lambda x: x["name"]):
        parts_html = ""
        for p in c["parts"]:
            prob_txt = f' <span style="color:#7A7A8A">({p["probability"]*100:.0f}%)</span>' if p["probability"] < 1 else ""
            parts_html += f'<div style="margin:2px 0">{p["element"]}: {pct_bar(p["min_pct"],p["max_pct"])}{prob_txt}</div>'
        rows += f"""
        <tr>
          <td><strong>{c['name']}</strong></td>
          <td style="color:#7A7A8A">{c['min_dist']}</td>
          <td><div style="font-size:12px">{parts_html}</div></td>
        </tr>"""

    color = {"Asteroid (Ship)": "#9b77cf", "Surface (Ship)": "#54c87a",
             "FPS Deposit": "#7ecfb3", "Vehicle Deposit": "#e8a838", "Surface Deposit": "#8B6FE8"}.get(rock_type, "#7A7A8A")
    comp_sections += f"""
    <div class="card-table" style="margin-bottom:24px">
      <div class="section-head" style="color:{color}">{rock_type}</div>
      <table style="width:100%;border-collapse:collapse">
        <thead><tr>
          <th style="width:180px">Rock Name</th>
          <th style="width:60px">Min Dist</th>
          <th>Composition</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

# Planet location table
loc_rows = ""
for body in sorted(planet_mineables.keys()):
    d = planet_mineables[body]
    ship_str = ", ".join(d["ship"]) if d["ship"] else "—"
    hand_str = ", ".join(d["hand"]) if d["hand"] else "—"
    loc_rows += f"""
    <tr>
      <td><strong style="color:#FFFFFF">{body}</strong></td>
      <td style="color:#9b77cf;font-size:12px">{ship_str}</td>
      <td style="color:#7ecfb3;font-size:12px">{hand_str}</td>
    </tr>"""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC Mining Report</title>
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
.tabs{{display:flex;border-bottom:1px solid #3A3F56;background:#15171D;padding:0 40px;overflow-x:auto;flex-shrink:0}}
.tab{{padding:11px 18px;cursor:pointer;color:#7A7A8A;font-size:13px;font-weight:500;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s;user-select:none}}
.tab:hover{{color:#FFFFFF}}
.tab.active{{color:#FFFFFF;border-bottom-color:#532CD8}}
.container{{max-width:1300px;margin:0 auto;padding:24px 40px;flex:1}}
.panel{{display:none}}.panel.active{{display:block}}
.card-table{{background:linear-gradient(168deg,#232634 0%,#191B25 77%);outline:0.5px solid #14141A;box-shadow:inset 0px 0.5px 0px #2B2E3B;border:1px solid #3A3F56;border-radius:10px;overflow:hidden;margin-bottom:16px}}
.section-head{{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#7A7A8A;padding:14px 16px 10px;border-bottom:1px solid #3A3F56}}
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
    <a href="mining_report.html" class="cur">Mining</a>
    <a href="loot_report.html">Loot Tables</a>
    <a href="crafting_calculator.html">Calculator</a>
  </nav>
  <div class="site-ver">SC {GAME_VERSION}</div>
</div>
<div class="page-header">
  <h1>Mining Report</h1>
  <div class="sub">{len(elements)} mineable elements &bull; Rock compositions &bull; Location guide</div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showTab('elements',this)">Elements ({len(elements)})</div>
  <div class="tab" onclick="showTab('compositions',this)">Rock Compositions</div>
  <div class="tab" onclick="showTab('locations',this)">Locations by Body</div>
</div>
<div class="container">
  <div id="elements" class="panel active">
    <div class="card-table">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr>
          <th>Element</th>
          <th>Type</th>
          <th>Rarity</th>
          <th>Resistance</th>
          <th>Instability</th>
          <th>Explosion</th>
          <th>Opt Window (mid/thin)</th>
          <th>Locations</th>
        </tr></thead>
        <tbody>{el_rows}</tbody>
      </table>
    </div>
  </div>
  <div id="compositions" class="panel">
    {comp_sections}
  </div>
  <div id="locations" class="panel">
    <div class="card-table">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr>
          <th>Body</th>
          <th>Ship Mineables</th>
          <th>Hand Mineables</th>
        </tr></thead>
        <tbody>{loc_rows}</tbody>
      </table>
    </div>
  </div>
</div>
<script>
function showTab(id,btn){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"Written: {OUTPUT}")
print(f"Elements: {len(elements)}")
for k, v in rock_compositions.items():
    print(f"  {k}: {len(v)} compositions")
print(f"  Locations: {len(planet_mineables)} bodies")

# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------
json_elements = []
for el in sorted(elements.values(), key=lambda x: (x["kind"], x["name"])):
    json_elements.append({
        "name":        el["name"],
        "kind":        el["kind"],
        "resistance":  el["resistance"],
        "instability": el["instability"],
        "explosion":   el["explosion"],
        "optimal_mid": el["optimal_mid"],
        "optimal_thin":el["optimal_thin"],
        "rarity":      asteroid_rarity.get(el["name"], "Unknown"),
        "location":    location_guide.get(el["name"].lower(), ""),
    })

json_compositions = []
for rock_type, comps in rock_compositions.items():
    for c in sorted(comps, key=lambda x: x["name"]):
        json_compositions.append({
            "name":           c["name"],
            "rock_type":      c["rock_type"],
            "min_distinct":   c["min_dist"],
            "parts":          c["parts"],
        })

json_locations = []
for body, data in sorted(planet_mineables.items()):
    json_locations.append({
        "body": body,
        "ship_mineables": data.get("ship", []),
        "hand_mineables": data.get("hand", []),
    })

total_comps = sum(len(v) for v in rock_compositions.values())
json_payload = {
    "meta": {
        "game_version":      GAME_VERSION,
        "generated_at":      datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "element_count":     len(json_elements),
        "composition_count": len(json_compositions),
        "location_count":    len(json_locations),
    },
    "elements":        json_elements,
    "compositions":    json_compositions,
    "planet_mineables":json_locations,
}

json_dir = REPORTS_DIR / "JSON"
json_dir.mkdir(parents=True, exist_ok=True)
json_out = json_dir / "mining.json"
json_out.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"JSON   -> {json_out}  ({json_out.stat().st_size:,} bytes)")
