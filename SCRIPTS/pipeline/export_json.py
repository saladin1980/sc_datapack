"""
export_json.py -- Shared JSON export utility for the SC DataPack pipeline.
========================================================================
Each report script calls write_json() after building its data list.

Output directory: HTML/JSON/
  ships.json           -- 276 ships with loadout and insurance
  components.json      -- 1,791 equippable ship components
  armor.json           -- 2,208 player armor pieces
  weapons.json         -- ship + FPS weapons + attachments
  ground_vehicles.json -- 27 ground vehicles
  items.json           -- 501 consumables, food, melee, tools, etc.

Schema envelope (all files):
  {
    "meta": {
      "game_version": "4.6.0-live.11319298",
      "generated_at": "2026-03-01T12:00:00Z",
      "count": <int>,
      ... (type-specific extras)
    },
    "data": [ { ... record ... }, ... ]
  }
"""
import json
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import GAME_VERSION, REPORTS_DIR

JSON_DIR = REPORTS_DIR / "JSON"


# ── Core writer ───────────────────────────────────────────────────────────────

def write_json(records, filename, extra_meta=None):
    """
    Serialize records list to JSON_DIR/filename.
    Returns the output Path.

    records     : list of dicts (already cleaned for JSON — no HTML markup)
    filename    : e.g. "ships.json"
    extra_meta  : optional dict merged into meta block (e.g. {"ship_count": 276})
    """
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "game_version": GAME_VERSION,
            "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(records),
            **(extra_meta or {}),
        },
        "data": records,
    }
    out = JSON_DIR / filename
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ── Per-type record transformers ──────────────────────────────────────────────

def _safe_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _rnd(v, d=2):
    """Round a float to d decimal places; return 0 if falsy/None."""
    return round(v, d) if v else 0


def _safe_int(v, default=None):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


_CAREER_COMPOUND_FIXES = {
    # Joined words from DataCore that need a space inserted
    "Capitalship":         "Capital Ship",
    "Heavygunship":        "Heavy Gunship",
    "Luxurytouring":       "Luxury Touring",
    "Heavyfighter":        "Heavy Fighter",
    "Lightfighter":        "Light Fighter",
    "Mediumfighter":       "Medium Fighter",
    "Lightfreight":        "Light Freight",
    "Mediumfreight":       "Medium Freight",
    "Heavyfreight":        "Heavy Freight",
    "Starterlightfreight": "Starter Light Freight",
    "Heavyrefuelling":     "Heavy Refuelling",
    "Lightsalvage":        "Light Salvage",
    "Heavysalvage":        "Heavy Salvage",
    "Mediumsalvage":       "Medium Salvage",
    "Startersalvage":      "Starter Salvage",
    "Mediummining":        "Medium Mining",
    "Lightmining":         "Light Mining",
    "Startermining":       "Starter Mining",
    "Stealthfighter":      "Stealth Fighter",
    "Stealthbomber":       "Stealth Bomber",
    "Heavybomber":         "Heavy Bomber",
    "Heavyfighterbomber":  "Heavy Fighter Bomber",
    "Snubfighter":         "Snub Fighter",
    "Starterpathfinder":   "Starter Pathfinder",
    "Mediumdata":          "Medium Data",
    "Lightscience":        "Light Science",
    # Dual-role compound values
    "Lightfreight Mediumfighter": "Light Freight / Medium Fighter",
    # Game data typo (RSI Constellation Andromeda)
    "Mediumfreightgunshio": "Medium Freight Gunship",
}


def _clean_career(v):
    """Strip raw loc key prefixes, clean joined words, and title-case the result."""
    if not v:
        return ""
    # Unresolved procedural placeholder — not a real career value
    if v == "Procedural Text Null":
        return ""
    # Strip @vehicle_* and @item_ShipFocus_* loc key prefixes
    for pfx in ("@vehicle_focus_", "@vehicle_career_", "@vehicle_class_",
                 "@vehicle_role_", "@vehicle_", "@item_ShipFocus_", "@item_shipfocus_"):
        if v.startswith(pfx):
            v = v[len(pfx):].replace("_", " ").strip().title()
            return _CAREER_COMPOUND_FIXES.get(v, v)
    # Strip "Item Shipfocus " prefix (pre-resolved fallback)
    if v.startswith("Item Shipfocus "):
        v = v[len("Item Shipfocus "):].strip().title()
        return _CAREER_COMPOUND_FIXES.get(v, v)
    # Plain-text resolved string (groundvehicles style) — still may have compound words
    v = v.lstrip("@").replace("_", " ").strip().title()
    return _CAREER_COMPOUND_FIXES.get(v, v)


# Canonical manufacturer codes derived from class_name prefix.
# DataCore Code field is truncated (AEGS->AEG, MISC->MIS, KRIG->KRI) and
# Mirai (MRAI) collides with MISC (both Code='MIS'). Class prefix is authoritative.
_CLASS_TO_MFR_CODE = {
    "AEGS": "AEGS", "ANVL": "ANVL", "ARGO": "ARGO", "BANU": "BANU",
    "CNOU": "CNOU", "CRUS": "CRUS", "DRAK": "DRAK", "ESPR": "ESPR",
    "GRIN": "GRIN", "KRIG": "KRIG", "MISC": "MISC", "MRAI": "MRAI",
    "ORIG": "ORIG", "RSI":  "RSI",  "TMBL": "TMBL", "XIAN": "XIAN",
    "XNAA": "XNAA",
}

# Normalize truncated DataCore component manufacturer codes → canonical 4-letter codes.
# DataCore Code field is truncated for many manufacturers (AEGS→AEG, BEHR→BEH, etc.).
# This ensures components.manufacturer_code aligns with ships.manufacturer_code for Postgres joins.
_COMP_MFR_CODE_NORM = {
    "AEG": "AEGS", "ANV": "ANVL", "BEH": "BEHR",
    "MIS": "MISC", "KRI": "KRIG", "CRU": "CRUS",
    "DRK": "DRAK", "KLW": "KLWE", "MNV": "MNVR",
    "VOL": "VOLT", "GRY": "GRYO", "ORI": "ORIG",
    "ARG": "ARGO", "TMB": "TMBL", "GAT": "GATS",
    "KLA": "KLWE",  # Klaus & Werner (DataCore uses KLA)
    # Pass-throughs (already canonical or unique to component data)
    "JOK": "JOK",  "VNC": "VNC",
}


def ships_to_records(ships):
    """
    Transform parse_ship() dicts into clean JSON records.

    ship fields used:
      class_name, display_name, mfr_name, mfr_code,
      career, role, crew (str), hull_hp (str), cargo_scu (float),
      ins_wait (float, minutes), ins_fee (int, aUEC),
      size_x/y/z (str, metres),
      hardpoints: [{port, category, class, weapon:{display_name,type,size,grade}}]
      systems:    [{port, category, class, display_name, type, size, grade}]
    """
    records = []
    for s in ships:
        if not s:
            continue

        cn   = s.get("class_name", "")
        name = s.get("display_name", "")

        # Derive canonical mfr_code from class_name prefix (DataCore Code field
        # is truncated and Mirai/MISC collide on 'MIS').
        prefix   = cn.split("_")[0]
        mfr_code = _CLASS_TO_MFR_CODE.get(prefix, s.get("mfr_code", ""))

        # canonical_name strips the manufacturer code prefix from the display name
        # (e.g. "AEGS Gladius" -> "Gladius") — used as UEX join key.
        parts          = name.split(" ", 1)
        canonical_name = parts[1] if len(parts) > 1 else name

        hardpoints = []
        for h in s.get("hardpoints", []):
            w = h.get("weapon", {})
            hardpoints.append({
                "port":         h.get("port", ""),
                "category":     h.get("category", ""),
                "class":        h.get("class", ""),
                "display_name": w.get("display_name", ""),
                "type":         w.get("type", ""),
                "size":         w.get("size", ""),
                "grade":        w.get("grade", ""),
            })

        systems = []
        for c in s.get("systems", []):
            systems.append({
                "port":         c.get("port", ""),
                "category":     c.get("category", ""),
                "class":        c.get("class", ""),
                "display_name": c.get("display_name", ""),
                "type":         c.get("type", ""),
                "size":         c.get("size", ""),
                "grade":        c.get("grade", ""),
            })

        records.append({
            "class_name":        cn,
            "name":              name,
            "canonical_name":    canonical_name,  # ship name without mfr prefix — UEX join key
            "uex_id":            None,             # populated later via UEX API match
            "manufacturer":      s.get("mfr_name", ""),
            "manufacturer_code": mfr_code,
            "career":            _clean_career(s.get("career", "")),
            "role":              _clean_career(s.get("role", "")),
            "crew":              _safe_int(s.get("crew")),
            "hull_hp":           _safe_float(s.get("hull_hp")),
            "cargo_scu":         s.get("cargo_scu") or 0,
            "ins_wait_min":      round(s.get("ins_wait") or 0, 2),
            "ins_fee_auec":      s.get("ins_fee") or 0,
            # maxBoundingBoxSize: x=width, y=length, z=height (same as groundvehicles)
            "width_m":           _safe_float(s.get("size_x")),
            "length_m":          _safe_float(s.get("size_y")),
            "height_m":          _safe_float(s.get("size_z")),
            "hardpoints":        hardpoints,
            "systems":           systems,
        })
    return records


def components_to_records(components):
    """
    Transform scan_all_components() dicts into clean JSON records.

    component fields used:
      class, display_name, type, sub_type, size, grade, mfr,
      stats: list of (label, value) tuples
    """
    records = []
    for c in components:
        # stats: list of (label, value) 2-tuples -> [{label, value}]
        stats = []
        for item in c.get("stats", []):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                stats.append({"label": item[0], "value": item[1]})
        raw_code = c.get("mfr_code", "")
        records.append({
            "class":             c.get("class", ""),
            "name":              c.get("display_name", ""),
            "type":              c.get("type", ""),
            "sub_type":          c.get("sub_type", ""),
            "size":              c.get("size", ""),
            "grade":             c.get("grade", ""),
            "manufacturer":      c.get("mfr", ""),
            "manufacturer_code": _COMP_MFR_CODE_NORM.get(raw_code, raw_code),
            "stats":             stats,
        })
    return records


def armor_to_records(items):
    """
    Transform parse_armor_item() dicts into clean JSON records.

    armor fields used:
      name, file, slot, tier, mfr, micro_scu,
      dmg: {Physical, Energy, Distortion, Thermal, Biochemical, Stun, Force} (pct floats)
      temp_min, temp_max (float, Celsius or None)
      rad_cap, rad_rate (float or None)
      sigs: [{type, emission, reduc_w, reduc_a}]
      container_scu: int (microSCU * 1000 for backpacks)
    """
    records = []
    for item in items:
        if not item or item.get("slot") == "Other":
            continue
        sigs = []
        for s in item.get("sigs", []):
            sigs.append({
                "type":            s.get("type", ""),
                "emission":        s.get("emission", 0),
                "reduce_weighted": s.get("reduc_w", 0),
                "reduce_absolute": s.get("reduc_a", 0),
            })
        records.append({
            "name":              item.get("name", "") or item.get("file", ""),
            "file":              item.get("file", ""),
            "slot":              item.get("slot", ""),
            "tier":              item.get("tier", ""),
            "manufacturer":      item.get("mfr", ""),
            "micro_scu":         item.get("micro_scu", 0),
            "damage_resistance": item.get("dmg", {}),
            "temp_min_c":        item.get("temp_min"),
            "temp_max_c":        item.get("temp_max"),
            "rad_capacity":      item.get("rad_cap"),
            "rad_diss_rate":     item.get("rad_rate"),
            "signatures":        sigs,
            "container_scu":     item.get("container_scu", 0),
        })
    return records


def weapons_to_records(weapons):
    """
    Transform parse_ship_weapon / parse_fps_weapon / parse_attachment dicts
    into clean JSON records.

    Common fields: category, name, manufacturer, size, subtype, display_type, inventory_scu
    ship/fps adds:  fire_rate_rpm, ammo_speed_ms, dmg_*, total_damage,
                    ideal_range_m, max_range_m, mag_capacity, attachment_slots
    attachment adds: tags
    """
    records = []
    for w in weapons:
        cat = w["category"]
        rec = {
            "category":      cat,
            "name":          w.get("name", ""),
            "class_name":    w.get("class_name", ""),  # DataCore class — links to ship hardpoints
            "manufacturer":  w.get("manufacturer", ""),
            "size":          w.get("size", 0),
            "subtype":       w.get("subtype", ""),
            "display_type":  w.get("display_type", ""),
            "inventory_scu": w.get("inventory_scu", 0),
        }
        if cat in ("ship", "fps"):
            ammo = w.get("ammo", {})
            # Round floats from 32-bit game data to avoid noise (e.g. 97.19999694824219)
            rec.update({
                "fire_rate_rpm":   w.get("fire_rate", 0),
                "ammo_speed_ms":   _rnd(ammo.get("speed", 0), 1),
                "ammo_lifetime_s": _rnd(ammo.get("lifetime", 0), 3),
                "dmg_physical":    _rnd(ammo.get("dmg_physical", 0)),
                "dmg_energy":      _rnd(ammo.get("dmg_energy", 0)),
                "dmg_distortion":  _rnd(ammo.get("dmg_distortion", 0)),
                "dmg_thermal":     _rnd(ammo.get("dmg_thermal", 0)),
                "dmg_biochemical": _rnd(ammo.get("dmg_biochemical", 0)),
                "total_damage":    _rnd(w.get("total_damage", 0)),
                "ideal_range_m":   _rnd(w.get("ideal_range", 0), 1),
                "max_range_m":     _rnd(w.get("max_range", 0), 1),
                "mag_capacity":    w.get("mag_capacity", 0),
                "attachment_slots": w.get("attachment_slots", []),
            })
        elif cat == "attachment":
            rec["tags"] = w.get("tags", "")
        records.append(rec)
    return records


def vehicles_to_records(vehicles):
    """
    Transform parse_vehicle() dicts into clean JSON records.

    vehicle fields used:
      name, file, mfr, mfr_code, career, role,
      crew (int), hull_hp (int), movement (str), weapons (int),
      bbox_x/y/z (float, metres)
      ins_wait (float, minutes), ins_fee (int, aUEC)
    """
    records = []
    for v in vehicles:
        if not v:
            continue
        records.append({
            "name":              v.get("name", "") or v.get("file", ""),
            "file":              v.get("file", ""),
            "manufacturer":      v.get("mfr", ""),
            "manufacturer_code": v.get("mfr_code", ""),
            "career":            v.get("career", ""),
            "role":              v.get("role", ""),
            "crew":              v.get("crew", 0),
            "hull_hp":           v.get("hull_hp", 0),
            "drive":             v.get("movement", ""),
            "weapon_ports":      v.get("weapons", 0),
            # maxBoundingBoxSize: x=width, y=length, z=height
            "width_m":           v.get("bbox_x", 0) or None,
            "length_m":          v.get("bbox_y", 0) or None,
            "height_m":          v.get("bbox_z", 0) or None,
            "ins_wait_min":      round(v.get("ins_wait", 0) or 0, 2),
            "ins_fee_auec":      v.get("ins_fee", 0),
        })
    return records


def items_to_records(items):
    """
    Transform parse_item() dicts into clean JSON records.

    item fields used:
      name, file, display_cat, type, subtype,
      mfr, mfr_code, size, grade, micro_scu, tags
    """
    records = []
    for v in items:
        if not v or not v.get("name"):
            continue
        records.append({
            "name":              v.get("name", ""),
            "file":              v.get("file", ""),
            "category":          v.get("display_cat", ""),
            "type":              v.get("type", ""),
            "subtype":           v.get("subtype", ""),
            "manufacturer":      v.get("mfr", ""),
            "manufacturer_code": v.get("mfr_code", ""),
            "size":              v.get("size", ""),
            "grade":             v.get("grade", ""),
            "micro_scu":         v.get("micro_scu", 0),
            "tags":              v.get("tags", ""),
        })
    return records
