"""Crafting Calculator — generates an interactive HTML tool.
Input your mineral inventory → see which blueprints you can craft.
"""
import os
import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION, REPORTS_DIR

DATA_BASE = Path(os.environ.get("SC_DATA_BASE", str(REPO_ROOT / "EXPLORER_Data")))

BASE   = DATA_BASE / "Data" / "Libs" / "foundry" / "records" / "crafting"
LOC    = DATA_BASE / "Data" / "Localization" / "english" / "global.ini"
OUTPUT = REPORTS_DIR / "crafting_calculator.html"

# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------
def load_loc(path):
    data = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.split(",")[0].strip().lstrip("@")
            data[key.lower()] = val.strip()
    return data

LOC_DATA = load_loc(LOC)
def loc(key):
    k = key.lstrip("@").lower()
    return LOC_DATA.get(k, key)

# ---------------------------------------------------------------------------
# Resource UUID -> mineral name (from DataCore ResourceType sub-records)
# ---------------------------------------------------------------------------
RESOURCE_NAMES = {
    "06cafea0-49fe-4dce-b0f0-dc583316c66d": "Taranite",
    "07570c9f-fdf6-4bca-a56b-c42809ec0e01": "Titanium",
    "1b4c4042-5fdc-4b52-bec4-07085cb3520a": "Tin",
    "21825507-7923-4683-9bf3-9cfe316940e3": "Gold",
    "35121003-f1af-481a-b16f-7f48d8af0efb": "Quartz",
    "392b4dca-449a-4d4d-8fef-beab024d9ee7": "Lindinium",
    "4236c16b-c47f-4083-9e26-4313733f2326": "Corundum",
    "48c7080a-bbef-43d2-901a-698321ed4340": "Aluminum",
    "4a47cad8-0271-4048-b19b-d9b52521fc20": "Savrilium",
    "60f116f4-c02a-45b2-9ded-333747795124": "Tungsten",
    "61189578-ed7a-4491-9774-37ae2f82b8b0": "Hephaestanite",
    "75b37a54-45c9-4f27-ac09-9830f092dd86": "Torite",
    "7bbd3197-a6e1-49b3-a495-0b7ef4f8ce40": "Silicon",
    "7f4599b0-a2b2-4178-8c7e-13292054ab20": "Laranite",
    "86d00bd8-08f7-4231-b375-a609803fc46d": "Riccite",
    "8cd317a3-df9b-4315-8ac3-0f1fca42dfd4": "Stileron",
    "93c8b7df-d6ac-4b4f-a115-b0e3afc238b8": "Beryl",
    "97f623df-e359-4d51-b819-91644b31ead2": "Steel",
    "989f9b73-f636-4f35-a81d-579dcbe3f0ab": "Ouratite",
    "9dc16af8-bfb9-4119-9e54-6db11b0a7ed2": "Carbon",
    "a789f57a-e12b-4bcd-8132-e0c03d84fc89": "Copper",
    "dc6fbcbb-5990-4ed5-82ee-93152dab7845": "Agricium",
    "f386a33c-ac9a-400a-a7b8-fe1fc7c8d270": "Iron",
    "fde0cd65-8827-4b23-804d-cc8845dfa7ac": "Aslarite",
}

ARMOR_PARTS  = {"arms", "core", "helmet", "legs", "undersuit", "backpack", "suit"}
WEIGHT_CLASS = {"heavy", "medium", "light"}
TINT_WORDS   = {"tint", "black", "blue", "red", "green", "tan", "grey", "yellow",
                "white", "brown", "orange", "purple", "pink", "gold", "silver",
                "shrike", "talon", "civilian", "firerats", "xenothreat", "9tails",
                "orbageddon", "stormbreaker", "darkwater"}

# ---------------------------------------------------------------------------
# Blueprint name parser
# ---------------------------------------------------------------------------
def parse_bp_name(stem, folder_parts=None):
    s     = re.sub(r"^bp_craft_", "", stem, flags=re.I).lower()
    parts = s.split("_")
    is_armor = "armor" in parts or "armour" in parts
    is_mag   = parts[-1] == "mag" or (len(parts) > 1 and parts[-1].endswith("mag"))

    if is_armor:
        ai        = next((i for i, p in enumerate(parts) if p in ("armor","armour")), -1)
        pre_armor = parts[:ai]
        post_armor = parts[ai+1:]
        mfr       = pre_armor[0].upper() if pre_armor else "UNK"
        weight = part = ""
        rest   = []
        for tok in pre_armor[1:] + post_armor:
            if tok in WEIGHT_CLASS and not weight: weight = tok.title()
            elif tok in ARMOR_PARTS and not part:  part = tok.title()
            else: rest.append(tok)
        variant    = next((t for t in rest if t.isdigit() or re.match(r"^\d", t)), "01")
        tint_parts = [t for t in rest if t in TINT_WORDS]
        set_extras = [t for t in rest if t not in TINT_WORDS and not t.isdigit() and not re.match(r"^\d+$", t)]
        tint       = " ".join(tint_parts).title() if tint_parts else ""
        extras_str = " ".join(t.title() for t in set_extras)
        family     = re.sub(r"\s+", " ", f"{mfr} {extras_str} {weight} Armor").strip()
        return {"major":"Armour","mfr":mfr,"family":family,"weight":weight,
                "part":part or "Unknown","tint":tint,"is_base":not bool(tint),"is_mag":False}

    elif is_mag:
        mfr   = parts[0].upper() if parts else "UNK"
        wtype = parts[1].title() if len(parts) > 1 else ""
        ammo  = parts[2].title() if len(parts) > 2 else ""
        return {"major":"Ammo","mfr":mfr,"family":f"{mfr} {wtype} {ammo}".strip(),
                "weight":"","part":"Magazine","tint":"","is_base":True,"is_mag":True}
    else:
        mfr   = parts[0].upper() if parts else "UNK"
        wtype = parts[1].title() if len(parts) > 1 else ""
        ammo  = parts[2].title() if len(parts) > 2 else ""
        vp    = parts[3:]
        tint_parts = [p for p in vp if p in TINT_WORDS]
        tint       = " ".join(tint_parts).title() if tint_parts else ""
        family     = f"{mfr} {wtype} {ammo}".strip()
        return {"major":"Weapons","mfr":mfr,"family":family,"weight":"",
                "part":f"{wtype} {ammo}".strip(),"tint":tint,"is_base":not bool(tint),"is_mag":False}

# ---------------------------------------------------------------------------
# Parse folder -> major override
# ---------------------------------------------------------------------------
def major_from_path(xml_file, bp_root):
    parts = xml_file.relative_to(bp_root).parts
    if parts and parts[0] in ("armour","armor"): return "Armour"
    if parts and parts[0] == "weapons":          return "Weapons"
    if parts and parts[0] == "ammo":             return "Ammo"
    return None

# ---------------------------------------------------------------------------
# Parse a blueprint XML — extract material slots
# ---------------------------------------------------------------------------
def craft_time_str(costs_el):
    ct = costs_el.find(".//craftTime") if costs_el is not None else None
    if ct is None: return ""
    d,h,m = int(ct.get("days",0)),int(ct.get("hours",0)),int(ct.get("minutes",0))
    s = float(ct.get("seconds",0))
    p = []
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    if s and not (d or h or m): p.append(f"{int(s)}s")
    return " ".join(p) or ""

def parse_slots(mandatory):
    slots = []
    seen  = set()
    if mandatory is None: return slots
    for sel in mandatory.findall(".//CraftingCost_Select"):
        name_el = sel.find("nameInfo")
        if name_el is None: continue
        debug   = name_el.get("debugName","").strip().rstrip(":")
        display = name_el.get("displayName","")
        sname   = loc(display) if display.startswith("@") else debug.title()
        if not sname or sname.upper() in ("ASPECTS",) or sname in seen: continue
        seen.add(sname)
        qty = 0.0
        mineral = ""
        res_el  = sel.find(".//CraftingCost_Resource")
        if res_el is not None:
            res_uuid = res_el.get("resource","")
            mineral  = RESOURCE_NAMES.get(res_uuid,"")
            qty_el   = res_el.find(".//quantity")
            if qty_el is not None:
                qty = float(qty_el.get("standardCargoUnits",0))
        if qty > 0:
            slots.append({"slot": sname, "mineral": mineral, "qty": round(qty, 4)})
    return slots

# ---------------------------------------------------------------------------
# Gather all BASE blueprints
# ---------------------------------------------------------------------------
bp_root    = BASE / "blueprints/crafting/fpsgear"
blueprints = []

for xml_file in sorted(bp_root.rglob("*.xml")):
    stem = xml_file.stem
    if "template" in stem.lower() or stem.lower().startswith("test"): continue
    meta = parse_bp_name(stem)
    folder_major = major_from_path(xml_file, bp_root)
    if folder_major:
        meta["major"] = folder_major

    # Fixup: armour-folder blueprints without "armor" in filename
    sl = stem.lower()
    if (folder_major == "Armour" and "armor" not in sl and "armour" not in sl and not meta.get("is_mag")):
        toks   = re.sub(r"^bp_craft_","",stem,flags=re.I).lower().split("_")
        mfr_t  = toks[0].upper()
        rel    = xml_file.relative_to(bp_root).parts
        wt     = rel[2].title() if len(rel)>2 and rel[2] in WEIGHT_CLASS else \
                 next((t.title() for t in toks if t in WEIGHT_CLASS),"")
        part_t = next((t.title() for t in toks if t in ARMOR_PARTS),"Unknown")
        stop   = next((i for i,t in enumerate(toks) if t in WEIGHT_CLASS or t in ARMOR_PARTS or re.match(r"^\d",t)),len(toks))
        extras = [t.title() for t in toks[1:stop] if t not in WEIGHT_CLASS and t not in ARMOR_PARTS]
        tint_t = " ".join(t.title() for t in toks if t in TINT_WORDS)
        family_t = re.sub(r"\s+"," ",f"{mfr_t} {' '.join(extras)} {wt} Armor").strip()
        meta.update({"mfr":mfr_t,"family":family_t,"weight":wt,"part":part_t,
                     "tint":tint_t,"is_base":not bool(tint_t),"is_mag":False})

    # Only keep BASE blueprints (not tint/color variants)
    if not meta.get("is_base", False): continue

    try:
        root = ET.parse(xml_file).getroot()
    except ET.ParseError:
        continue
    bp_el = root.find("blueprint")
    if bp_el is None: continue
    tier     = bp_el.find(".//CraftingBlueprintTier")
    recipe   = tier.find("recipe") if tier is not None else None
    costs_el = recipe.find("costs") if recipe is not None else None
    ct       = craft_time_str(costs_el)
    mandatory = costs_el.find("mandatoryCost") if costs_el is not None else None
    slots    = parse_slots(mandatory)
    if not slots: continue  # skip blueprints with no material requirements

    # Aggregate materials: {mineral -> total_qty}
    materials = defaultdict(float)
    mat_slots = []
    for s in slots:
        if s["mineral"]:
            materials[s["mineral"]] += s["qty"]
            mat_slots.append({"slot": s["slot"], "mineral": s["mineral"], "qty": s["qty"]})

    if not mat_slots: continue

    # Display name
    major  = meta["major"]
    mfr    = meta["mfr"]
    family = meta["family"]
    part   = meta.get("part","")
    weight = meta.get("weight","")

    if major == "Armour":
        display = f"{family} — {part}" if part and part != "Unknown" else family
    elif major == "Ammo":
        display = family
    else:
        display = family

    blueprints.append({
        "id":       stem,
        "display":  display,
        "major":    major,
        "mfr":      mfr,
        "family":   family,
        "part":     part,
        "weight":   weight,
        "time":     ct,
        "materials": [{"slot": k["slot"], "mineral": k["mineral"], "qty": k["qty"]} for k in mat_slots],
        "totals":   {m: round(q, 4) for m, q in materials.items()},
    })

print(f"Parsed {len(blueprints)} base blueprints")

# Collect all minerals actually used
all_minerals = sorted(set(
    m for bp in blueprints for m in bp["totals"].keys()
))
print(f"Minerals used: {len(all_minerals)} -> {all_minerals}")

# ---------------------------------------------------------------------------
# Embed data into HTML
# ---------------------------------------------------------------------------
bp_json      = json.dumps(blueprints, separators=(",",":"))
mineral_json = json.dumps(all_minerals, separators=(",",":"))

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC Crafting Calculator — {GAME_VERSION}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --accent:     #532CD8;
  --accent-hover: #6B44E8;
  --accent-dim: rgba(83,44,216,0.35);
  --accent-glow: rgba(83,44,216,0.15);
  --bg:    #13141A;
  --bg2:   #15171D;
  --bg3:   #2E3144;
  --bg4:   #363A52;
  --border:  #3A3F56;
  --border2: #4A5270;
  --text:  #FFFFFF;
  --text2: #CCCCCC;
  --text3: #888888;
  --green: #4ade9a;
  --green-bg: rgba(74,222,154,.10);
  --amber: #f5a742;
  --amber-bg: rgba(245,167,66,.10);
  --red: #ef4444;
  --red-bg: rgba(239,68,68,.08);
  --radius: 10px;
  --sidebar: 320px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}}
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #333; border-radius: 3px; }}

/* ── HEADER ── */
.header {{
  background: linear-gradient(to right, #1A1C26 0%, #15171D 100%);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
  z-index: 10;
}}
.logo {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 17px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #fff;
  white-space: nowrap;
}}
.logo .o {{ color: var(--accent); }}
.header-title {{
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.06em;
  color: var(--text2);
  border-left: 1px solid var(--border2);
  padding-left: 20px;
}}
.header-title span {{ color: var(--accent); }}
.header-right {{
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}}
.version-badge {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text3);
  border: 1px solid var(--border2);
  padding: 3px 8px;
  border-radius: 4px;
}}
.stat-pill {{
  font-size: 11px;
  color: var(--text2);
  border: 1px solid var(--border);
  background: var(--bg3);
  padding: 4px 10px;
  border-radius: 4px;
}}
.stat-pill strong {{ color: var(--accent); }}

/* ── LAYOUT ── */
.layout {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}

/* ── SIDEBAR ── */
.sidebar {{
  width: var(--sidebar);
  flex-shrink: 0;
  background: var(--bg2);
  border-right: 1px solid var(--border2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.sidebar-head {{
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
.sidebar-label {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
}}
.sidebar-label::before {{
  content: '';
  display: block;
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 2px;
  flex-shrink: 0;
}}
.total-bar {{
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  padding: 10px 12px;
  display: flex;
  gap: 16px;
}}
.total-item {{
  text-align: center;
  flex: 1;
}}
.total-item .n {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 20px;
  display: block;
}}
.total-item .n.green {{ color: var(--green); }}
.total-item .n.amber {{ color: var(--amber); }}
.total-item .n.grey  {{ color: var(--text3); }}
.total-item .lbl {{
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text3);
  font-weight: 600;
}}

.sidebar-scroll {{
  flex: 1;
  overflow-y: auto;
  padding: 10px 0 6px;
}}

/* ── MINERAL TILE GRID ── */
.mineral-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
  padding: 0 12px;
}}
.mineral-card {{
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 9px 7px;
  cursor: default;
  transition: border-color .15s, background .15s;
  position: relative;
}}
.mineral-card:hover {{ border-color: var(--border2); }}
.mineral-card.active {{
  border-color: var(--accent-dim);
  background: rgba(232,197,71,.05);
}}
.m-head {{
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
}}
.m-gem {{
  width: 8px;
  height: 8px;
  border-radius: 2px;
  transform: rotate(45deg);
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity .2s, box-shadow .2s;
}}
.mineral-card.active .m-gem {{
  opacity: 1;
  box-shadow: 0 0 5px currentColor;
}}
.m-name {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 9px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  transition: color .15s;
}}
.mineral-card.active .m-name {{ color: var(--text2); }}
.m-val-wrap {{
  display: flex;
  align-items: baseline;
  gap: 3px;
  margin-bottom: 7px;
  justify-content: center;
}}
.m-val-input {{
  background: transparent;
  border: none;
  outline: none;
  font-family: 'Geist Mono', monospace;
  font-size: 15px;
  font-weight: 600;
  color: var(--text3);
  text-align: center;
  width: 72px;
  cursor: text;
  transition: color .15s;
  padding: 0;
  -moz-appearance: textfield;
}}
.m-val-input::-webkit-inner-spin-button,
.m-val-input::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}
.mineral-card.active .m-val-input {{ color: var(--accent); }}
.m-scu {{
  font-size: 8px;
  color: var(--text3);
  letter-spacing: 0.07em;
  text-transform: uppercase;
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  flex-shrink: 0;
}}
.m-slider {{
  -webkit-appearance: none;
  width: 100%;
  height: 3px;
  background: var(--bg4);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
  display: block;
}}
.m-slider::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--border2);
  cursor: pointer;
  transition: background .15s, transform .15s;
  border: 1px solid var(--border2);
}}
.mineral-card.active .m-slider::-webkit-slider-thumb {{
  background: var(--accent);
  border-color: var(--accent);
  transform: scale(1.1);
}}
.m-slider::-moz-range-thumb {{
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--border2);
  cursor: pointer;
  border: 1px solid var(--border2);
}}

.sidebar-foot {{
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 8px;
}}
.btn-clear {{
  flex: 1;
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  background: transparent;
  color: var(--text3);
  border: 1px solid var(--border2);
  padding: 8px;
  border-radius: 5px;
  cursor: pointer;
  transition: all .15s;
}}
.btn-clear:hover {{ color: var(--text); border-color: var(--text2); }}

.btn-fill-example {{
  flex: 1;
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: var(--accent-glow);
  color: var(--accent);
  border: 1px solid var(--accent-dim);
  padding: 8px;
  border-radius: 5px;
  cursor: pointer;
  transition: all .15s;
}}
.btn-fill-example:hover {{ background: rgba(232,197,71,.2); }}

/* ── MAIN CONTENT ── */
.main {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ── TOOLBAR ── */
.toolbar {{
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  background: #1A1C26;
}}
.search-wrap {{
  position: relative;
  flex: 1;
  max-width: 300px;
}}
.search-wrap input {{
  width: 100%;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: 5px;
  padding: 7px 10px 7px 30px;
  color: var(--text);
  font-family: 'Outfit', sans-serif;
  font-size: 12px;
  outline: none;
  transition: border-color .15s;
}}
.search-wrap input:focus {{ border-color: var(--accent); }}
.search-wrap input::placeholder {{ color: var(--text3); }}
.search-icon {{
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text3);
  font-size: 12px;
  pointer-events: none;
}}

.filter-group {{
  display: flex;
  gap: 4px;
  margin-left: 8px;
}}
.filter-btn {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--text2);
  padding: 6px 14px;
  border-radius: 5px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}}
.filter-btn:hover {{ color: var(--text); border-color: var(--text2); }}
.filter-btn.active {{ background: var(--bg4); color: var(--text); border-color: var(--text2); }}
.filter-btn.f-can {{ border-color: var(--green); color: var(--green); background: var(--green-bg); }}
.filter-btn.f-partial {{ border-color: var(--amber); color: var(--amber); background: var(--amber-bg); }}

.sort-select {{
  margin-left: auto;
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--text2);
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 6px 10px;
  border-radius: 5px;
  outline: none;
  cursor: pointer;
}}
.sort-select option {{ background: var(--bg2); }}

/* ── BLUEPRINT LIST ── */
.bp-scroll {{
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}}

.group-header {{
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text3);
  padding: 4px 0 8px;
  margin-top: 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}
.group-count {{
  font-size: 10px;
  color: var(--text3);
  font-weight: 500;
}}

.bp-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 8px;
  margin-bottom: 20px;
}}

.bp-card {{
  background: linear-gradient(168deg, #232634 0%, #191B25 77%);
  outline: 0.5px solid #14141A;
  box-shadow: inset 0px 0.5px 0px #2B2E3B;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  transition: border-color .15s, box-shadow .15s;
  cursor: default;
}}
.bp-card:hover {{ border-color: var(--border2); box-shadow: inset 0px 0.5px 0px #3A3F56; }}
.bp-card.can-craft  {{ border-color: rgba(74,222,154,.35); box-shadow: inset 0px 0.5px 0px rgba(74,222,154,.2); }}
.bp-card.partial    {{ border-color: rgba(245,167,66,.35);  box-shadow: inset 0px 0.5px 0px rgba(245,167,66,.2); }}
.bp-card.cant-craft {{ opacity: 0.45; }}

.bp-head {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}}
.bp-name {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 14px;
  color: var(--text);
  line-height: 1.2;
  flex: 1;
}}
.bp-name .bp-part {{
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  letter-spacing: 0.04em;
  margin-top: 1px;
}}
.bp-badges {{
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}}
.badge {{
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 3px;
  white-space: nowrap;
}}
.badge-heavy  {{ background: rgba(232,84,84,.15);  color: #e85454; }}
.badge-medium {{ background: rgba(232,168,56,.15); color: #e8a838; }}
.badge-light  {{ background: rgba(84,200,122,.15); color: #54c87a; }}
.badge-status-can     {{ background: var(--green-bg); color: var(--green); border: 1px solid rgba(61,186,126,.3); }}
.badge-status-partial {{ background: var(--amber-bg); color: var(--amber); border: 1px solid rgba(224,145,58,.3); }}
.badge-status-cant    {{ background: rgba(80,80,80,.15); color: var(--text3); border: 1px solid var(--border); }}

.bp-materials {{
  display: flex;
  flex-direction: column;
  gap: 5px;
}}
.mat-row {{
  display: flex;
  align-items: center;
  gap: 8px;
}}
.mat-slot {{
  font-size: 10px;
  color: var(--text3);
  width: 110px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
.mat-bar-wrap {{
  flex: 1;
  height: 4px;
  background: var(--bg4);
  border-radius: 2px;
  overflow: hidden;
}}
.mat-bar {{
  height: 100%;
  border-radius: 2px;
  transition: width .3s ease;
}}
.mat-bar.full    {{ background: var(--green); }}
.mat-bar.partial {{ background: var(--amber); }}
.mat-bar.empty   {{ background: var(--bg4); width: 0 !important; }}
.mat-mineral {{
  font-size: 11px;
  font-weight: 500;
  color: var(--text2);
  width: 88px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.mat-qty {{
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text3);
  width: 44px;
  text-align: right;
  flex-shrink: 0;
  white-space: nowrap;
}}
.mat-qty.have    {{ color: var(--green); }}
.mat-qty.partial {{ color: var(--amber); }}

.bp-foot {{
  margin-top: 9px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}
.bp-time {{
  font-size: 10px;
  color: var(--text3);
  display: flex;
  align-items: center;
  gap: 4px;
}}
.craft-count {{
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--green);
  font-weight: 500;
}}

.no-results {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text3);
  gap: 8px;
  font-family: 'Outfit', sans-serif;
  font-size: 14px;
  letter-spacing: 0.06em;
}}
.no-results .icon {{ font-size: 32px; }}

</style>
</head>
<body>

<!-- ── HEADER ── -->
<header class="header">
  <div class="logo">SALADINS INFORMATION</div>
  <div class="header-title">Crafting Calculator &mdash; <span>SC {GAME_VERSION}</span></div>
  <div class="header-right">
    <div class="version-badge">DataCore {GAME_VERSION}</div>
    <div class="stat-pill"><strong id="bp-count">0</strong> blueprints</div>
    <div class="stat-pill"><strong id="mineral-count">0</strong> minerals tracked</div>
  </div>
</header>

<!-- ── LAYOUT ── -->
<div class="layout">

  <!-- ── SIDEBAR ── -->
  <aside class="sidebar">
    <div class="sidebar-head">
      <div class="sidebar-label">Your Resources</div>
      <div class="total-bar">
        <div class="total-item">
          <span class="n green" id="count-can">0</span>
          <span class="lbl">Can Craft</span>
        </div>
        <div class="total-item">
          <span class="n amber" id="count-partial">0</span>
          <span class="lbl">Partial</span>
        </div>
        <div class="total-item">
          <span class="n grey" id="count-cant">0</span>
          <span class="lbl">Missing</span>
        </div>
      </div>
    </div>

    <div class="sidebar-scroll" id="mineral-list"></div>

    <div class="sidebar-foot">
      <button class="btn-clear" onclick="clearAll()">Clear All</button>
      <button class="btn-fill-example" onclick="fillExample()">Try Example</button>
    </div>
  </aside>

  <!-- ── MAIN ── -->
  <div class="main">

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-icon">⌕</span>
        <input type="text" id="search-input" placeholder="Search blueprints..." oninput="render()">
      </div>
      <div class="filter-group">
        <button class="filter-btn active" data-filter="all"     onclick="setFilter('all',this)">All</button>
        <button class="filter-btn f-can"  data-filter="can"     onclick="setFilter('can',this)">✓ Can Craft</button>
        <button class="filter-btn"        data-filter="partial" onclick="setFilter('partial',this)">◑ Partial</button>
        <button class="filter-btn"        data-filter="cant"    onclick="setFilter('cant',this)">✗ Missing</button>
      </div>
      <select class="sort-select" id="sort-select" onchange="render()">
        <option value="status">Sort: Craftable First</option>
        <option value="alpha">Sort: A → Z</option>
        <option value="major">Sort: By Category</option>
        <option value="time">Sort: Craft Time</option>
      </select>
    </div>

    <!-- Blueprint list -->
    <div class="bp-scroll" id="bp-list"></div>

  </div>
</div>

<script>
// ── Embedded data ─────────────────────────────────────────────────
const BLUEPRINTS = {bp_json};
const MINERALS   = {mineral_json};

// ── State ─────────────────────────────────────────────────────────
let inventory = {{}};
let activeFilter = 'all';
let mineralMax = {{}};

// ── Mineral gem colors ─────────────────────────────────────────────
const GEM_COLORS = {{
  'Agricium':     '#84cc16',
  'Aluminum':     '#94a3b8',
  'Aslarite':     '#38bdf8',
  'Beryl':        '#10b981',
  'Carbon':       '#6b7280',
  'Copper':       '#c97b3a',
  'Corundum':     '#ef4444',
  'Gold':         '#fbbf24',
  'Hephaestanite':'#f97316',
  'Iron':         '#b45309',
  'Laranite':     '#7c3aed',
  'Lindinium':    '#fb923c',
  'Ouratite':     '#E8C547',
  'Quartz':       '#e879f9',
  'Riccite':      '#06b6d4',
  'Savrilium':    '#c026d3',
  'Silicon':      '#fde68a',
  'Steel':        '#64748b',
  'Stileron':     '#f59e0b',
  'Taranite':     '#a78bfa',
  'Tin':          '#9ca3af',
  'Titanium':     '#60a5fa',
  'Torite':       '#22c55e',
  'Tungsten':     '#475569',
}};

// ── Precompute max qty needed per mineral across all blueprints ────
function computeMineralMaxes() {{
  BLUEPRINTS.forEach(bp => {{
    Object.entries(bp.totals).forEach(([mineral, qty]) => {{
      mineralMax[mineral] = Math.max(mineralMax[mineral] || 0, qty);
    }});
  }});
  // Floor at 0.1 SCU so slider isn't uselessly tiny
  MINERALS.forEach(m => {{
    mineralMax[m] = Math.max(mineralMax[m] || 0.1, 0.1) * 1.5;
  }});
}}

// ── Build sidebar mineral tile grid ───────────────────────────────
function buildSidebar() {{
  computeMineralMaxes();
  const el = document.getElementById('mineral-list');
  const grid = document.createElement('div');
  grid.className = 'mineral-grid';

  MINERALS.forEach(m => {{
    const mid   = m.replace(/ /g, '_');
    const color = GEM_COLORS[m] || '#7d8590';
    const maxV  = mineralMax[m] || 1.0;

    const card = document.createElement('div');
    card.className  = 'mineral-card';
    card.id         = 'mcard-' + mid;
    card.innerHTML  = `
      <div class="m-head">
        <div class="m-gem" style="background:${{color}};color:${{color}}"></div>
        <div class="m-name" title="${{m}}">${{m}}</div>
      </div>
      <div class="m-val-wrap">
        <input class="m-val-input" type="number" min="0" step="0.001" value="0.000"
               data-mineral="${{m}}" oninput="onValInput(this,'${{m}}')">
        <span class="m-scu">SCU</span>
      </div>
      <input type="range" class="m-slider" min="0" max="${{maxV.toFixed(4)}}" step="0.0005"
             value="0" data-mineral="${{m}}" oninput="onSliderInput(this,'${{m}}')">`;
    grid.appendChild(card);
  }});

  el.appendChild(grid);
  document.getElementById('bp-count').textContent     = BLUEPRINTS.length;
  document.getElementById('mineral-count').textContent = MINERALS.length;
}}

function updateSliderFill(slider, val, max) {{
  const pct = max > 0 ? Math.min(val / max * 100, 100) : 0;
  slider.style.background =
    `linear-gradient(to right,var(--accent) 0%,var(--accent) ${{pct}}%,var(--bg4) ${{pct}}%,var(--bg4) 100%)`;
}}

function setCardActive(mineral, val) {{
  const card = document.getElementById('mcard-' + mineral.replace(/ /g,'_'));
  if (!card) return;
  if (val > 0) card.classList.add('active');
  else         card.classList.remove('active');
}}

function onValInput(input, mineral) {{
  const val = Math.max(parseFloat(input.value) || 0, 0);
  inventory[mineral] = val;
  const card   = document.getElementById('mcard-' + mineral.replace(/ /g,'_'));
  if (card) {{
    const slider = card.querySelector('.m-slider');
    if (slider) {{
      slider.value = Math.min(val, parseFloat(slider.max));
      updateSliderFill(slider, val, parseFloat(slider.max));
    }}
  }}
  setCardActive(mineral, val);
  render();
}}

function onSliderInput(slider, mineral) {{
  const val = parseFloat(slider.value) || 0;
  inventory[mineral] = val;
  const card = document.getElementById('mcard-' + mineral.replace(/ /g,'_'));
  if (card) {{
    const vi = card.querySelector('.m-val-input');
    if (vi) vi.value = val.toFixed(3);
  }}
  updateSliderFill(slider, val, parseFloat(slider.max));
  setCardActive(mineral, val);
  render();
}}

// ── Evaluate a blueprint against current inventory ────────────────
function evaluate(bp) {{
  // Group required materials
  const needed = bp.totals;  // {{mineral: qty}}
  let canAll = true, anyHave = false;
  const detail = {{}};
  for (const [mineral, qty] of Object.entries(needed)) {{
    const have = inventory[mineral] || 0;
    const ratio = qty > 0 ? Math.min(have / qty, 1) : 1;
    detail[mineral] = {{ have, need: qty, ratio }};
    if (ratio < 1) canAll = false;
    if (have > 0) anyHave = true;
  }}
  const status = canAll ? 'can' : (anyHave ? 'partial' : 'cant');
  // How many can we craft?
  let count = Infinity;
  for (const [mineral, qty] of Object.entries(needed)) {{
    const have = inventory[mineral] || 0;
    count = Math.min(count, qty > 0 ? Math.floor(have / qty) : Infinity);
  }}
  return {{ status, detail, count: isFinite(count) ? count : 0 }};
}}

// ── Filter / sort / render ────────────────────────────────────────
function setFilter(f, btn) {{
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active','f-can'));
  btn.classList.add('active');
  if (f === 'can') btn.classList.add('f-can');
  render();
}}

function render() {{
  const query = document.getElementById('search-input').value.toLowerCase().trim();
  const sort  = document.getElementById('sort-select').value;

  // Evaluate all
  const evaluated = BLUEPRINTS.map(bp => ({{ bp, ev: evaluate(bp) }}));

  // Tally
  const nCan     = evaluated.filter(x => x.ev.status === 'can').length;
  const nPartial = evaluated.filter(x => x.ev.status === 'partial').length;
  const nCant    = evaluated.filter(x => x.ev.status === 'cant').length;
  document.getElementById('count-can').textContent     = nCan;
  document.getElementById('count-partial').textContent = nPartial;
  document.getElementById('count-cant').textContent    = nCant;

  // Filter
  let visible = evaluated.filter(x => {{
    if (activeFilter === 'can'     && x.ev.status !== 'can')     return false;
    if (activeFilter === 'partial' && x.ev.status !== 'partial') return false;
    if (activeFilter === 'cant'    && x.ev.status !== 'cant')    return false;
    if (query && !x.bp.display.toLowerCase().includes(query) &&
                 !x.bp.family.toLowerCase().includes(query) &&
                 !x.bp.mfr.toLowerCase().includes(query))        return false;
    return true;
  }});

  // Sort
  const statusOrder = {{ can: 0, partial: 1, cant: 2 }};
  if (sort === 'status') {{
    visible.sort((a, b) => statusOrder[a.ev.status] - statusOrder[b.ev.status]
                        || a.bp.display.localeCompare(b.bp.display));
  }} else if (sort === 'alpha') {{
    visible.sort((a, b) => a.bp.display.localeCompare(b.bp.display));
  }} else if (sort === 'major') {{
    visible.sort((a, b) => a.bp.major.localeCompare(b.bp.major)
                        || a.bp.family.localeCompare(b.bp.family)
                        || a.bp.part.localeCompare(b.bp.part));
  }} else if (sort === 'time') {{
    visible.sort((a, b) => (a.bp.time || '').localeCompare(b.bp.time || ''));
  }}

  buildList(visible);
}}

function buildList(items) {{
  const container = document.getElementById('bp-list');
  container.innerHTML = '';

  if (items.length === 0) {{
    container.innerHTML = '<div class="no-results"><span class="icon">◈</span>No blueprints match your filters</div>';
    return;
  }}

  // Group by major
  const byMajor = {{}};
  items.forEach(x => {{
    const key = x.bp.major;
    if (!byMajor[key]) byMajor[key] = [];
    byMajor[key].push(x);
  }});

  const ORDER = ['Armour', 'Weapons', 'Ammo'];
  const sortedMajors = ORDER.filter(m => byMajor[m]);

  sortedMajors.forEach(major => {{
    const group = byMajor[major];
    const gh = document.createElement('div');
    gh.className = 'group-header';
    const canC = group.filter(x=>x.ev.status==='can').length;
    gh.innerHTML = `<span>${{major.toUpperCase()}}</span>
      <span class="group-count">${{canC > 0 ? canC + ' craftable / ':''}}${{group.length}} total</span>`;
    container.appendChild(gh);

    const grid = document.createElement('div');
    grid.className = 'bp-grid';

    group.forEach(({{bp, ev}}) => {{
      const card = buildCard(bp, ev);
      grid.appendChild(card);
    }});
    container.appendChild(grid);
  }});
}}

function buildCard(bp, ev) {{
  const card = document.createElement('div');
  card.className = 'bp-card ' + (ev.status === 'can' ? 'can-craft' : ev.status === 'partial' ? 'partial' : 'cant-craft');

  // Weight badge
  const wBadge = bp.weight
    ? `<span class="badge badge-${{bp.weight.toLowerCase()}}">${{bp.weight}}</span>` : '';

  // Status badge
  const sBadge = ev.status === 'can'
    ? `<span class="badge badge-status-can">✓ Can Craft</span>`
    : ev.status === 'partial'
    ? `<span class="badge badge-status-partial">◑ Partial</span>`
    : `<span class="badge badge-status-cant">✗ Missing</span>`;

  // Part line
  const partLine = (bp.major === 'Armour' && bp.part && bp.part !== 'Unknown')
    ? `<span class="bp-part">${{bp.mfr}} · ${{bp.part}}</span>` : '';

  // Materials
  let matsHtml = '';
  bp.materials.forEach(mat => {{
    const d = ev.detail[mat.mineral] || {{ have: 0, need: mat.qty, ratio: 0 }};
    const pct = Math.round(d.ratio * 100);
    const barClass = d.ratio >= 1 ? 'full' : d.ratio > 0 ? 'partial' : 'empty';
    const qtyClass = d.ratio >= 1 ? 'have' : d.ratio > 0 ? 'partial' : '';
    const haveStr  = d.have > 0 ? d.have.toFixed(4) : '0';
    const needStr  = mat.qty.toFixed(4);
    matsHtml += `
      <div class="mat-row">
        <div class="mat-slot" title="${{mat.slot}}">${{mat.slot}}</div>
        <div class="mat-bar-wrap"><div class="mat-bar ${{barClass}}" style="width:${{pct}}%"></div></div>
        <div class="mat-mineral" title="${{mat.mineral}}">${{mat.mineral}}</div>
        <div class="mat-qty ${{qtyClass}}">${{d.have > 0 || d.ratio >= 1 ? haveStr + '/' : ''}}${{needStr}}</div>
      </div>`;
  }});

  // Craft count
  const countHtml = ev.count > 0
    ? `<span class="craft-count">×${{ev.count}} craftable</span>` : '';

  card.innerHTML = `
    <div class="bp-head">
      <div class="bp-name">${{bp.family}}${{partLine}}</div>
      <div class="bp-badges">${{wBadge}}${{sBadge}}</div>
    </div>
    <div class="bp-materials">${{matsHtml}}</div>
    <div class="bp-foot">
      <div class="bp-time">${{bp.time ? '⧗ ' + bp.time : ''}}</div>
      ${{countHtml}}
    </div>`;
  return card;
}}

// ── Clear / example ───────────────────────────────────────────────
function clearAll() {{
  inventory = {{}};
  document.querySelectorAll('.m-val-input').forEach(i => {{ i.value = '0.000'; }});
  document.querySelectorAll('.m-slider').forEach(s => {{
    s.value = 0;
    updateSliderFill(s, 0, parseFloat(s.max));
  }});
  document.querySelectorAll('.mineral-card').forEach(c => c.classList.remove('active'));
  render();
}}

function fillExample() {{
  // Realistic mining haul
  const example = {{
    'Hephaestanite': 0.15,
    'Ouratite':      0.25,
    'Aslarite':      0.12,
    'Tungsten':      0.10,
    'Taranite':      0.08,
    'Iron':          0.06,
    'Aluminum':      0.05,
  }};
  clearAll();
  Object.entries(example).forEach(([m, qty]) => {{
    inventory[m] = qty;
    const card = document.getElementById('mcard-' + m.replace(/ /g,'_'));
    if (card) {{
      const vi     = card.querySelector('.m-val-input');
      const slider = card.querySelector('.m-slider');
      if (vi) vi.value = qty.toFixed(3);
      if (slider) {{
        slider.value = Math.min(qty, parseFloat(slider.max));
        updateSliderFill(slider, qty, parseFloat(slider.max));
      }}
      card.classList.add('active');
    }}
  }});
  // Switch to "can craft" filter to show results immediately
  const canBtn = document.querySelector('[data-filter="can"]');
  if (canBtn) setFilter('can', canBtn);
  render();
}}

// ── Init ──────────────────────────────────────────────────────────
buildSidebar();
render();
</script>
</body>
</html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"Written: {OUTPUT}")
print(f"  {len(blueprints)} base blueprints embedded")
print(f"  {len(all_minerals)} minerals tracked")
