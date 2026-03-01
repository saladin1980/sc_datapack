"""
Armor reference page generator.
Scans pu_armor + starwear/helmet items, extracts all stats,
outputs a searchable/filterable self-contained HTML page.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR, GAME_VERSION

# Reuse helpers from ships_preview
from pipeline.ships_preview import (
    build_uuid_index,
    build_localization_index,
    build_manufacturer_index,
    _get_display_name,
)

RECORDS_DIR  = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
ARMOR_BASE   = RECORDS_DIR / "entities" / "scitem" / "characters" / "human" / "armor" / "pu_armor"
HELMET_DIR   = RECORDS_DIR / "entities" / "scitem" / "characters" / "human" / "starwear" / "helmet"
DAMAGE_DIR   = RECORDS_DIR / "damage"

# ── Slot display ──────────────────────────────────────────────────────────────

SLOT_FROM_TYPE = {
    "Char_Armor_Helmet":    "Helmet",
    "Char_Armor_Torso":     "Torso",
    "Char_Armor_Arms":      "Arms",
    "Char_Armor_Legs":      "Legs",
    "Char_Armor_Undersuit": "Undersuit",
    "Char_Armor_Backpack":  "Backpack",
}

SLOT_ORDER  = ["Helmet", "Torso", "Arms", "Legs", "Undersuit", "Backpack", "Other"]
SLOT_ICONS  = {
    "Helmet":    "&#9651;",  # triangle for helmet feel
    "Torso":     "&#9632;",  # square
    "Arms":      "&#9674;",  # diamond
    "Legs":      "&#9650;",  # triangle
    "Undersuit": "&#9711;",  # circle
    "Backpack":  "&#9670;",  # filled diamond
    "Other":     "&#9733;",  # star
}

TIER_COLORS = {
    "Heavy":    "#c0392b",   # red
    "Medium":   "#e67e22",   # orange
    "Light":    "#3498db",   # blue
    "Helmet":   "#9b59b6",   # purple (standalone helmet tier label)
    "Personal": "#27ae60",   # green (backpacks)
}

# Normalize raw SubType values to filterable tier keys
def _normalize_tier(subtype):
    """Return 'heavy'/'medium'/'light' or '' for unknown/generic subtypes."""
    s = subtype.strip().lower()
    if s in ("heavy",):
        return "heavy"
    if s in ("medium",):
        return "medium"
    if s in ("light", "lightarmor"):
        return "light"
    return ""  # Helmet, Personal, UNDEFINED, etc.

# Known armor manufacturer codes -> display names
MFR_NAMES = {
    "CDS":    "Crusader Defense",
    "KLWE":   "Klaus & Werner",
    "ACOM":   "Acom",
    "BASL":   "Basilisk",
    "BEHR":   "Behring",
    "CGPO":   "CIG",
    "LNDR":   "Lander",
    "AMRS":   "Amrs",
    "CRSD":   "Crossfire",
    "MRAI":   "Mirai",
    "JUST":   "JUST",
    "TALN":   "Talon",
    "GATS":   "Gatso",
    "RSI":    "RSI",
    "TMBL":   "Tumbril",
    "ORIG":   "Origin",
    "MNVR":   "Musashi",
    "VOLT":   "Volt",
    "GRYO":   "Greycat",
    "SBER":   "Sber",
    "MISC":   "MISC",
    "DRAK":   "Drake",
    "ANVL":   "Anvil",
    "AEGS":   "Aegis",
    "CNUS":   "C. Outland",
    "GRIN":   "Greycat Ind.",
    "XNAA":   "Xenotech",
}

# ── Damage resistance index ──────────────────────────────────────────────────

DMG_KEYS = ["Physical", "Energy", "Distortion", "Thermal", "Biochemical", "Stun"]

def build_dmg_res_index():
    """UUID -> {Physical: %, Energy: %, ..., Force: %} where % = (1-mult)*100."""
    idx = {}
    for f in DAMAGE_DIR.glob("*.xml"):
        try:
            root = ET.parse(f).getroot()
            ref  = root.get("__id")
            if not ref:
                continue
            res = {}
            for el in root.iter():
                tag  = el.tag
                mult = el.get("Multiplier")
                if mult:
                    for key in DMG_KEYS:
                        if key in tag:
                            try:
                                res[key] = round((1.0 - float(mult)) * 100, 1)
                            except (ValueError, TypeError):
                                pass
                            break
                force = el.get("impactForceResistance")
                if force:
                    try:
                        res["Force"] = round((1.0 - float(force)) * 100, 1)
                    except (ValueError, TypeError):
                        pass
            idx[ref] = res
        except Exception:
            pass
    print(f"  {len(idx)} damage resistance macros indexed")
    return idx


def _get_container_scu(uuid, uuid_idx):
    """Resolve an InventoryContainer UUID -> microSCU int (0 if not found)."""
    if not uuid or uuid == "00000000-0000-0000-0000-000000000000":
        return 0
    entry = uuid_idx.get(uuid)
    if not entry:
        return 0
    try:
        root = ET.parse(entry["path"]).getroot()
        for el in root.iter():
            v = el.get("microSCU")
            if v:
                return int(v)
    except Exception:
        pass
    return 0


# ── Armor item parser ─────────────────────────────────────────────────────────

def parse_armor_item(path, uuid_idx, mfr_idx, loc_idx, dmg_idx):
    """Parse one armor XML, return info dict or None."""
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None

    info = {
        "file":          path.stem,
        "name":          "",
        "slot":          "Other",
        "subtype":       "",
        "tier":          "",   # "heavy" / "medium" / "light" / ""
        "mfr":           "",
        "micro_scu":     0,
        "dmg":           {},
        "temp_min":      None,
        "temp_max":      None,
        "rad_cap":       None,
        "rad_rate":      None,
        "sigs":          [],
        "container_scu": 0,
    }

    # ── AttachDef ──────────────────────────────────────────────────────────────
    for el in root.iter():
        pt = el.get("__polymorphicType", "")
        if pt == "SItemDefinition" or el.tag == "AttachDef":
            typ     = el.get("Type", "")
            subtype = el.get("SubType", "")
            mfr_ref = el.get("Manufacturer", "")

            info["slot"]    = SLOT_FROM_TYPE.get(typ, "Other")
            info["subtype"] = subtype if subtype not in ("UNDEFINED", "") else ""
            info["tier"]    = _normalize_tier(subtype)

            # Backpacks in heavy/light/medium subdirs are tagged "Personal" by the
            # game regardless of set — infer tier from parent directory path instead
            if info["slot"] == "Backpack" and not info["tier"]:
                parts = [p.lower() for p in path.parts]
                if "heavy" in parts:
                    info["tier"] = "heavy"
                elif "medium" in parts:
                    info["tier"] = "medium"
                elif "light" in parts:
                    info["tier"] = "light"

            # Manufacturer
            mfr_code = mfr_idx.get(mfr_ref, "")
            info["mfr"] = MFR_NAMES.get(mfr_code, mfr_code) if mfr_code else ""

            # Display name via Localization child
            info["name"] = _get_display_name(el, loc_idx)

            # Item occupancy (inline microSCU)
            for sub in el.iter():
                v = sub.get("microSCU")
                if v:
                    try:
                        info["micro_scu"] = int(v)
                    except (ValueError, TypeError):
                        pass
                    break
            break

    # Fallback name from SCItemPurchasableParams.displayName
    if not info["name"]:
        for el in root.iter():
            dn = el.get("displayName", "")
            if dn and dn.startswith("@") and dn not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                key = dn[1:].lower()
                name = loc_idx.get(key, "")
                if name and "PLACEHOLDER" not in name.upper():
                    info["name"] = name
                    break

    # If still no name, check whether the XML's loc key explicitly resolves to PLACEHOLDER
    # (now returns "" from _get_display_name). Those are dev-only items — skip entirely.
    # Items with genuinely missing translations get filename fallback instead.
    if not info["name"]:
        is_placeholder = False
        for el in root.iter():
            if "Localization" in el.tag:
                k = el.get("Name", "")
                if k and k.startswith("@") and k not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                    raw = loc_idx.get(k[1:].lower(), "")
                    if "PLACEHOLDER" in raw.upper():
                        is_placeholder = True
                    break
        if is_placeholder:
            return None  # filter dev-only items
        info["name"] = path.stem  # real item, just missing translation

    # ── SCItemSuitArmorParams ──────────────────────────────────────────────────
    for el in root.iter():
        pt = el.get("__polymorphicType", "")
        if "SCItemSuitArmorParams" in el.tag or "SCItemSuitArmorParams" in pt:
            # Damage resistance UUID
            dmg_ref = el.get("damageResistance", "")
            if dmg_ref and dmg_ref != "00000000-0000-0000-0000-000000000000":
                info["dmg"] = dmg_idx.get(dmg_ref, {})

            # Signatures (inline children)
            for sig_el in el.iter():
                if "ItemSuitArmorSignatureParams" in sig_el.tag:
                    sig_type    = sig_el.get("signatureType", "")
                    emission    = sig_el.get("signatureEmission", "")
                    reduc_w     = sig_el.get("signatureReductionWeighted", "")
                    reduc_a     = sig_el.get("signatureReductionAbsolute", "")
                    if sig_type:
                        try:
                            info["sigs"].append({
                                "type":      sig_type,
                                "emission":  float(emission)  if emission  else 0.0,
                                "reduc_w":   float(reduc_w)   if reduc_w   else 0.0,
                                "reduc_a":   float(reduc_a)   if reduc_a   else 0.0,
                            })
                        except (ValueError, TypeError):
                            pass
            break

    # ── SCItemClothingParams ───────────────────────────────────────────────────
    for el in root.iter():
        pt = el.get("__polymorphicType", "")
        if "SCItemClothingParams" in el.tag or "SCItemClothingParams" in pt:
            for sub in el.iter():
                # Temperature
                if "TemperatureResistance" in sub.tag:
                    try:
                        info["temp_min"] = float(sub.get("MinResistance", ""))
                        info["temp_max"] = float(sub.get("MaxResistance", ""))
                    except (ValueError, TypeError):
                        pass
                # Radiation
                if "RadiationResistance" in sub.tag:
                    try:
                        info["rad_cap"]  = float(sub.get("MaximumRadiationCapacity", ""))
                        info["rad_rate"] = float(sub.get("RadiationDissipationRate", ""))
                    except (ValueError, TypeError):
                        pass
            break

    # ── Inventory container (backpacks) ───────────────────────────────────────
    for el in root.iter():
        pt = el.get("__polymorphicType", "")
        if "SCItemInventoryContainerComponentParams" in el.tag or \
           "SCItemInventoryContainerComponentParams" in pt:
            container_ref = el.get("containerParams", "")
            info["container_scu"] = _get_container_scu(container_ref, uuid_idx)
            break

    return info


# ── Scanner ───────────────────────────────────────────────────────────────────

# Skip patterns for non-player variants
_SKIP_PATTERNS = ("_nodraw", "_ai_", "_npc_", "_s42_", "_mannequin")
_SKIP_PREFIXES = frozenset({"entityclassdefinition", "backpack_nodraw"})

def _should_skip(stem):
    s = stem.lower()
    if s in _SKIP_PREFIXES:
        return True
    return any(p in s for p in _SKIP_PATTERNS)


def scan_all_armor():
    """Return list of armor XML paths from pu_armor and starwear/helmet."""
    paths = []
    # pu_armor subtree
    if ARMOR_BASE.exists():
        for f in sorted(ARMOR_BASE.rglob("*.xml")):
            if not _should_skip(f.stem):
                paths.append(f)
    # starwear helmets
    if HELMET_DIR.exists():
        for f in sorted(HELMET_DIR.rglob("*.xml")):
            if not _should_skip(f.stem):
                paths.append(f)
    return paths


# ── HTML generation ───────────────────────────────────────────────────────────

def _tier_badge(subtype):
    if not subtype:
        return ""
    color = TIER_COLORS.get(subtype, "#7f8c8d")
    return f'<span class="tier" style="background:{color}">{subtype}</span>'


def _dmg_bar(pct, label):
    """Render a single damage resistance bar."""
    if pct is None:
        return ""
    bar_color = "#27ae60" if pct >= 35 else "#e67e22" if pct >= 20 else "#3498db"
    return (
        f'<div class="bar-row">'
        f'<span class="bar-lbl">{label}</span>'
        f'<div class="bar-bg"><div class="bar-fill" style="width:{min(pct,100):.0f}%;background:{bar_color}"></div></div>'
        f'<span class="bar-val">{pct:.0f}%</span>'
        f'</div>'
    )


def item_to_html(item):
    if not item or item["slot"] == "Other":
        return ""

    slot   = item["slot"]
    name   = item["name"] or item["file"]
    subtype = item["subtype"]
    mfr    = item["mfr"] or "Unknown"

    # Header badges
    tier_badge = _tier_badge(subtype)
    size_badge = (
        f'<span class="stat-chip">{item["micro_scu"]:,} µSCU</span>'
        if item["micro_scu"] > 0 else ""
    )

    # Damage resistance section
    dmg = item["dmg"]
    dmg_html = ""
    if dmg:
        bars = ""
        for key in ["Physical", "Energy", "Distortion", "Thermal", "Biochemical", "Stun"]:
            v = dmg.get(key)
            if v is not None:
                short = {"Physical": "Phys", "Energy": "Enrg", "Distortion": "Dist",
                         "Thermal": "Thrm", "Biochemical": "Bio", "Stun": "Stun"}.get(key, key)
                bars += _dmg_bar(v, short)
        force = dmg.get("Force")
        if force is not None:
            bars += _dmg_bar(force, "Impact")
        if bars:
            dmg_html = f'<div class="stat-section"><div class="stat-title">Damage Resistance</div>{bars}</div>'

    # Temperature section
    temp_html = ""
    if item["temp_min"] is not None and item["temp_max"] is not None:
        temp_html = (
            f'<div class="stat-section">'
            f'<div class="stat-title">Temperature</div>'
            f'<div class="kv-grid">'
            f'<span class="k">Min</span><span class="v">{item["temp_min"]:g} °C</span>'
            f'<span class="k">Max</span><span class="v">{item["temp_max"]:g} °C</span>'
            f'</div></div>'
        )

    # Radiation section
    rad_html = ""
    if item["rad_cap"] is not None:
        rad_html = (
            f'<div class="stat-section">'
            f'<div class="stat-title">Radiation</div>'
            f'<div class="kv-grid">'
            f'<span class="k">Capacity</span><span class="v">{item["rad_cap"]:g}</span>'
            f'<span class="k">Diss.Rate</span><span class="v">{item["rad_rate"]:g}/s</span>'
            f'</div></div>'
        )

    # Signatures
    sig_html = ""
    if item["sigs"]:
        rows = ""
        for s in item["sigs"]:
            em = s["emission"]
            rw = s["reduc_w"]
            ra = s["reduc_a"]
            rows += (
                f'<span class="k">{s["type"]}</span>'
                f'<span class="v">+{em:g} / -{rw:g}w -{ra:g}a</span>'
            )
        sig_html = (
            f'<div class="stat-section">'
            f'<div class="stat-title">Signatures (emit / reduce)</div>'
            f'<div class="kv-grid">{rows}</div></div>'
        )

    # Container (backpack storage)
    container_html = ""
    if item["container_scu"] > 0:
        scu_k = item["container_scu"] / 1000
        container_html = (
            f'<div class="stat-section">'
            f'<div class="stat-title">Storage</div>'
            f'<div class="kv-grid">'
            f'<span class="k">Capacity</span><span class="v">{scu_k:g}K µSCU</span>'
            f'</div></div>'
        )

    stats_body = dmg_html + temp_html + rad_html + sig_html + container_html
    if not stats_body:
        stats_body = '<div class="no-stats">No detailed stats found</div>'

    return f"""
<div class="item-card" data-slot="{slot}" data-tier="{item['tier']}" data-name="{name.lower()}">
  <div class="card-header">
    <div class="card-title-row">
      <span class="item-name">{name}</span>
      {tier_badge}
    </div>
    <div class="card-meta">{mfr} &middot; {slot} {size_badge}</div>
  </div>
  <div class="card-body">
    {stats_body}
  </div>
</div>"""


def generate_html(items):
    from collections import Counter
    valid  = [i for i in items if i and i["slot"] != "Other"]
    count  = len(valid)
    cards  = "\n".join(item_to_html(i) for i in valid)

    # Slot tabs
    slot_counts = Counter(i["slot"] for i in valid)
    slot_tabs = (
        f'<button class="tab slot-tab active" data-slot="all" onclick="setSlotTab(this)">'
        f'All <span class="tc">{count}</span></button>'
    )
    for slot in SLOT_ORDER:
        if slot == "Other":
            continue
        c = slot_counts.get(slot, 0)
        if c:
            slot_tabs += (
                f'<button class="tab slot-tab" data-slot="{slot}" onclick="setSlotTab(this)">'
                f'{slot} <span class="tc">{c}</span></button>'
            )

    # Tier tabs
    tier_counts = Counter(i["tier"] for i in valid if i["tier"])
    tier_total  = sum(tier_counts.values())
    tier_tabs = (
        f'<button class="tab tier-tab active" data-tier="all" onclick="setTierTab(this)">'
        f'All Tiers <span class="tc">{tier_total}</span></button>'
    )
    for tier, label in [("light", "Light"), ("medium", "Medium"), ("heavy", "Heavy")]:
        c = tier_counts.get(tier, 0)
        if c:
            color = {"light": "#3498db", "medium": "#e67e22", "heavy": "#c0392b"}[tier]
            tier_tabs += (
                f'<button class="tab tier-tab" data-tier="{tier}" '
                f'style="--tier-color:{color}" onclick="setTierTab(this)">'
                f'{label} <span class="tc">{c}</span></button>'
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SC Armor Reference</title>
<style>
  :root {{
    --bg:     #0d0f14;
    --card:   #161922;
    --border: #2a2f3d;
    --text:   #e8ecf0;
    --muted:  #8892a4;
    --accent: #5b9cf6;
    --green:  #27ae60;
    --orange: #e67e22;
    --red:    #c0392b;
    --blue:   #3498db;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font:14px/1.5 "Inter","Segoe UI",sans-serif; }}
  h1 {{ font-size:1.6rem; font-weight:700; letter-spacing:-.02em; }}
  header {{ padding:20px 24px 12px; border-bottom:1px solid var(--border); }}
  header .sub {{ color:var(--muted); font-size:.85rem; margin-top:4px; }}
  .controls {{ display:flex; flex-direction:column; gap:0; border-bottom:1px solid var(--border); }}
  .filter-row {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px;
                 padding:10px 24px; border-bottom:1px solid var(--border); }}
  .filter-row:last-child {{ border-bottom:none; }}
  .filter-label {{ font-size:.7rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
                   color:var(--muted); min-width:40px; }}
  .tabs {{ display:flex; flex-wrap:wrap; gap:6px; flex:1; }}
  .tab {{ background:var(--card); border:1px solid var(--border); border-radius:6px;
          color:var(--muted); cursor:pointer; font-size:.8rem; padding:5px 12px;
          transition:all .15s; }}
  .tab:hover {{ border-color:var(--accent); color:var(--text); }}
  .tab.active {{ background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }}
  .tier-tab.active {{ background:var(--tier-color,var(--accent));
                      border-color:var(--tier-color,var(--accent)); }}
  .tc {{ opacity:.7; font-weight:400; }}
  #search-box {{ background:var(--card); border:1px solid var(--border); border-radius:6px;
                 color:var(--text); font-size:.85rem; padding:6px 12px; width:220px; }}
  #search-box:focus {{ outline:none; border-color:var(--accent); }}
  #vis-count {{ color:var(--muted); font-size:.8rem; white-space:nowrap; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr));
           gap:14px; padding:18px 24px; }}
  .item-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px;
                overflow:hidden; transition:border-color .15s; }}
  .item-card:hover {{ border-color:var(--accent); }}
  .card-header {{ padding:12px 14px 10px; border-bottom:1px solid var(--border); }}
  .card-title-row {{ display:flex; align-items:flex-start; gap:6px; flex-wrap:wrap; margin-bottom:4px; }}
  .item-name {{ font-weight:600; font-size:.9rem; line-height:1.3; flex:1; min-width:0;
                overflow-wrap:break-word; }}
  .tier {{ font-size:.7rem; font-weight:700; border-radius:4px; padding:2px 7px;
           color:#fff; white-space:nowrap; align-self:flex-start; }}
  .card-meta {{ font-size:.75rem; color:var(--muted); display:flex; flex-wrap:wrap; gap:6px;
                align-items:center; }}
  .stat-chip {{ background:#1e2535; border:1px solid var(--border); border-radius:4px;
                font-size:.7rem; padding:1px 6px; color:var(--muted); }}
  .card-body {{ padding:10px 14px 12px; display:flex; flex-direction:column; gap:10px; }}
  .stat-section {{ display:flex; flex-direction:column; gap:4px; }}
  .stat-title {{ font-size:.7rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
                  color:var(--muted); margin-bottom:2px; }}
  /* Damage bars */
  .bar-row {{ display:grid; grid-template-columns:44px 1fr 38px; align-items:center; gap:6px; }}
  .bar-lbl {{ font-size:.72rem; color:var(--muted); text-align:right; }}
  .bar-bg {{ background:#1e2535; border-radius:3px; height:7px; overflow:hidden; }}
  .bar-fill {{ height:100%; border-radius:3px; transition:width .3s; }}
  .bar-val {{ font-size:.72rem; font-weight:600; color:var(--text); text-align:right; }}
  /* KV grid */
  .kv-grid {{ display:grid; grid-template-columns:auto 1fr; gap:2px 10px; }}
  .k {{ font-size:.75rem; color:var(--muted); }}
  .v {{ font-size:.75rem; color:var(--text); font-weight:500; }}
  .no-stats {{ font-size:.78rem; color:var(--muted); font-style:italic; }}
  footer {{ text-align:center; padding:20px; color:var(--muted); font-size:.8rem; }}
</style>
</head>
<body>
<header>
  <h1>Star Citizen — Armor Reference</h1>
  <div class="sub">All player-usable armor &mdash; {count} items &middot; {GAME_VERSION}</div>
</header>
<div class="controls">
  <div class="filter-row">
    <span class="filter-label">Slot</span>
    <div class="tabs">{slot_tabs}</div>
    <input id="search-box" type="search" placeholder="Search by name..." oninput="applyFilters()">
    <span id="vis-count">{count} shown</span>
  </div>
  <div class="filter-row">
    <span class="filter-label">Tier</span>
    <div class="tabs">{tier_tabs}</div>
  </div>
</div>
<div class="grid" id="item-grid">
{cards}
</div>
<footer>Data extracted from Star Citizen Data.p4k &mdash; For reference only</footer>
<script>
function setSlotTab(btn) {{
  document.querySelectorAll('.slot-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function setTierTab(btn) {{
  document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function applyFilters() {{
  const slot = document.querySelector('.slot-tab.active').dataset.slot;
  const tier = document.querySelector('.tier-tab.active').dataset.tier;
  const q    = document.getElementById('search-box').value.toLowerCase().trim();
  let vis = 0;
  document.querySelectorAll('.item-card').forEach(c => {{
    const sok = slot === 'all' || c.dataset.slot === slot;
    // tier filter: 'all' shows everything; specific tier matches exact OR items with no tier
    const tok = tier === 'all' || c.dataset.tier === tier;
    const nok = !q || c.dataset.name.includes(q);
    const show = sok && tok && nok;
    c.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById('vis-count').textContent = vis + ' shown';
}}
</script>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Building indexes...")
    uuid_idx = build_uuid_index()
    mfr_idx  = build_manufacturer_index(uuid_idx)
    loc_idx  = build_localization_index()

    print("Building damage resistance index...")
    dmg_idx  = build_dmg_res_index()

    armor_paths = scan_all_armor()
    print(f"\nParsing {len(armor_paths)} armor items...")

    items = []
    skipped = 0
    for i, path in enumerate(armor_paths, 1):
        if i % 200 == 0:
            print(f"  {i}/{len(armor_paths)}...", flush=True)
        item = parse_armor_item(path, uuid_idx, mfr_idx, loc_idx, dmg_idx)
        if item and item["slot"] != "Other":
            items.append(item)
        else:
            skipped += 1

    # Sort by slot order then name
    slot_rank = {s: i for i, s in enumerate(SLOT_ORDER)}
    items.sort(key=lambda x: (slot_rank.get(x["slot"], 99), x["name"].lower()))

    print(f"  {len(items)} items rendered, {skipped} skipped (Other/untyped)")

    out_path = REPORTS_DIR / "armor_preview.html"
    html = generate_html(items)
    out_path.write_text(html, encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"  File size: {out_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    run()
