"""Crafting report — granular breakdown by item family, part, variant, slots + stat modifiers."""
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "SCRIPTS"))
from config.settings import GAME_VERSION, REPORTS_DIR

DATA_BASE = Path(os.environ.get("SC_DATA_BASE", str(REPO_ROOT / "EXPLORER_Data")))

BASE   = DATA_BASE / "Data" / "Libs" / "foundry" / "records" / "crafting"
LOC    = DATA_BASE / "Data" / "Localization" / "english" / "global.ini"
OUTPUT = REPORTS_DIR / "crafting_report.html"

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
# Crafted property UUID -> stat name
# ---------------------------------------------------------------------------
STAT_PROPS = {}  # uuid -> human name
for f in sorted((BASE / "craftedproperties").glob("*.xml")):
    try:
        root = ET.parse(f).getroot()
        uid  = root.get("__id", "")
        pname = root.get("propertyName", "")
        if uid:
            STAT_PROPS[uid] = loc(pname) if pname else f.stem.replace("gpp_", "").replace("_", " ").title()
    except ET.ParseError:
        pass

# ---------------------------------------------------------------------------
# Crafting resource UUID -> mineral name
# Source: ResourceType sub-records in DataCore (resourcetypedatabase.xml)
# All 25 resolved directly from game data via scdatatools
# ---------------------------------------------------------------------------
RESOURCE_NAMES = {
    "06cafea0-49fe-4dce-b0f0-dc583316c66d": "Taranite",       # Shot, Segment Paneling, Frame (sniper)
    "07570c9f-fdf6-4bca-a56b-c42809ec0e01": "Titanium",       # Casing Weave, Support Structure
    "1b4c4042-5fdc-4b52-bec4-07085cb3520a": "Tin",            # Casing (backpack)
    "21825507-7923-4683-9bf3-9cfe316940e3": "Gold",           # Cabling (Volt), Charge Chamber (energy ammo)
    "35121003-f1af-481a-b16f-7f48d8af0efb": "Quartz",         # Internal Array (energy ammo)
    "392b4dca-449a-4d4d-8fef-beab024d9ee7": "Lindinium",      # Frame (LMG/pistol energy), Support Structure
    "3e5fdc37-cb59-4fd3-8168-e3c538ab9722": "Hadanite",       # (test records only)
    "4236c16b-c47f-4083-9e26-4313733f2326": "Corundum",       # Plating (starwear), Frame (energy rifle/SMG)
    "48c7080a-bbef-43d2-901a-698321ed4340": "Aluminum",       # Frame (ballistic pistol/rifle)
    "4a47cad8-0271-4048-b19b-d9b52521fc20": "Savrilium",      # Casing Weave, Support Structure (utility armor)
    "60f116f4-c02a-45b2-9ded-333747795124": "Tungsten",       # Core, Protective Sheathing, Frame (energy)
    "61189578-ed7a-4491-9774-37ae2f82b8b0": "Hephaestanite",  # Magazine, Stock, Grip
    "75b37a54-45c9-4f27-ac09-9830f092dd86": "Torite",         # Frame (shotguns)
    "7bbd3197-a6e1-49b3-a495-0b7ef4f8ce40": "Silicon",        # Suit Underlay (flightsuits)
    "7f4599b0-a2b2-4178-8c7e-13292054ab20": "Laranite",       # Casing, Sheathing Coating (specialist armor)
    "86d00bd8-08f7-4231-b375-a609803fc46d": "Riccite",        # Panel Covering, Plating Barrier, Frame
    "8cd317a3-df9b-4315-8ac3-0f1fca42dfd4": "Stileron",       # Shell, Support Structure (env armor)
    "93c8b7df-d6ac-4b4f-a115-b0e3afc238b8": "Beryl",          # Conduit (energy rifle)
    "97f623df-e359-4d51-b819-91644b31ead2": "Steel",          # Aspect slots (weapon attachments)
    "989f9b73-f636-4f35-a81d-579dcbe3f0ab": "Ouratite",       # Armoured Carapace
    "9dc16af8-bfb9-4119-9e54-6db11b0a7ed2": "Carbon",         # Aspect slots (weapon attachments)
    "a789f57a-e12b-4bcd-8132-e0c03d84fc89": "Copper",         # Conduit Channel, Wiring (energy weapons)
    "dc6fbcbb-5990-4ed5-82ee-93152dab7845": "Agricium",       # Support Structure (legacy armor)
    "f386a33c-ac9a-400a-a7b8-fe1fc7c8d270": "Iron",           # Barrel (all ballistic weapons)
    "fde0cd65-8827-4b23-804d-cc8845dfa7ac": "Aslarite",       # Insulative Liner
}

# ---------------------------------------------------------------------------
# Parse blueprint filename into structured parts
# ---------------------------------------------------------------------------
# Armor patterns:  bp_craft_{set}_{weight}_armor_{part}_{v1}_{v2}_{color}
#                  bp_craft_{set}_armor_{weight}_{part}_{v1}_{v2}_{color}
# Weapon patterns: bp_craft_{mfr}_{type}_{ammo}_{variant}_{tint}
# Ammo patterns:   bp_craft_{mfr}_{type}_{ammo}_{variant}_mag

ARMOR_PARTS  = {"arms", "core", "helmet", "legs", "undersuit", "backpack", "suit"}
WEIGHT_CLASS = {"heavy", "medium", "light"}
TINT_WORDS   = {"tint", "black", "blue", "red", "green", "tan", "grey", "yellow",
                "white", "brown", "orange", "purple", "pink", "gold", "silver",
                "shrike", "talon", "civilian", "firerats", "xenothreat", "9tails",
                "orbageddon", "stormbreaker", "darkwater"}

def parse_bp_name(stem):
    """Parse a blueprint stem into structured metadata."""
    s = re.sub(r"^bp_craft_", "", stem, flags=re.I).lower()
    parts = s.split("_")

    # Detect if armor
    is_armor  = "armor" in parts or "armour" in parts
    is_mag    = parts[-1] == "mag" or (len(parts) > 1 and parts[-1].endswith("mag"))

    if is_armor:
        # Find armor index
        ai = next((i for i, p in enumerate(parts) if p in ("armor","armour")), -1)
        pre_armor = parts[:ai]   # e.g. ['cds'] or ['ccc','medium'] or ['outlaw','legacy']
        post_armor = parts[ai+1:]  # e.g. ['heavy','arms','01','01','01']

        # Manufacturer = first token before armor (or weight)
        mfr = pre_armor[0].upper() if pre_armor else "UNK"
        # Weight may be before or after 'armor'
        weight = ""
        part   = ""
        rest   = []
        remaining = pre_armor[1:] + post_armor
        for tok in remaining:
            if tok in WEIGHT_CLASS and not weight: weight = tok.title()
            elif tok in ARMOR_PARTS and not part: part = tok.title()
            else: rest.append(tok)

        # Tint = ONLY explicit tint keywords; non-numeric non-tint tokens are set-name extras
        variant    = next((t for t in rest if t.isdigit() or re.match(r"^\d", t)), "01")
        tint_parts = [t for t in rest if t in TINT_WORDS]
        set_extras = [t for t in rest if t not in TINT_WORDS and not t.isdigit() and not re.match(r"^\d+$", t)]
        tint       = " ".join(tint_parts).title() if tint_parts else ""
        # Set-name extras (e.g. "legacy", "env", "utility") go into family name
        extras_str = " ".join(t.title() for t in set_extras)
        family     = re.sub(r"\s+", " ", f"{mfr} {extras_str} {weight} Armor").strip()

        return {
            "major":   "Armour",
            "mfr":     mfr,
            "family":  family,
            "weight":  weight,
            "part":    part or "Unknown",
            "variant": variant,
            "tint":    tint,
            "is_base": not bool(tint),
            "is_mag":  False,
        }

    elif is_mag:
        # Magazine blueprint
        mfr  = parts[0].upper() if parts else "UNK"
        wtype = parts[1].title() if len(parts) > 1 else ""
        ammo  = parts[2].title() if len(parts) > 2 else ""
        return {
            "major":   "Ammo",
            "mfr":     mfr,
            "family":  f"{mfr} {wtype} {ammo}".strip(),
            "weight":  "",
            "part":    "Magazine",
            "variant": parts[3] if len(parts) > 3 else "01",
            "tint":    "",
            "is_base": True,
            "is_mag":  True,
        }

    else:
        # Weapon
        mfr   = parts[0].upper() if parts else "UNK"
        wtype = parts[1].title() if len(parts) > 1 else ""
        ammo  = parts[2].title() if len(parts) > 2 else ""
        variant_parts = parts[3:]
        num_parts = [p for p in variant_parts if re.match(r"^\d+$", p)]
        tint_parts = [p for p in variant_parts if p in TINT_WORDS or (p and not re.match(r"^\d+$", p))]
        variant = num_parts[0] if num_parts else "01"
        tint    = " ".join(tint_parts).title() if tint_parts else ""
        family  = f"{mfr} {wtype} {ammo}".strip()
        return {
            "major":   "Weapons",
            "mfr":     mfr,
            "family":  family,
            "weight":  "",
            "part":    f"{wtype} {ammo}".strip(),
            "variant": variant,
            "tint":    tint,
            "is_base": not bool(tint),
            "is_mag":  False,
        }

# ---------------------------------------------------------------------------
# Parse blueprint XML — slots with quantities + stat modifiers
# ---------------------------------------------------------------------------
def craft_time_str(costs_el):
    ct = costs_el.find(".//craftTime") if costs_el is not None else None
    if ct is None: return "—"
    d, h, m = int(ct.get("days",0)), int(ct.get("hours",0)), int(ct.get("minutes",0))
    s = float(ct.get("seconds", 0))
    p = []
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    if s: p.append(f"{int(s)}s")
    return " ".join(p) or "—"

def parse_slots(mandatory):
    """Return list of {name, qty_scu, stats[]}"""
    slots = []
    seen_names = set()
    if mandatory is None:
        return slots
    for sel in mandatory.findall(".//CraftingCost_Select"):
        name_el = sel.find("nameInfo")
        if name_el is None: continue
        debug   = name_el.get("debugName", "").strip().rstrip(":")
        display = name_el.get("displayName", "")
        sname   = loc(display) if display.startswith("@") else debug.title()
        if not sname or sname.upper() in ("ASPECTS",) or sname in seen_names:
            continue
        seen_names.add(sname)

        # Resource quantity + mineral name
        qty = 0.0
        mineral = ""
        res_el = sel.find(".//CraftingCost_Resource")
        if res_el is not None:
            res_uuid = res_el.get("resource", "")
            mineral  = RESOURCE_NAMES.get(res_uuid, "")
            qty_el   = res_el.find(".//quantity")
            if qty_el is not None:
                qty = float(qty_el.get("standardCargoUnits", 0))

        # Stats this slot can modify
        stats = []
        seen_stats = set()
        for mod in sel.iter("CraftingGameplayPropertyModifierCommon"):
            uid = mod.get("gameplayPropertyRecord", "")
            sname_stat = STAT_PROPS.get(uid)
            if sname_stat and sname_stat not in seen_stats:
                # Get modifier range
                vr = mod.find(".//CraftingGameplayPropertyModifierValueRange_Linear")
                if vr is not None:
                    lo = round(float(vr.get("modifierAtStart", 1)) * 100 - 100, 1)
                    hi = round(float(vr.get("modifierAtEnd",   1)) * 100 - 100, 1)
                    stats.append({"name": sname_stat, "lo": lo, "hi": hi})
                else:
                    stats.append({"name": sname_stat, "lo": None, "hi": None})
                seen_stats.add(sname_stat)

        slots.append({"name": sname, "qty": round(qty, 4), "mineral": mineral, "stats": stats})
    return slots

# ---------------------------------------------------------------------------
# Gather all blueprints
# ---------------------------------------------------------------------------
# Folder -> major category override (path takes priority over filename parsing)
def major_from_path(xml_file, bp_root):
    parts = xml_file.relative_to(bp_root).parts
    if parts and parts[0] in ("armour", "armor"):
        return "Armour"
    if parts and parts[0] == "weapons":
        return "Weapons"
    if parts and parts[0] == "ammo":
        return "Ammo"
    return None  # fall back to filename parsing

blueprints = []
bp_root = BASE / "blueprints/crafting/fpsgear"

for xml_file in sorted(bp_root.rglob("*.xml")):
    if "template" in xml_file.stem.lower() or xml_file.stem.lower().startswith("test"):
        continue
    meta = parse_bp_name(xml_file.stem)
    # Override major category from folder path
    folder_major = major_from_path(xml_file, bp_root)
    if folder_major:
        meta["major"] = folder_major

    # Fixup: armour-folder blueprints without "armor"/"armour" in filename
    # (e.g. bp_craft_qrt_combat_medium_arms_01_01_01 — set name replaces the word "armor")
    stem_lower = xml_file.stem.lower()
    if (folder_major == "Armour"
            and "armor" not in stem_lower and "armour" not in stem_lower
            and not meta.get("is_mag")):
        s      = re.sub(r"^bp_craft_", "", xml_file.stem, flags=re.I).lower()
        toks   = s.split("_")
        mfr_t  = toks[0].upper() if toks else "UNK"
        # Weight from folder (rel path: armour/combat/heavy/...) or filename
        rel    = xml_file.relative_to(bp_root).parts
        wt     = rel[2].title() if len(rel) > 2 and rel[2] in WEIGHT_CLASS else \
                 next((t.title() for t in toks if t in WEIGHT_CLASS), "")
        # Part from ARMOR_PARTS tokens in filename
        part_t = next((t.title() for t in toks if t in ARMOR_PARTS), "Unknown")
        # Set extras: tokens between mfr and first weight/part/digit
        stop   = next((i for i, t in enumerate(toks) if t in WEIGHT_CLASS or t in ARMOR_PARTS or re.match(r"^\d", t)), len(toks))
        extras = [t.title() for t in toks[1:stop] if t != mfr_t.lower() and t not in WEIGHT_CLASS and t not in ARMOR_PARTS]
        # Tint: TINT_WORDS found after weight/part
        tint_t = " ".join(t.title() for t in toks if t in TINT_WORDS)
        family_t = re.sub(r"\s+", " ", f"{mfr_t} {' '.join(extras)} {wt} Armor").strip()
        meta.update({
            "mfr":     mfr_t,
            "family":  family_t,
            "weight":  wt,
            "part":    part_t,
            "tint":    tint_t,
            "is_base": not bool(tint_t),
            "is_mag":  False,
        })
    try:
        root = ET.parse(xml_file).getroot()
    except ET.ParseError:
        continue
    bp_el = root.find("blueprint")
    if bp_el is None: continue
    tier = bp_el.find(".//CraftingBlueprintTier")
    recipe = tier.find("recipe") if tier is not None else None
    costs_el = recipe.find("costs") if recipe is not None else None
    craft_time = craft_time_str(costs_el)
    mandatory = costs_el.find("mandatoryCost") if costs_el is not None else None
    slots = parse_slots(mandatory)
    meta.update({"stem": xml_file.stem, "craft_time": craft_time, "slots": slots})
    blueprints.append(meta)

# ---------------------------------------------------------------------------
# Group: major -> mfr -> family -> [blueprints]
# ---------------------------------------------------------------------------
tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for bp in sorted(blueprints, key=lambda x: (x["major"], x["mfr"], x["family"], x["tint"], x["part"])):
    tree[bp["major"]][bp["mfr"]][bp["family"]].append(bp)

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def stat_pill(stat):
    lo, hi = stat["lo"], stat["hi"]
    if lo is None:
        txt = stat["name"]
        return f'<span style="background:#2A2F42;color:#CCCCCC;padding:2px 6px;border-radius:6px;font-size:10px">{txt}</span>'
    # lo is negative (penalty at low quality), hi is positive (bonus at high quality) — or vice versa
    lo_str = (f'+{lo}%' if lo > 0 else f'{lo}%') if lo != 0 else '0%'
    hi_str = (f'+{hi}%' if hi > 0 else f'{hi}%') if hi != 0 else '0%'
    txt = f'{stat["name"]}: {lo_str}→{hi_str}'
    return f'<span style="background:#252D3E;color:#888888;padding:2px 6px;border-radius:6px;font-size:10px;border:1px solid #3A3F56">{txt}</span>'

def slots_html(slots):
    if not slots:
        return '<span style="color:#4A4A5A">—</span>'
    rows = ""
    for sl in slots:
        qty_str = f'<span style="color:#8B6FE8;font-size:11px;min-width:44px;display:inline-block">{sl["qty"]:.4f} SCU</span>' if sl["qty"] else ""
        mineral = sl.get("mineral", "")
        if mineral:
            mineral_span = f'<span style="color:#4ade9a;font-size:11px;font-weight:500;min-width:110px;display:inline-block">{mineral}</span>'
        elif sl["qty"]:
            mineral_span = f'<span style="color:#4A4A5A;font-size:11px;min-width:110px;display:inline-block" title="Mineral not yet identified">?</span>'
        else:
            mineral_span = ""
        stat_pills = " ".join(stat_pill(s) for s in sl["stats"])
        rows += (
            f'<div style="margin:3px 0;display:flex;align-items:flex-start;gap:8px">'
            f'<span style="color:#FFFFFF;min-width:160px;font-size:12px">{sl["name"]}</span>'
            f'{qty_str}'
            f'{mineral_span}'
            f'<div style="display:flex;flex-wrap:wrap;gap:3px">{stat_pills}</div>'
            f'</div>'
        )
    return rows

WEIGHT_COLORS = {"Heavy": "#e85454", "Medium": "#e8a838", "Light": "#54c87a",
                 "": "#7A7A8A"}
PART_ORDER    = ["Helmet", "Core", "Arms", "Legs", "Undersuit"]
MAJOR_COLORS  = {"Armour": "#54a8e8", "Weapons": "#e85454", "Ammo": "#e8a838"}

# ---------------------------------------------------------------------------
# Build HTML panels per major category
# ---------------------------------------------------------------------------
tab_buttons = ""
tab_panels  = ""
total = len(blueprints)

for i, (major, mfr_map) in enumerate(sorted(tree.items())):
    mcolor = MAJOR_COLORS.get(major, "#7A7A8A")
    active = "active" if i == 0 else ""
    gid    = major.replace(" ", "_")
    count  = sum(len(bps) for fams in mfr_map.values() for bps in fams.values())
    tab_buttons += (
        f'<div class="tab {active}" onclick="showTab(\'{gid}\',this)" '
        f'style="{"border-bottom-color:"+mcolor+";color:"+mcolor if active else ""}">'
        f'{major} ({count})</div>'
    )

    panel_html = ""
    for mfr in sorted(mfr_map.keys()):
        fam_map = mfr_map[mfr]
        panel_html += f'<div class="mfr-header" style="color:{mcolor}">{mfr}</div>'

        for family in sorted(fam_map.keys()):
            bps_in_fam = fam_map[family]
            base_bps   = [b for b in bps_in_fam if b["is_base"]]
            tint_bps   = [b for b in bps_in_fam if not b["is_base"]]

            # Family header — wrapped in card
            weight = bps_in_fam[0].get("weight", "")
            wc     = WEIGHT_COLORS.get(weight, "#7A7A8A")
            wbadge = f'<span style="background:{wc}22;color:{wc};padding:1px 7px;border-radius:8px;font-size:11px;margin-left:8px">{weight}</span>' if weight else ""
            panel_html += f'<div class="family-card"><div class="family-header">{family}{wbadge}</div>'

            # Base blueprints - group by part for armor, flat list for weapons
            if major == "Armour" and base_bps:
                # Sort parts in logical order
                by_part = defaultdict(list)
                for bp in base_bps:
                    by_part[bp["part"]].append(bp)

                parts_html = ""
                for part in PART_ORDER + sorted(set(by_part.keys()) - set(PART_ORDER)):
                    if part not in by_part: continue
                    for bp in by_part[part]:
                        parts_html += (
                            f'<tr class="bp-row">'
                            f'<td style="color:#888888;width:90px;font-size:12px">{bp["part"]}</td>'
                            f'<td style="color:#8B6FE8;width:70px;font-size:12px">{bp["craft_time"]}</td>'
                            f'<td><div style="display:flex;flex-direction:column;gap:2px">{slots_html(bp["slots"])}</div></td>'
                            f'</tr>'
                        )
                if parts_html:
                    panel_html += (
                        f'<table class="bp-table"><thead><tr style="color:#4A4A5A;font-size:11px">'
                        f'<th>Part</th><th>Time</th><th>Material Slots → Stat Modifiers (low quality → high quality)</th>'
                        f'</tr></thead><tbody>{parts_html}</tbody></table>'
                    )

            elif base_bps:
                # Weapons/Ammo flat list
                rows = ""
                for bp in sorted(base_bps, key=lambda x: x["part"]):
                    rows += (
                        f'<tr class="bp-row">'
                        f'<td style="color:#888888;width:70px;font-size:12px">{bp["craft_time"]}</td>'
                        f'<td><div style="display:flex;flex-direction:column;gap:2px">{slots_html(bp["slots"])}</div></td>'
                        f'</tr>'
                    )
                panel_html += (
                    f'<table class="bp-table"><thead><tr style="color:#4A4A5A;font-size:11px">'
                    f'<th>Time</th><th>Material Slots → Stat Modifiers</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table>'
                )

            # Tint/variant blueprints — collapsible summary
            if tint_bps:
                tint_names = ", ".join(sorted(set(b["tint"] or b["stem"] for b in tint_bps)))
                fid = re.sub(r"[^a-z0-9]", "_", family.lower())
                panel_html += (
                    f'<div class="tint-row" onclick="toggleTints(\'{fid}\')" style="cursor:pointer">'
                    f'<span style="color:#4A4A5A;font-size:11px">▶ {len(tint_bps)} variant/tint blueprints: '
                    f'<span style="color:#5A5A6A">{tint_names[:120]}{"..." if len(tint_names)>120 else ""}</span></span>'
                    f'</div>'
                    f'<div id="tints_{fid}" style="display:none;padding:4px 0 8px 16px">'
                )
                for bp in sorted(tint_bps, key=lambda x: x["tint"]):
                    panel_html += (
                        f'<div style="padding:4px 0;border-bottom:1px solid #2A2F42;font-size:12px">'
                        f'<span style="color:#888888;min-width:160px;display:inline-block">{bp["tint"] or bp["stem"]}</span>'
                        f'<span style="color:#8B6FE8;margin:0 12px">{bp["craft_time"]}</span>'
                        f'<span style="color:#4A4A5A">{", ".join(s["name"] for s in bp["slots"])}</span>'
                        f'</div>'
                    )
                panel_html += f'</div>'

            panel_html += f'</div>'  # close family-card

    tab_panels += f'<div id="tab_{gid}" class="panel {active}">{panel_html}</div>'

# Summary pills
summary_pills = ""
for major, mfr_map in sorted(tree.items()):
    mcolor = MAJOR_COLORS.get(major, "#7A7A8A")
    cnt = sum(len(bps) for fams in mfr_map.values() for bps in fams.values())
    base_cnt = sum(1 for fams in mfr_map.values() for bps in fams.values() for b in bps if b["is_base"])
    tint_cnt = cnt - base_cnt
    summary_pills += (
        f'<div style="background:#1C1F2E;border:1px solid #3A3F56;border-radius:8px;padding:12px 18px;min-width:130px">'
        f'<div style="font-size:22px;font-weight:700;color:{mcolor}">{cnt}</div>'
        f'<div style="font-size:11px;color:#7A7A8A;text-transform:uppercase;letter-spacing:.5px;margin-top:2px">{major}</div>'
        f'<div style="font-size:11px;color:#4A4A5A;margin-top:3px">{base_cnt} base &bull; {tint_cnt} variants</div>'
        f'</div>'
    )

# Stat legend
stat_legend = "".join(
    f'<span style="background:#252D3E;border:1px solid #3A3F56;color:#888888;padding:2px 7px;border-radius:6px;font-size:11px;margin:2px">{v}</span>'
    for v in sorted(STAT_PROPS.values())
)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SC Crafting Report</title>
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
.summary-bar{{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}}
.stat-legend{{margin-top:12px;padding:10px 14px;background:rgba(35,38,52,.7);border:1px solid #3A3F56;border-radius:8px}}
.stat-legend .label{{color:#7A7A8A;font-size:11px;margin-bottom:6px}}
.explainer{{margin-top:12px;background:rgba(35,38,52,.7);border:1px solid #2d2050;border-left:3px solid #f5a742;border-radius:8px;padding:12px 16px}}
.explainer-title{{color:#f5a742;font-size:12px;font-weight:600;margin-bottom:8px;letter-spacing:.3px}}
.explainer-body p{{color:#888888;font-size:12px;line-height:1.65;margin-bottom:6px}}
.explainer-body p:last-child{{margin-bottom:0}}
.explainer-body strong{{color:#CCCCCC}}
.tabs{{display:flex;border-bottom:1px solid #3A3F56;background:#15171D;padding:0 40px;overflow-x:auto;flex-shrink:0}}
.tab{{padding:11px 18px;cursor:pointer;color:#7A7A8A;font-size:13px;font-weight:500;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s;user-select:none}}
.tab:hover{{color:#FFFFFF}}
.tab.active{{color:#FFFFFF;border-bottom-color:#532CD8}}
.container{{max-width:1300px;margin:0 auto;padding:24px 40px;flex:1}}
.panel{{display:none}}.panel.active{{display:block}}
.search-wrap{{margin-bottom:16px;display:flex;gap:10px;align-items:center}}
.search-wrap input{{background:rgba(35,38,52,.8);border:1px solid #3A3F56;color:#FFFFFF;padding:7px 13px;border-radius:6px;width:280px;font-size:13px;outline:none;transition:border-color .15s;font-family:'Outfit',sans-serif}}
.search-wrap input:focus{{border-color:#532CD8}}
.search-wrap input::placeholder{{color:#4A4A5A}}
.show-tints{{display:flex;align-items:center;gap:6px;color:#7A7A8A;font-size:12px;cursor:pointer;user-select:none}}
.mfr-header{{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:18px 0 8px;border-bottom:1px solid #3A3F56;margin-bottom:8px}}
.family-header{{font-size:13px;font-weight:600;color:#FFFFFF;padding:12px 0 6px;margin-top:4px}}
.bp-table{{width:100%;border-collapse:collapse;margin-bottom:4px}}
.bp-table th{{background:rgba(21,23,29,.9);color:#7A7A8A;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:6px 10px;border-bottom:1px solid #3A3F56;text-align:left}}
.bp-row td{{padding:7px 10px;border-bottom:1px solid #252D3E;vertical-align:top}}
.bp-row:last-child td{{border-bottom:none}}
.bp-row:hover td{{background:rgba(35,38,52,.6)}}
.tint-row{{padding:4px 10px 6px;margin-top:2px}}
.family-card{{background:linear-gradient(168deg,#232634 0%,#191B25 77%);outline:0.5px solid #14141A;box-shadow:inset 0px 0.5px 0px #2B2E3B;border:1px solid #3A3F56;border-radius:10px;padding:0 14px 10px;margin-bottom:10px;overflow:hidden}}
</style>
</head>
<body>
<div class="site-bar">
  <div class="site-logo">Saladins Information</div>
  <nav class="site-nav">
    <a href="crafting_report.html" class="cur">Crafting</a>
    <a href="mining_report.html">Mining</a>
    <a href="loot_report.html">Loot Tables</a>
    <a href="crafting_calculator.html">Calculator</a>
  </nav>
  <div class="site-ver">SC {GAME_VERSION}</div>
</div>
<div class="page-header">
  <h1>Crafting Report</h1>
  <div class="sub">{total} blueprints &bull; {len(STAT_PROPS)} craftable stats &bull; Grouped by item family &bull; Shows slot materials + stat modifier ranges</div>
  <div class="summary-bar">{summary_pills}</div>
  <div class="stat-legend">
    <div class="label">Craftable stats (affected by material slot choice &amp; quality):</div>
    {stat_legend}
  </div>
  <div class="explainer">
    <div class="explainer-title">&#9432; How to read this report &amp; known limitations</div>
    <div class="explainer-body">
      <p><strong>How crafting works:</strong> Each blueprint has 2&ndash;3 <em>material slots</em> (e.g. Armored Carapace, Frame, Barrel).
      You fill each slot with a specific crafting material. The material you choose determines which stats get modified and by how much &mdash;
      quality of the material (0&ndash;1000) then sets where in the modifier range the final item lands.</p>
      <p><strong>Reading the modifier ranges:</strong> <span style="color:#888888">Damage Mitigation: -15%&rarr;+15%</span> means
      a low-quality material gives &minus;15% damage mitigation, a high-quality material gives +15%.
      Slot choice locks in <em>which</em> stats are affected; material quality locks in <em>how much</em>.</p>
      <p><strong>Materials (minerals):</strong> Each slot is filled with a specific mineable resource &mdash;
      shown in <span style="color:#4ade9a">green</span> next to the SCU quantity.
      Materials are standard Star Citizen mineables (Hephaestanite, Iron, Tungsten, Ouratite, Aslarite, Taranite, Gold, Corundum, etc.).
      The SCU amount is small (0.01&ndash;0.10 SCU) but must be the correct mineral type.
      Some slot types (Frame, Support Structure, Casing Weave) use different minerals depending on the armor/weapon set.</p>
      <p><strong>Variants/tints:</strong> Color and faction variants (9Tails, Xenothreat, Shrike, etc.) use the same slot structure as the base blueprint
      but produce a differently skinned item. Toggle <em>Show all variants/tints</em> to expand them.</p>
    </div>
  </div>
</div>
<div class="tabs">{tab_buttons}</div>
<div class="container">
  <div class="search-wrap">
    <input type="text" id="search" placeholder="Filter by name..." oninput="filterRows(this.value)">
    <label class="show-tints">
      <input type="checkbox" id="showTints" onchange="toggleAllTints(this.checked)">
      Show all variants/tints
    </label>
  </div>
  {tab_panels}
</div>
<script>
function showTab(id,btn){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>{{t.classList.remove('active');t.style.borderBottomColor='';t.style.color='';}});
  document.getElementById('tab_'+id).classList.add('active');
  btn.classList.add('active');
}}
function filterRows(q){{
  q=q.toLowerCase();
  document.querySelectorAll('.family-header').forEach(fh=>{{
    const container=fh.parentElement;
    const match=fh.textContent.toLowerCase().includes(q)||
      Array.from(container.querySelectorAll('.bp-row td')).some(td=>td.textContent.toLowerCase().includes(q));
    fh.style.display=q&&!match?'none':'';
    container.querySelectorAll('.bp-table,.tint-row,[id^="tints_"]').forEach(el=>{{
      el.style.display=q&&!match?'none':'';
    }});
  }});
  document.querySelectorAll('.mfr-header').forEach(mh=>{{
    const allHidden=Array.from(mh.parentElement.querySelectorAll('.family-header'))
      .every(fh=>fh.style.display==='none');
    mh.style.display=q&&allHidden?'none':'';
  }});
}}
function toggleTints(id){{
  const el=document.getElementById('tints_'+id);
  const row=el.previousElementSibling;
  if(el.style.display==='none'){{el.style.display='block';row.querySelector('span').textContent=row.querySelector('span').textContent.replace('▶','▼');}}
  else{{el.style.display='none';row.querySelector('span').textContent=row.querySelector('span').textContent.replace('▼','▶');}}
}}
function toggleAllTints(show){{
  document.querySelectorAll('[id^="tints_"]').forEach(el=>el.style.display=show?'block':'none');
}}
</script>
</body>
</html>"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as fh:
    fh.write(HTML)
print(f"Written: {OUTPUT}")
print(f"Total blueprints: {total}")
for major, mfr_map in sorted(tree.items()):
    cnt = sum(len(bps) for fams in mfr_map.values() for bps in fams.values())
    base = sum(1 for fams in mfr_map.values() for bps in fams.values() for b in bps if b["is_base"])
    print(f"  {major}: {cnt} total ({base} base, {cnt-base} variants) — {len(mfr_map)} manufacturers")
    for mfr in sorted(mfr_map.keys())[:8]:
        fcount = len(mfr_map[mfr])
        print(f"    {mfr}: {fcount} families")

# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------
from pipeline.export_json import write_json

json_records = []
for bp in blueprints:
    json_records.append({
        "category":    bp["major"],
        "manufacturer":bp["mfr"],
        "family":      bp["family"],
        "part":        bp["part"],
        "weight":      bp.get("weight", ""),
        "tint":        bp.get("tint", ""),
        "is_base":     bp["is_base"],
        "craft_time":  bp["craft_time"],
        "file":        bp["stem"],
        "materials": [
            {
                "slot":        s["name"],
                "mineral":     s["mineral"],
                "quantity_scu":s["qty"],
                "stat_modifiers": s["stats"],
            }
            for s in bp["slots"]
        ],
    })

json_out = write_json(json_records, "crafting.json")
print(f"JSON   -> {json_out}  ({json_out.stat().st_size:,} bytes)")
