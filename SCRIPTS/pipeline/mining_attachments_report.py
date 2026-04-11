"""Mining attachments report — ship mining lasers, ship mining modules (active/passive),
and FPS mining gadgets with full stats from DataCore."""
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION, REPORTS_DIR

DATA_BASE   = Path(os.environ.get("SC_DATA_BASE", str(REPO_ROOT / "EXPLORER_Data")))

SCITEM_BASE = DATA_BASE / "Data" / "Libs" / "foundry" / "records" / "entities" / "scitem"
LOC_FILE    = DATA_BASE / "Data" / "Localization" / "english" / "global.ini"
OUTPUT      = REPORTS_DIR / "mining_attachments_report.html"

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

LOC_DATA = load_loc(LOC_FILE)

def loc(key):
    k = key.lstrip("@").lower()
    return LOC_DATA.get(k, key)

# ---------------------------------------------------------------------------
# Manufacturer code → display name
# ---------------------------------------------------------------------------
MFR_CODES = {
    "grin": "Greycat",
    "shin": "Shubin",
    "thcn": "Thermyte",
    "drak": "Drake",
}

def mfr_from_stem(stem):
    for code, name in MFR_CODES.items():
        if f"_{code}_" in stem or stem.endswith(f"_{code}"):
            return name
    return ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def float_val(root, tag):
    """Find first matching tag with FloatModifierMultiplicative and return value as float."""
    el = root.find(f".//{tag}[@__polymorphicType='FloatModifierMultiplicative']")
    if el is None:
        el = root.find(f".//{tag}")
    if el is not None:
        v = el.get("value")
        if v is not None:
            try:
                return float(v)
            except ValueError:
                pass
    return None

def fmt_mod(val, unit="%"):
    """Format a modifier value as +30% / -10% / etc."""
    if val is None:
        return None
    rounded = round(val)
    sign = "+" if rounded > 0 else ""
    return f"{sign}{rounded}{unit}"

# ---------------------------------------------------------------------------
# Parse Mining Lasers
# ---------------------------------------------------------------------------
laser_dir = SCITEM_BASE / "ships" / "weapons"
LASER_SKIP = {"test", "template", "mpuv", "golem", "arm"}

lasers = []
for f in sorted(laser_dir.glob("mining_laser*.xml")):
    if any(s in f.stem for s in LASER_SKIP):
        continue
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue
    att = root.find(".//AttachDef")
    if att is None or att.get("Type") != "WeaponMining":
        continue

    loc_el = root.find(".//Localization")
    name = loc(loc_el.get("Name", "")) if loc_el is not None else f.stem
    if name.startswith("@"):  # loc failed — fallback to stem
        name = f.stem.replace("mining_laser_", "").replace("_", " ").title()

    size = att.get("Size", "?")
    mfr  = mfr_from_stem(f.stem)

    desc_el = loc_el.get("Description", "") if loc_el is not None else ""
    desc    = loc(desc_el) if desc_el else ""

    laser = {
        "name":     name,
        "size":     size,
        "mfr":      mfr,
        "file":     f.stem,
        "filter":   float_val(root, "filterModifier"),
        "instab":   float_val(root, "laserInstability"),
        "rate":     float_val(root, "optimalChargeWindowRateModifier"),
        "win":      float_val(root, "optimalChargeWindowSizeModifier"),
        "shatter":  float_val(root, "shatterdamageModifier"),
        "cat_rate": float_val(root, "catastrophicChargeWindowRateModifier"),
        "desc":     desc,
    }
    lasers.append(laser)

lasers.sort(key=lambda x: (x["size"], x["name"]))

# ---------------------------------------------------------------------------
# Parse Mining Modules (active + passive)
# Stats sourced from localization descriptions — exactly what the game shows,
# including Mining Laser Power / Extraction Laser Power which live in
# weaponStats.damageMultiplier, not in MiningLaserModifiers.
# ---------------------------------------------------------------------------
STAT_SKIP_LABELS = {
    "manufacturer", "item type", "duration", "uses",
    "size", "grade", "optimal range", "maximum range",
    "module slots", "extraction throughput", "power transfer",
}

def parse_desc_stats(desc_raw):
    """Extract (label, value) stat pairs from a localization description string."""
    stats = []
    for line in desc_raw.replace("\\n", "\n").splitlines():
        line = line.strip()
        m = re.match(r"^([A-Za-z][A-Za-z\s()]+?):\s*([+-]?\d+\.?\d*\s*%?)$", line)
        if m:
            label = m.group(1).strip()
            value = m.group(2).strip()
            if label.lower() not in STAT_SKIP_LABELS:
                stats.append((label, value))
    return stats

mod_dir = SCITEM_BASE / "ships" / "utility" / "mining" / "miningarm"
active_modules  = []
passive_modules = []

for f in sorted(mod_dir.glob("mining_modules_*.xml")):
    if "vehiclemod" in f.stem:
        continue
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue

    loc_el = root.find(".//Localization")
    name   = loc(loc_el.get("Name", "")) if loc_el is not None else f.stem
    if name.startswith("@"):
        name = f.stem.replace("mining_modules_", "").replace("_", " ").title()

    desc_key = loc_el.get("Description", "") if loc_el is not None else ""
    desc_raw = loc(desc_key) if desc_key else ""
    stats    = parse_desc_stats(desc_raw)

    # Manufacturer from description
    mfr = ""
    m2 = re.search(r"Manufacturer:\s*(.+?)(?:\\n|\n|$)", desc_raw)
    if m2:
        mfr = m2.group(1).strip()

    # Activation type
    mp = root.find(".//EntityComponentAttachableModifierParams")
    activation = "Passive"
    charges    = None
    if mp is not None:
        am = mp.get("activationMethod", "")
        if "OnDemand" in am:
            activation = "Active"
            charges    = mp.get("charges")

    # Lifetime (active only)
    lifetime = None
    lt = root.find(".//modifierLifetime[@__polymorphicType='ItemModifierTimedLife']")
    if lt is not None:
        try:
            lifetime = float(lt.get("lifetime", "0"))
        except ValueError:
            pass

    mod = {
        "name":     name,
        "mfr":      mfr,
        "file":     f.stem,
        "charges":  charges,
        "lifetime": lifetime,
        "stats":    stats,
        "desc":     desc_raw,
    }

    if activation == "Active":
        active_modules.append(mod)
    else:
        passive_modules.append(mod)

active_modules.sort(key=lambda x: x["name"])
passive_modules.sort(key=lambda x: x["name"])

# ---------------------------------------------------------------------------
# Parse FPS Mining Gadgets
# ---------------------------------------------------------------------------
gadget_dir = SCITEM_BASE / "weapons" / "devices"
gadgets = []

for f in sorted(gadget_dir.glob("mining_gadget*.xml")):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue

    loc_el = root.find(".//Localization")
    name   = loc(loc_el.get("Name", "")) if loc_el is not None else f.stem
    if name.startswith("@"):
        name = f.stem.replace("mining_gadget_", "").replace("_", " ").title()

    desc_key = loc_el.get("Description", "") if loc_el is not None else ""
    desc_raw = loc(desc_key) if desc_key else ""

    # Parse stats from description — they appear as "Label: +XX%\n" or "Label: XX%\n"
    stats = []
    for line in desc_raw.replace("\\n", "\n").splitlines():
        line = line.strip()
        m = re.match(r"^([A-Za-z][A-Za-z\s]+?):\s*([+-]?\d+%?)$", line)
        if m:
            label, value = m.group(1).strip(), m.group(2).strip()
            if label not in ("Item Type", "Size", "Grade"):
                stats.append((label, value))

    # Manufacturer from description
    mfr = ""
    m2 = re.search(r"Manufacturer:\s*(.+?)(?:\\n|\n|$)", desc_raw)
    if m2:
        mfr = m2.group(1).strip()

    att = root.find(".//AttachDef")
    size = att.get("Size", "?") if att is not None else "?"

    gadgets.append({
        "name":  name,
        "mfr":   mfr,
        "size":  size,
        "file":  f.stem,
        "stats": stats,
        "desc":  desc_raw,
    })

gadgets.sort(key=lambda x: x["name"])

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
COLOR_POS  = "#3fb950"   # green
COLOR_NEG  = "#f85149"   # red
COLOR_NEU  = "#7d8590"   # grey
COLOR_GOLD = "#d29922"   # yellow/gold

def stat_chip(label, val, unit="%"):
    """Render a single stat as a coloured chip."""
    if val is None:
        return ""
    display = fmt_mod(val, unit)
    v = round(val)

    # Colour logic: green = good, red = bad
    # For instability: negative is good; for filter/win_rate/win_size: context-dependent
    # We'll green=positive, red=negative for most; invert for instability/resistance
    INVERT = {"instab", "resist"}
    is_positive = v > 0
    is_neg_stat  = False

    color = COLOR_POS if is_positive else (COLOR_NEG if v < 0 else COLOR_NEU)

    label_short = {
        "filter":   "Filter",
        "instab":   "Instability",
        "rate":     "Chg Rate",
        "win":      "Chg Window",
        "shatter":  "Shatter Dmg",
        "resist":   "Resistance",
        "cat_rate": "Catrph Rate",
    }.get(label, label)

    return (
        f'<div class="stat-chip">'
        f'<span class="stat-label">{label_short}</span>'
        f'<span class="stat-val" style="color:{color}">{display}</span>'
        f'</div>'
    )

SIZE_COLORS = {
    "0": "#7d8590",
    "1": "#58a6ff",
    "2": "#a371f7",
    "3": "#f0883e",
}

def size_badge(size):
    color = SIZE_COLORS.get(str(size), "#7d8590")
    return f'<span class="size-badge" style="border-color:{color};color:{color}">S{size}</span>'

def mfr_badge(mfr):
    if not mfr:
        return ""
    return f'<span class="mfr-badge">{mfr}</span>'

# ---------------------------------------------------------------------------
# Build laser section
# ---------------------------------------------------------------------------
lasers_by_size = defaultdict(list)
for l in lasers:
    lasers_by_size[l["size"]].append(l)

laser_html = ""
for size in sorted(lasers_by_size.keys()):
    group = lasers_by_size[size]
    size_color = SIZE_COLORS.get(str(size), "#7d8590")
    laser_html += f'<div class="size-group"><div class="size-header" style="border-left-color:{size_color}"><span style="color:{size_color};font-weight:700;font-size:15px">Size {size}</span> <span class="dim">({len(group)} lasers)</span></div>'
    laser_html += '<div class="card-grid">'
    for l in group:
        chips = ""
        for key in ["filter", "instab", "rate", "win", "shatter", "cat_rate"]:
            chips += stat_chip(key, l[key])

        laser_html += f"""
        <div class="card">
          <div class="card-header">
            <div class="card-title">{l["name"]}</div>
            <div class="card-badges">{mfr_badge(l["mfr"])}{size_badge(l["size"])}</div>
          </div>
          <div class="stat-row">{chips if chips else '<span class="dim">No stat modifiers</span>'}</div>
        </div>"""
    laser_html += "</div></div>"

# ---------------------------------------------------------------------------
# Build modules section
# ---------------------------------------------------------------------------
def desc_stat_chip(label, value_str):
    """Stat chip for description-parsed stats. Handles signed % and bare % (like 135%)."""
    if value_str.startswith("+"):
        color = COLOR_POS
    elif value_str.startswith("-"):
        color = COLOR_NEG
    else:
        # bare percentage like "135%" or "85%" — compare to 100
        try:
            num = float(value_str.rstrip("%").strip())
            color = COLOR_POS if num > 100 else (COLOR_NEG if num < 100 else COLOR_NEU)
        except ValueError:
            color = COLOR_GOLD
    return (
        f'<div class="stat-chip">'
        f'<span class="stat-label">{label}</span>'
        f'<span class="stat-val" style="color:{color}">{value_str}</span>'
        f'</div>'
    )

def module_card(m, is_active=False):
    chips = ""
    for label, val in m["stats"]:
        chips += desc_stat_chip(label, val)

    header_extra = ""
    if is_active and m["charges"] is not None:
        lifetime_s = f"{int(m['lifetime'])}s" if m["lifetime"] else "?"
        header_extra = f'<span class="charge-pill">{m["charges"]}x &bull; {lifetime_s}</span>'

    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title">{m["name"]}</div>
        <div class="card-badges">{mfr_badge(m.get("mfr",""))}{header_extra}</div>
      </div>
      <div class="stat-row">{chips if chips else '<span class="dim">No stat modifiers</span>'}</div>
    </div>"""

active_cards  = "".join(module_card(m, True)  for m in active_modules)
passive_cards = "".join(module_card(m, False) for m in passive_modules)

modules_html = f"""
<div class="sub-section">
  <div class="sub-header"><span class="sub-icon act">ACT</span> Active Modules <span class="dim">({len(active_modules)})</span></div>
  <div class="note-box">Active modules are single-use consumables with limited charges. Activate during mining to apply effects for a fixed duration.</div>
  <div class="card-grid">{active_cards}</div>
</div>
<div class="sub-section">
  <div class="sub-header"><span class="sub-icon pas">PAS</span> Passive Modules <span class="dim">({len(passive_modules)})</span></div>
  <div class="note-box">Passive modules apply their modifiers permanently while attached to the mining head.</div>
  <div class="card-grid">{passive_cards}</div>
</div>"""

# ---------------------------------------------------------------------------
# Build gadgets section
# ---------------------------------------------------------------------------
gadgets_html = '<div class="card-grid">'
for g in gadgets:
    stat_rows = ""
    for label, val in g["stats"]:
        stat_rows += desc_stat_chip(label, val)
    gadgets_html += f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title">{g["name"]}</div>
        <div class="card-badges">{mfr_badge(g["mfr"])}<span class="size-badge" style="border-color:#7d8590;color:#7d8590">FPS</span></div>
      </div>
      <div class="stat-row">{stat_rows if stat_rows else '<span class="dim">—</span>'}</div>
      <div class="gadget-warning">Warning: Using more than one gadget per deposit can cause a catastrophic explosion.</div>
    </div>"""
gadgets_html += "</div>"

# ---------------------------------------------------------------------------
# Full HTML
# ---------------------------------------------------------------------------
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC Mining Attachments — {GAME_VERSION}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;min-height:100vh}}
body{{background:#13141A;color:#CCCCCC;font-family:'Outfit',sans-serif;font-size:14px;display:flex;flex-direction:column}}

/* Nav bar */
.site-bar{{background:linear-gradient(to right,#1A1C26 0%,#15171D 100%);border-bottom:1px solid #3A3F56;height:52px;padding:0 32px;display:flex;align-items:center;gap:0;position:sticky;top:0;z-index:100;flex-shrink:0}}
.site-logo{{font-weight:800;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#FFFFFF;display:flex;align-items:center;gap:8px;flex-shrink:0}}
.site-logo::before{{content:'';display:block;width:8px;height:8px;background:#532CD8;border-radius:2px;transform:rotate(45deg)}}
.site-nav{{display:flex;gap:2px;margin-left:24px;flex:1}}
.site-nav a{{color:#7A7A8A;text-decoration:none;font-size:12px;font-weight:500;padding:5px 12px;border-radius:6px;transition:all .15s;white-space:nowrap}}
.site-nav a:hover{{color:#FFFFFF;background:rgba(255,255,255,.06)}}
.site-nav a.cur{{color:#FFFFFF;background:#532CD8}}
.site-ver{{font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#4A4A5A;font-family:'Geist Mono',monospace;flex-shrink:0}}

/* Page header */
.page-header{{background:#15171D;border-bottom:1px solid #3A3F56;padding:22px 40px 18px;flex-shrink:0}}
.page-header h1{{font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-.01em}}
.page-header .sub{{color:#7A7A8A;font-size:13px;margin-top:4px}}
.summary-pills{{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap}}
.pill{{background:#232634;border:1px solid #3A3F56;border-radius:8px;padding:10px 18px;display:flex;flex-direction:column;gap:2px}}
.pill .num{{font-size:22px;font-weight:700;color:#FFFFFF}}
.pill .lbl{{font-size:11px;color:#7A7A8A;text-transform:uppercase;letter-spacing:.05em}}

/* Tabs */
.tabs{{display:flex;border-bottom:1px solid #3A3F56;background:#15171D;padding:0 40px;overflow-x:auto;flex-shrink:0}}
.tab{{padding:11px 20px;cursor:pointer;color:#7A7A8A;font-size:13px;font-weight:500;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s;user-select:none}}
.tab:hover{{color:#FFFFFF}}
.tab.active{{color:#FFFFFF;border-bottom-color:#532CD8}}

/* Layout */
.container{{max-width:1300px;width:100%;margin:0 auto;padding:28px 40px;flex:1}}
.panel{{display:none}}.panel.active{{display:block}}

/* Size groups */
.size-group{{margin-bottom:28px}}
.size-header{{border-left:3px solid #532CD8;padding:6px 0 6px 14px;margin-bottom:14px}}

/* Sub-sections (active/passive) */
.sub-section{{margin-bottom:32px}}
.sub-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px;font-size:15px;font-weight:600;color:#e6edf3}}
.sub-icon{{width:32px;height:32px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#0d1117;flex-shrink:0}}
.sub-icon.act{{background:#e8a838}}
.sub-icon.pas{{background:#58a6ff}}

/* Cards */
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}
.card{{background:linear-gradient(168deg,#232634 0%,#191B25 77%);border:1px solid #3A3F56;border-radius:10px;padding:14px 16px;transition:border-color .15s}}
.card:hover{{border-color:#58a6ff40}}
.card-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:10px}}
.card-title{{font-size:14px;font-weight:600;color:#e6edf3;line-height:1.3}}
.card-badges{{display:flex;gap:6px;align-items:center;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end}}

/* Stat row */
.stat-row{{display:flex;flex-wrap:wrap;gap:6px}}
.stat-chip{{background:#0d1117;border:1px solid #2b2e3b;border-radius:6px;padding:4px 8px;display:flex;flex-direction:column;gap:1px;min-width:80px}}
.stat-label{{font-size:10px;color:#7A7A8A;text-transform:uppercase;letter-spacing:.04em;font-family:'Geist Mono',monospace}}
.stat-val{{font-size:13px;font-weight:700;font-family:'Geist Mono',monospace}}

/* Badges */
.size-badge{{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid;font-family:'Geist Mono',monospace}}
.mfr-badge{{font-size:11px;font-weight:500;padding:2px 8px;border-radius:10px;background:#232634;border:1px solid #3A3F56;color:#7A7A8A}}
.charge-pill{{font-size:11px;font-weight:700;padding:3px 10px;border-radius:10px;background:#3a2e0f;color:#d29922;font-family:'Geist Mono',monospace}}

/* Notes */
.note-box{{background:#1a1c26;border:1px solid #3A3F56;border-radius:8px;padding:10px 14px;font-size:12px;color:#7A7A8A;margin-bottom:14px;line-height:1.6}}
.gadget-warning{{margin-top:8px;font-size:11px;color:#d29922;font-style:italic}}

.dim{{color:#7A7A8A;font-weight:400;font-size:13px}}

/* Legend */
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px;font-size:12px}}
.legend-item{{display:flex;align-items:center;gap:6px}}
.legend-dot{{width:10px;height:10px;border-radius:2px}}

footer{{text-align:center;padding:24px;color:#484f58;font-size:12px;border-top:1px solid #21262d;margin-top:16px}}
</style>
</head>
<body>
<div class="site-bar">
  <div class="site-logo">Saladins Information</div>
  <nav class="site-nav">
    <a href="crafting_report.html">Crafting</a>
    <a href="mining_report.html">Mining</a>
    <a href="mining_attachments_report.html" class="cur">Mining Gear</a>
    <a href="loot_report.html">Loot Tables</a>
    <a href="crafting_calculator.html">Calculator</a>
  </nav>
  <div class="site-ver">SC {GAME_VERSION}</div>
</div>

<div class="page-header">
  <h1>Mining Attachments</h1>
  <div class="sub">Ship mining lasers, mining modules, and FPS mining gadgets — full stats from DataCore</div>
  <div class="summary-pills">
    <div class="pill"><div class="num">{len(lasers)}</div><div class="lbl">Mining Lasers</div></div>
    <div class="pill"><div class="num">{len(active_modules)}</div><div class="lbl">Active Modules</div></div>
    <div class="pill"><div class="num">{len(passive_modules)}</div><div class="lbl">Passive Modules</div></div>
    <div class="pill"><div class="num">{len(gadgets)}</div><div class="lbl">FPS Gadgets</div></div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('lasers',this)">Mining Lasers ({len(lasers)})</div>
  <div class="tab" onclick="showTab('modules',this)">Mining Modules ({len(active_modules) + len(passive_modules)})</div>
  <div class="tab" onclick="showTab('gadgets',this)">FPS Gadgets ({len(gadgets)})</div>
</div>

<div class="container">
  <!-- LASERS -->
  <div id="tab_lasers" class="panel active">
    <div class="legend">
      <span class="dim">Stats are % modifiers relative to the base laser head.</span>
      <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div> Positive modifier</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f85149"></div> Negative modifier</div>
    </div>
    {laser_html}
  </div>

  <!-- MODULES -->
  <div id="tab_modules" class="panel">
    <div class="legend">
      <span class="dim">Active module charges: number of uses &bull; duration each activation.</span>
    </div>
    {modules_html}
  </div>

  <!-- GADGETS -->
  <div id="tab_gadgets" class="panel">
    <div class="note-box">
      <strong style="color:#f5a742">FPS Mining Gadgets</strong> — Placed directly on a rock deposit before mining. Stats shown are from in-game descriptions. Only one gadget may be active per deposit safely.
    </div>
    {gadgets_html}
  </div>
</div>

<footer>Generated from DataCore snapshot &bull; SC DataPack Explorer &bull; {GAME_VERSION}</footer>

<script>
function showTab(id, btn) {{
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab_' + id).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"Written: {OUTPUT}")
print(f"Size: {OUTPUT.stat().st_size // 1024} KB")
print(f"Mining lasers:   {len(lasers)}")
print(f"Active modules:  {len(active_modules)}")
print(f"Passive modules: {len(passive_modules)}")
print(f"FPS gadgets:     {len(gadgets)}")

# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------
from pipeline.export_json import write_json

json_records = []
for laser in lasers:
    json_records.append({
        "category":           "laser",
        "name":               laser["name"],
        "manufacturer":       laser["mfr"],
        "size":               laser["size"],
        "file":               laser["file"],
        "filter_modifier":    laser["filter"],
        "instability_modifier":laser["instab"],
        "charge_rate_modifier":laser["rate"],
        "window_size_modifier":laser["win"],
        "shatter_modifier":   laser["shatter"],
        "catastrophic_rate_modifier": laser["cat_rate"],
        "stats":              [{"label": l, "value": v} for l, v in []],
    })
for mod in active_modules:
    json_records.append({
        "category":   "active_module",
        "name":       mod["name"],
        "manufacturer": mod["mfr"],
        "size":       None,
        "file":       mod["file"],
        "charges":    int(mod["charges"]) if mod["charges"] is not None else None,
        "lifetime_s": mod["lifetime"],
        "stats":      [{"label": l, "value": v} for l, v in mod["stats"]],
    })
for mod in passive_modules:
    json_records.append({
        "category":   "passive_module",
        "name":       mod["name"],
        "manufacturer": mod["mfr"],
        "size":       None,
        "file":       mod["file"],
        "charges":    None,
        "lifetime_s": None,
        "stats":      [{"label": l, "value": v} for l, v in mod["stats"]],
    })
for gadget in gadgets:
    json_records.append({
        "category":   "fps_gadget",
        "name":       gadget["name"],
        "manufacturer": gadget["mfr"],
        "size":       gadget["size"],
        "file":       gadget["file"],
        "stats":      [{"label": l, "value": v} for l, v in gadget["stats"]],
    })

json_out = write_json(json_records, "mining_gear.json", extra_meta={
    "lasers":          len(lasers),
    "active_modules":  len(active_modules),
    "passive_modules": len(passive_modules),
    "fps_gadgets":     len(gadgets),
})
print(f"JSON   -> {json_out}  ({json_out.stat().st_size:,} bytes)")
