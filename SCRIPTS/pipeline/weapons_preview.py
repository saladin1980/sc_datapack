#!/usr/bin/env python3
"""
weapons_preview.py -- Builds weapons reference HTML page.

Covers:
  - Ship weapons   (WeaponGun)        from entities/scitem/ships/weapons/
  - FPS weapons    (WeaponPersonal)   from entities/scitem/weapons/fps_weapons/
  - Attachments    (WeaponAttachment) from entities/scitem/weapons/weapon_modifier/

Damage stats resolved via UUID chain:
  Ship: weapon -> ammoParamsRecord -> ammoparams/vehicle/
  FPS:  weapon -> ammoContainerRecord -> magazine -> ammoParamsRecord -> ammoparams/fps/

No AI, no external dependencies -- pure stdlib XML parsing.
"""

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR

RECORDS_DIR      = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
SHIP_WEAPONS_DIR = RECORDS_DIR / "entities" / "scitem" / "ships" / "weapons"
FPS_WEAPONS_DIR  = RECORDS_DIR / "entities" / "scitem" / "weapons" / "fps_weapons"
MODIFIERS_DIR    = RECORDS_DIR / "entities" / "scitem" / "weapons" / "weapon_modifier"
AMMO_DIR         = RECORDS_DIR / "ammoparams"

NULL_UUID = "00000000-0000-0000-0000-000000000000"

# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------

def build_loc_index():
    ini_path = OUTPUT_DIR / "Data" / "Localization" / "english" / "global.ini"
    idx = {}
    if not ini_path.exists():
        return idx
    with open(ini_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith(";"):
                k, _, v = line.partition("=")
                idx[k.strip().lower()] = v.strip()
    return idx


def build_uuid_index():
    """UUID (__ref) -> file path for all XMLs in records/. Used to resolve magazine UUIDs."""
    idx = {}
    for xml_file in RECORDS_DIR.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref = root.get("__ref", "")
            if ref and ref != NULL_UUID:
                idx[ref] = xml_file
        except Exception:
            pass
    return idx


def build_ammo_index():
    """UUID -> file path for all ammo params XMLs under records/ammoparams/."""
    idx = {}
    for xml_file in AMMO_DIR.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref = root.get("__ref", "")
            if ref and ref != NULL_UUID:
                idx[ref] = xml_file
        except Exception:
            pass
    return idx


def build_manufacturer_index(uuid_idx, loc_idx):
    idx = {}
    mfr_dir = RECORDS_DIR / "scitemmanufacturer"
    if not mfr_dir.exists():
        return idx
    for xml_file in mfr_dir.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref = root.get("__ref", "")
            if not ref:
                continue
            for el in root.iter():
                if "Localization" in el.tag:
                    k = el.get("Name", "") or el.get("name", "")
                    if k.startswith("@") and k not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                        v = loc_idx.get(k[1:].lower(), "")
                        if v and "PLACEHOLDER" not in v.upper():
                            idx[ref] = v
                            break
        except Exception:
            pass
    return idx


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

def _get_display_name(root, loc_idx):
    for el in root.iter():
        if "Localization" in el.tag:
            k = el.get("Name", "") or el.get("name", "")
            if k.startswith("@") and k not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                v = loc_idx.get(k[1:].lower(), "")
                if "PLACEHOLDER" in v.upper():
                    return ""
                return v
        if "SCItemPurchasableParams" in el.tag:
            k = el.get("displayName", "")
            if k.startswith("@") and k not in ("@LOC_UNINITIALIZED", "@LOC_EMPTY"):
                v = loc_idx.get(k[1:].lower(), "")
                if "PLACEHOLDER" in v.upper():
                    return ""
                return v
    return ""


def _get_display_type(root, loc_idx):
    """Weapon class label from SCItemPurchasableParams.displayType -> loc lookup."""
    for el in root.iter():
        if "SCItemPurchasableParams" in el.tag:
            k = el.get("displayType", "")
            if k.startswith("@"):
                return loc_idx.get(k[1:].lower(), "")
    return ""


def _parse_ammo(ammo_uuid, ammo_idx):
    """Read ammo params XML, return dict of speed + damage per type."""
    result = {
        "speed": 0.0, "lifetime": 0.0,
        "dmg_physical": 0.0, "dmg_energy": 0.0,
        "dmg_distortion": 0.0, "dmg_thermal": 0.0,
        "dmg_biochemical": 0.0, "dmg_stun": 0.0,
    }
    if not ammo_uuid or ammo_uuid == NULL_UUID:
        return result
    path = ammo_idx.get(ammo_uuid)
    if not path:
        return result
    try:
        root = ET.parse(path).getroot()
        result["speed"]    = float(root.get("speed", 0) or 0)
        result["lifetime"] = float(root.get("lifetime", 0) or 0)
        # First DamageInfo = primary impact damage
        for el in root.iter():
            if "DamageInfo" in el.tag:
                result["dmg_physical"]   = float(el.get("DamagePhysical", 0) or 0)
                result["dmg_energy"]     = float(el.get("DamageEnergy", 0) or 0)
                result["dmg_distortion"] = float(el.get("DamageDistortion", 0) or 0)
                result["dmg_thermal"]    = float(el.get("DamageThermal", 0) or 0)
                result["dmg_biochemical"]= float(el.get("DamageBiochemical", 0) or 0)
                result["dmg_stun"]       = float(el.get("DamageStun", 0) or 0)
                break
    except Exception:
        pass
    return result


def _get_fire_rate(root):
    """First non-zero fireRate (RPM) from any fireAction element."""
    for el in root.iter():
        if el.tag and "SWeaponActionFire" in el.tag:
            try:
                v = float(el.get("fireRate", 0) or 0)
                if v > 0:
                    return int(v)
            except ValueError:
                pass
    return 0


def _get_ammo_container(root):
    """(maxAmmoCount, ammoParamsRecord UUID) from SAmmoContainerComponentParams."""
    for el in root.iter():
        if "SAmmoContainerComponentParams" in el.tag:
            count = int(el.get("maxAmmoCount", 0) or 0)
            uuid  = el.get("ammoParamsRecord", NULL_UUID) or NULL_UUID
            return count, uuid
    return 0, NULL_UUID


def _get_attachment_slots(root):
    """List of WeaponAttachment subtypes accepted by this weapon's item ports."""
    slots = []
    for el in root.iter():
        if "SItemPortDef" in el.tag:
            for sub in el.iter():
                if "SItemPortDefTypes" in sub.tag and sub.get("Type") == "WeaponAttachment":
                    for enum_el in sub.iter():
                        if enum_el.tag == "Enum":
                            v = enum_el.get("value", "")
                            if v and v not in slots:
                                slots.append(v)
    return slots


def _get_weapon_ai_range(root):
    for el in root.iter():
        # Tag is "weaponAIData"; __type attr is "SWeaponAIDataParams"
        if el.tag == "weaponAIData" or el.get("__type") == "SWeaponAIDataParams":
            ideal = float(el.get("idealCombatRange", 0) or 0)
            max_r = float(el.get("maxFiringRange", 0) or 0)
            if ideal > 0 or max_r > 0:
                return ideal, max_r
    return 0.0, 0.0


def _infer_damage_type(ammo):
    p = ammo["dmg_physical"]
    e = ammo["dmg_energy"]
    d = ammo["dmg_distortion"]
    t = ammo["dmg_thermal"]
    b = ammo["dmg_biochemical"]
    if d > 0 and p == 0 and e == 0:
        return "Distortion"
    if b > 0 and p == 0:
        return "Biochemical"
    if t > 0 and p == 0 and e == 0:
        return "Thermal"
    if e > 0 and p == 0:
        return "Energy"
    if e > 0 and p > 0:
        return "Energy"   # plasma / mixed
    if p > 0:
        return "Ballistic"
    return ""


def _total_damage(ammo):
    return (ammo["dmg_physical"] + ammo["dmg_energy"] + ammo["dmg_distortion"]
            + ammo["dmg_thermal"] + ammo["dmg_biochemical"])


def _get_scu(root):
    for el in root.iter():
        if "SMicroCargoUnit" in el.tag:
            return float(el.get("microSCU", 0) or 0) / 1_000_000
    return 0.0


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_ship_weapon(path, loc_idx, mfr_idx, ammo_idx):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None

    name = _get_display_name(root, loc_idx)
    if not name:
        return None

    attach_def = next((el for el in root.iter() if el.tag == "AttachDef"), None)
    if attach_def is None or attach_def.get("Type") != "WeaponGun":
        return None

    size         = int(attach_def.get("Size", 0) or 0)
    mfr_uuid     = attach_def.get("Manufacturer", NULL_UUID)
    manufacturer = mfr_idx.get(mfr_uuid, "")
    tags         = attach_def.get("Tags", "")

    fire_rate          = _get_fire_rate(root)
    _, ammo_uuid       = _get_ammo_container(root)
    ammo               = _parse_ammo(ammo_uuid, ammo_idx)
    damage_type        = _infer_damage_type(ammo)
    ideal_r, max_r     = _get_weapon_ai_range(root)

    return {
        "category":     "ship",
        "name":         name,
        "manufacturer": manufacturer,
        "size":         size,
        "subtype":      "Gun",
        "display_type": damage_type or "Gun",
        "fire_rate":    fire_rate,
        "ammo":         ammo,
        "total_damage": _total_damage(ammo),
        "ideal_range":  ideal_r,
        "max_range":    max_r,
        "mag_capacity": 0,
        "attachment_slots": [],
        "inventory_scu":    _get_scu(root),
        "tags":         tags,
    }


def parse_fps_weapon(path, loc_idx, mfr_idx, ammo_idx, uuid_idx):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None

    name = _get_display_name(root, loc_idx)
    if not name:
        return None

    attach_def = next((el for el in root.iter() if el.tag == "AttachDef"), None)
    if attach_def is None or attach_def.get("Type") != "WeaponPersonal":
        return None

    subtype      = attach_def.get("SubType", "")
    size         = int(attach_def.get("Size", 0) or 0)
    mfr_uuid     = attach_def.get("Manufacturer", NULL_UUID)
    manufacturer = mfr_idx.get(mfr_uuid, "")

    # Weapon class label (Rifle, SMG, Pistol, etc.)
    display_type = _get_display_type(root, loc_idx) or subtype

    fire_rate = _get_fire_rate(root)

    # Ammo chain: weapon -> magazine -> ammo params
    # Check for direct ammo params first (energy FPS weapons may have this)
    direct_count, direct_ammo_uuid = _get_ammo_container(root)
    if direct_ammo_uuid != NULL_UUID:
        ammo_uuid    = direct_ammo_uuid
        mag_capacity = direct_count
    else:
        # Follow ammoContainerRecord -> magazine XML -> ammo params
        ammo_uuid    = NULL_UUID
        mag_capacity = 0
        for el in root.iter():
            if "SCItemWeaponComponentParams" in el.tag:
                mag_uuid = el.get("ammoContainerRecord", NULL_UUID) or NULL_UUID
                if mag_uuid != NULL_UUID:
                    mag_path = uuid_idx.get(mag_uuid)
                    if mag_path:
                        try:
                            mag_root     = ET.parse(mag_path).getroot()
                            mag_capacity, ammo_uuid = _get_ammo_container(mag_root)
                        except Exception:
                            pass
                break

    ammo        = _parse_ammo(ammo_uuid, ammo_idx)
    damage_type = _infer_damage_type(ammo)

    return {
        "category":         "fps",
        "name":             name,
        "manufacturer":     manufacturer,
        "size":             size,
        "subtype":          subtype,
        "display_type":     display_type,
        "fire_rate":        fire_rate,
        "ammo":             ammo,
        "total_damage":     _total_damage(ammo),
        "damage_type":      damage_type,
        "ideal_range":      0.0,
        "max_range":        0.0,
        "mag_capacity":     mag_capacity,
        "attachment_slots": _get_attachment_slots(root),
        "inventory_scu":    _get_scu(root),
    }


def parse_attachment(path, loc_idx, mfr_idx):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None

    name = _get_display_name(root, loc_idx)
    if not name:
        return None

    attach_def = next((el for el in root.iter() if el.tag == "AttachDef"), None)
    if attach_def is None or attach_def.get("Type") != "WeaponAttachment":
        return None

    subtype      = attach_def.get("SubType", "")
    size         = int(attach_def.get("Size", 0) or 0)
    mfr_uuid     = attach_def.get("Manufacturer", NULL_UUID)
    manufacturer = mfr_idx.get(mfr_uuid, "")
    tags         = attach_def.get("Tags", "")

    return {
        "category":     "attachment",
        "name":         name,
        "manufacturer": manufacturer,
        "size":         size,
        "subtype":      subtype,
        "display_type": subtype,
        "tags":         tags,
        "inventory_scu": _get_scu(root),
    }


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def scan_all_weapons(loc_idx, mfr_idx, ammo_idx, uuid_idx):
    weapons = []

    ship_files = sorted(SHIP_WEAPONS_DIR.glob("*.xml"))
    print(f"Ship weapons: {len(ship_files)} files...")
    sys.stdout.flush()
    for i, path in enumerate(ship_files, 1):
        item = parse_ship_weapon(path, loc_idx, mfr_idx, ammo_idx)
        if item:
            weapons.append(item)
        if i % 200 == 0:
            print(f"  ship {i}/{len(ship_files)}")
            sys.stdout.flush()

    fps_files = sorted(FPS_WEAPONS_DIR.glob("*.xml"))
    print(f"FPS weapons: {len(fps_files)} files...")
    sys.stdout.flush()
    for i, path in enumerate(fps_files, 1):
        item = parse_fps_weapon(path, loc_idx, mfr_idx, ammo_idx, uuid_idx)
        if item:
            weapons.append(item)
        if i % 100 == 0:
            print(f"  fps {i}/{len(fps_files)}")
            sys.stdout.flush()

    mod_files = sorted(MODIFIERS_DIR.glob("*.xml"))
    print(f"Attachments: {len(mod_files)} files...")
    sys.stdout.flush()
    for path in mod_files:
        item = parse_attachment(path, loc_idx, mfr_idx)
        if item:
            weapons.append(item)

    return weapons


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

SLOT_LABELS = {
    "Magazine":        "MAG",
    "IronSight":       "OPT",
    "Barrel":          "BRL",
    "Underbarrel":     "UB",
    "Flashlight":      "LITE",
    "BarrelAttachment":"BRL",
}

TYPE_COLORS = {
    "energy":      "#4fc3f7",
    "ballistic":   "#ef9a9a",
    "distortion":  "#ce93d8",
    "thermal":     "#ffcc02",
    "biochemical": "#a5d6a7",
    "rifle":       "#90caf9",
    "smg":         "#80cbc4",
    "pistol":      "#ffab91",
    "shotgun":     "#bcaaa4",
    "sniper":      "#b39ddb",
    "lmg":         "#ef9a9a",
    "grenade launcher": "#ffcc80",
    "knife":       "#cfd8dc",
    "barrel":      "#78909c",
    "ironsight":   "#4db6ac",
    "magazine":    "#f48fb1",
    "underbarrel": "#a1887f",
}


def _type_color(display_type):
    return TYPE_COLORS.get(display_type.lower(), "#607d8b")


def item_to_html(item):
    name         = item["name"]
    mfr          = item["manufacturer"]
    cat          = item["category"]
    size         = item["size"]
    display_type = item.get("display_type") or item.get("subtype") or ""
    inv          = item.get("inventory_scu", 0)
    color        = _type_color(display_type)

    mfr_badge  = f'<span class="badge mfr">{mfr}</span>' if mfr else ""
    size_badge = f'<span class="badge size">S{size}</span>' if size else ""
    type_badge = f'<span class="badge type" style="border-color:{color};color:{color}">{display_type}</span>' if display_type else ""

    stats = []

    if cat in ("ship", "fps"):
        ammo      = item.get("ammo", {})
        fire_rate = item.get("fire_rate", 0)
        speed     = ammo.get("speed", 0)
        mag       = item.get("mag_capacity", 0)
        ideal_r   = item.get("ideal_range", 0)
        max_r     = item.get("max_range", 0)

        dp = ammo.get("dmg_physical", 0)
        de = ammo.get("dmg_energy", 0)
        dd = ammo.get("dmg_distortion", 0)
        dt = ammo.get("dmg_thermal", 0)
        db = ammo.get("dmg_biochemical", 0)

        if dp > 0:
            stats.append(f'<div class="stat"><span class="sl">Phys</span><span class="sv">{dp:.1f}</span></div>')
        if de > 0:
            stats.append(f'<div class="stat"><span class="sl">Energy</span><span class="sv">{de:.1f}</span></div>')
        if dd > 0:
            stats.append(f'<div class="stat"><span class="sl">Dist</span><span class="sv">{dd:.1f}</span></div>')
        if dt > 0:
            stats.append(f'<div class="stat"><span class="sl">Therm</span><span class="sv">{dt:.1f}</span></div>')
        if db > 0:
            stats.append(f'<div class="stat"><span class="sl">Bio</span><span class="sv">{db:.1f}</span></div>')
        if fire_rate > 0:
            stats.append(f'<div class="stat"><span class="sl">RPM</span><span class="sv">{fire_rate}</span></div>')
        if speed > 0:
            stats.append(f'<div class="stat"><span class="sl">Speed</span><span class="sv">{speed:.0f} m/s</span></div>')
        if mag > 0:
            stats.append(f'<div class="stat"><span class="sl">Mag</span><span class="sv">{mag}</span></div>')
        if ideal_r > 0:
            stats.append(f'<div class="stat"><span class="sl">Range</span><span class="sv">{ideal_r:.0f} / {max_r:.0f} m</span></div>')

    if inv > 0:
        stats.append(f'<div class="stat"><span class="sl">Size</span><span class="sv">{inv:.3f} SCU</span></div>')

    stats_html = f'<div class="stats-grid">{"".join(stats)}</div>' if stats else ""

    # Attachment slots (FPS only)
    slots_html = ""
    if cat == "fps":
        slots = item.get("attachment_slots", [])
        if slots:
            badges = "".join(
                f'<span class="slot-badge">{SLOT_LABELS.get(s, s)}</span>'
                for s in slots
            )
            slots_html = f'<div class="slots-row">{badges}</div>'

    type_key   = display_type.lower().replace(" ", "-")
    data_attrs = (f'data-cat="{cat}" data-type="{type_key}" '
                  f'data-name="{name.lower()}" data-size="{size}"')

    return f'''<div class="item-card" {data_attrs}>
  <div class="card-header">
    <div class="card-name">{name}</div>
    <div class="card-badges">{mfr_badge}{size_badge}{type_badge}</div>
  </div>
  {stats_html}{slots_html}
</div>'''


def generate_html(weapons):
    ship_weapons = sorted([w for w in weapons if w["category"] == "ship"],
                          key=lambda x: (x["size"], x["name"]))
    fps_weapons  = sorted([w for w in weapons if w["category"] == "fps"],
                          key=lambda x: (x["display_type"], x["name"]))
    attachments  = sorted([w for w in weapons if w["category"] == "attachment"],
                          key=lambda x: (x["subtype"], x["name"]))

    ship_types = sorted(set(w["display_type"] for w in ship_weapons if w["display_type"]))
    fps_types  = sorted(set(w["display_type"] for w in fps_weapons  if w["display_type"]))
    att_types  = sorted(set(w["subtype"]      for w in attachments  if w["subtype"]))

    def tab_row(options, prefix, fn_name):
        btns = f'<button class="{prefix}-tab active" data-{prefix}="all" onclick="{fn_name}(this)">All</button>'
        for opt in options:
            key = opt.lower().replace(" ", "-")
            btns += f'<button class="{prefix}-tab" data-{prefix}="{key}" onclick="{fn_name}(this)">{opt}</button>'
        return btns

    ship_cards = "\n".join(item_to_html(w) for w in ship_weapons)
    fps_cards  = "\n".join(item_to_html(w) for w in fps_weapons)
    att_cards  = "\n".join(item_to_html(w) for w in attachments)

    ship_type_tabs = tab_row(ship_types, "stype", "setShipType")
    fps_type_tabs  = tab_row(fps_types,  "ftype", "setFpsType")
    att_type_tabs  = tab_row(att_types,  "atype", "setAttType")

    n_ship = len(ship_weapons)
    n_fps  = len(fps_weapons)
    n_att  = len(attachments)
    total  = len(weapons)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SC Weapons Reference</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:system-ui,sans-serif;font-size:13px}}
a{{color:#58a6ff;text-decoration:none}}
h1{{font-size:1.3rem;font-weight:600;color:#e6edf3}}

/* Layout */
.page-header{{background:#161b22;border-bottom:1px solid #30363d;padding:14px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.page-header h1{{flex:1}}
.count-badge{{background:#21262d;border:1px solid #30363d;border-radius:12px;padding:2px 10px;font-size:11px;color:#8b949e}}

.main-tabs{{display:flex;gap:6px;padding:14px 20px 0;border-bottom:1px solid #30363d;background:#161b22}}
.main-tab{{background:none;border:none;border-bottom:2px solid transparent;padding:8px 16px;color:#8b949e;cursor:pointer;font-size:13px;transition:color .15s,border-color .15s}}
.main-tab:hover{{color:#c9d1d9}}
.main-tab.active{{color:#58a6ff;border-bottom-color:#58a6ff}}

.section{{display:none;padding:16px 20px}}
.section.active{{display:block}}

.filter-bar{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}}
.filter-label{{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}}
.tab-row{{display:flex;flex-wrap:wrap;gap:4px;flex:1}}
.filter-tab{{background:#21262d;border:1px solid #30363d;border-radius:4px;padding:3px 10px;color:#8b949e;cursor:pointer;font-size:11px;transition:all .15s}}
.filter-tab:hover{{border-color:#58a6ff;color:#c9d1d9}}
.filter-tab.active{{background:#1f6feb;border-color:#388bfd;color:#fff}}

#search-ship,#search-fps,#search-att{{background:#21262d;border:1px solid #30363d;border-radius:4px;padding:4px 10px;color:#c9d1d9;font-size:12px;width:200px;outline:none}}
#search-ship:focus,#search-fps:focus,#search-att:focus{{border-color:#58a6ff}}

.vis-count{{color:#8b949e;font-size:11px;white-space:nowrap}}

/* Cards */
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}}
.item-card{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;transition:border-color .15s}}
.item-card:hover{{border-color:#58a6ff}}
.card-header{{margin-bottom:8px}}
.card-name{{font-weight:600;color:#e6edf3;font-size:13px;margin-bottom:5px;line-height:1.3}}
.card-badges{{display:flex;flex-wrap:wrap;gap:4px}}
.badge{{border-radius:3px;padding:1px 6px;font-size:10px;font-weight:500}}
.badge.mfr{{background:#21262d;color:#8b949e;border:1px solid #30363d}}
.badge.size{{background:#21262d;color:#79c0ff;border:1px solid #1f6feb}}
.badge.type{{background:transparent;border:1px solid;font-size:10px}}

/* Stats */
.stats-grid{{display:flex;flex-wrap:wrap;gap:4px 10px;margin-top:6px}}
.stat{{display:flex;flex-direction:column;min-width:60px}}
.sl{{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:.04em}}
.sv{{color:#e6edf3;font-size:12px;font-weight:500;margin-top:1px}}

/* Slot badges */
.slots-row{{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;padding-top:8px;border-top:1px solid #21262d}}
.slot-badge{{background:#21262d;border:1px solid #30363d;border-radius:3px;padding:1px 6px;font-size:10px;color:#8b949e}}
</style>
</head>
<body>

<div class="page-header">
  <h1>SC Weapons Reference</h1>
  <span class="count-badge">{n_ship} ship weapons</span>
  <span class="count-badge">{n_fps} FPS weapons</span>
  <span class="count-badge">{n_att} attachments</span>
</div>

<!-- Main category tabs -->
<div class="main-tabs">
  <button class="main-tab active" onclick="showSection('ship',this)">Ship Weapons <small>({n_ship})</small></button>
  <button class="main-tab" onclick="showSection('fps',this)">FPS Weapons <small>({n_fps})</small></button>
  <button class="main-tab" onclick="showSection('att',this)">Attachments <small>({n_att})</small></button>
</div>

<!-- Ship Weapons -->
<div id="sec-ship" class="section active">
  <div class="filter-bar">
    <span class="filter-label">Type</span>
    <div class="tab-row">{ship_type_tabs}</div>
    <input id="search-ship" type="search" placeholder="Search..." oninput="applyShip()">
    <span class="vis-count" id="vis-ship">{n_ship} shown</span>
  </div>
  <div class="card-grid" id="grid-ship">
{ship_cards}
  </div>
</div>

<!-- FPS Weapons -->
<div id="sec-fps" class="section">
  <div class="filter-bar">
    <span class="filter-label">Class</span>
    <div class="tab-row">{fps_type_tabs}</div>
    <input id="search-fps" type="search" placeholder="Search..." oninput="applyFps()">
    <span class="vis-count" id="vis-fps">{n_fps} shown</span>
  </div>
  <div class="card-grid" id="grid-fps">
{fps_cards}
  </div>
</div>

<!-- Attachments -->
<div id="sec-att" class="section">
  <div class="filter-bar">
    <span class="filter-label">Type</span>
    <div class="tab-row">{att_type_tabs}</div>
    <input id="search-att" type="search" placeholder="Search..." oninput="applyAtt()">
    <span class="vis-count" id="vis-att">{n_att} shown</span>
  </div>
  <div class="card-grid" id="grid-att">
{att_cards}
  </div>
</div>

<script>
function showSection(id, btn) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  btn.classList.add('active');
}}

function setShipType(btn) {{
  document.querySelectorAll('.stype-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active'); applyShip();
}}
function setFpsType(btn) {{
  document.querySelectorAll('.ftype-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active'); applyFps();
}}
function setAttType(btn) {{
  document.querySelectorAll('.atype-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active'); applyAtt();
}}

function applyFilter(gridId, visId, typeAttr, activeTabClass, searchId) {{
  const typeTab = document.querySelector('.' + activeTabClass + '.active');
  const typeVal = typeTab ? typeTab.dataset[typeAttr] : 'all';
  const q = document.getElementById(searchId).value.toLowerCase().trim();
  let vis = 0;
  document.querySelectorAll('#' + gridId + ' .item-card').forEach(c => {{
    const tok = typeVal === 'all' || c.dataset.type === typeVal;
    const nok = !q || c.dataset.name.includes(q);
    const show = tok && nok;
    c.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById(visId).textContent = vis + ' shown';
}}

function applyShip() {{ applyFilter('grid-ship', 'vis-ship', 'stype', 'stype-tab', 'search-ship'); }}
function applyFps()  {{ applyFilter('grid-fps',  'vis-fps',  'ftype', 'ftype-tab', 'search-fps'); }}
function applyAtt()  {{ applyFilter('grid-att',  'vis-att',  'atype', 'atype-tab', 'search-att'); }}
</script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run():
    t0 = time.time()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading localization...")
    sys.stdout.flush()
    loc_idx = build_loc_index()
    print(f"  {len(loc_idx):,} keys")

    print("Building UUID index (all records)...")
    sys.stdout.flush()
    uuid_idx = build_uuid_index()
    print(f"  {len(uuid_idx):,} UUIDs")

    print("Building ammo index...")
    sys.stdout.flush()
    ammo_idx = build_ammo_index()
    print(f"  {len(ammo_idx):,} ammo records")

    print("Building manufacturer index...")
    sys.stdout.flush()
    mfr_idx = build_manufacturer_index(uuid_idx, loc_idx)
    print(f"  {len(mfr_idx):,} manufacturers")

    print("Scanning weapons...")
    sys.stdout.flush()
    weapons = scan_all_weapons(loc_idx, mfr_idx, ammo_idx, uuid_idx)

    n_ship = sum(1 for w in weapons if w["category"] == "ship")
    n_fps  = sum(1 for w in weapons if w["category"] == "fps")
    n_att  = sum(1 for w in weapons if w["category"] == "attachment")
    print(f"  {n_ship} ship weapons, {n_fps} FPS weapons, {n_att} attachments")
    sys.stdout.flush()

    print("Generating HTML...")
    sys.stdout.flush()
    html = generate_html(weapons)

    out_path = REPORTS_DIR / "weapons_preview.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Written -> {out_path}  ({len(html):,} bytes)")

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
