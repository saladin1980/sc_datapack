"""
Comprehensive ship data extractor.
Parses ALL loadout entries per ship, resolves every linked entity,
outputs a self-contained HTML review file.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import OUTPUT_DIR, REPORTS_DIR

RECORDS_DIR = OUTPUT_DIR / "Data" / "Libs" / "foundry" / "records"
SHIPS_DIR   = RECORDS_DIR / "entities" / "spaceships"

MFR_NAMES = {
    "AEGS": "Aegis Dynamics",       "ANVL": "Anvil Aerospace",
    "BANU": "Banu",                 "CNOU": "Consolidated Outland",
    "CRUS": "Crusader Industries",  "DRAK": "Drake Interplanetary",
    "ESPR": "Esperia",              "ESPRIA": "Esperia",
    "GRIN": "Greycat Industrial",   "KRIG": "Kruger Intergalactic",
    "MISC": "MISC",                 "MRAI": "Mirai",
    "ORIG": "Origin Jumpworks",     "RSI": "Roberts Space Industries",
    "TMBL": "Tumbril",              "ARGO": "Argo Astronautics",
    "XIAN": "Aopoa",                "XNAA": "Xenotech",
}

# ── Ship discovery ─────────────────────────────────────────────────────────────

# Prefixes that are not player-manufacturer ships
_SKIP_PREFIXES = frozenset({
    "eaobjectivedestructable", "orbital", "probe", "glsn",
    "spaceship", "gama", "vncl",
})
# Stem substrings that indicate NPC/mission/test variants
_SKIP_PATTERNS = (
    "_pu_ai_", "_ai_", "_unmanned_", "_tutorial", "_teach",
    "_tier_1", "_tier_2", "_tier_3", "_pu_hijacked", "_pu_civilian",
    "_pu_npc", "_ea_",
)

def scan_all_ships():
    """Return sorted list of ship XML paths, filtered to player-relevant ships."""
    result = []
    for f in sorted(SHIPS_DIR.glob("*.xml")):
        s = f.stem.lower()
        if s.split("_")[0] in _SKIP_PREFIXES:
            continue
        if any(p in s for p in _SKIP_PATTERNS):
            continue
        result.append(f)
    return result

# ── Port categorisation ────────────────────────────────────────────────────────

SECTION_ORDER = [
    "weapon", "turret", "missile",
    "shield", "power", "cooler", "quantum",
    "fuel_h", "fuel_q",
    "lifesupport", "landing",
    "other",
]

SECTION_META = {          # (emoji, label, css-class)
    "weapon":      ("⚔",  "Weapons",        "sec-weapon"),
    "turret":      ("⚔",  "Turrets",         "sec-turret"),
    "missile":     ("🚀", "Missiles",        "sec-missile"),
    "shield":      ("🛡", "Shields",         "sec-shield"),
    "power":       ("⚡", "Power Plants",    "sec-power"),
    "cooler":      ("❄",  "Coolers",         "sec-cooler"),
    "quantum":     ("🌌", "Quantum Drive",   "sec-quantum"),
    "fuel_h":      ("⛽", "Hydrogen Fuel",   "sec-fuel"),
    "fuel_q":      ("⚗",  "Quantum Fuel",    "sec-fuel"),
    "thruster":    ("🔥", "Thrusters",       "sec-thruster"),
    "radar":       ("📡", "Radar / Sensors", "sec-radar"),
    "lifesupport": ("💨", "Life Support",    "sec-other"),
    "landing":     ("🦿", "Landing",         "sec-other"),
    "controller":  ("🎮", "Controllers",     "sec-ctrl"),
    "other":       ("⚙",  "Other",           "sec-other"),
}

def get_port_category(port_lc):
    if any(k in port_lc for k in ("weapon", "gun")) and "missile" not in port_lc:
        return "weapon"
    if "turret" in port_lc:
        return "turret"
    if "missile" in port_lc:
        return "missile"
    if any(k in port_lc for k in ("cargogrid", "cargo_bay", "cargo_grid")):
        return "cargo"
    if "shield" in port_lc:
        return "shield"
    if any(k in port_lc for k in ("powerplant", "power_plant")):
        return "power"
    if "cooler" in port_lc:
        return "cooler"
    if "quantum" in port_lc:
        return "quantum"
    if any(k in port_lc for k in ("fuel_tank", "fueltank", "htank", "htnk", "fuel_intake")):
        return "fuel_h"
    if any(k in port_lc for k in ("qtank", "qtnk")):
        return "fuel_q"
    if any(k in port_lc for k in ("thruster", "engine")):
        return "thruster"
    if any(k in port_lc for k in ("radar", "sensor", "avionics")):
        return "radar"
    if any(k in port_lc for k in ("lifesupport", "life_support")):
        return "lifesupport"
    if "landing" in port_lc:
        return "landing"
    if "relay" in port_lc:
        return "relay"
    if "controller" in port_lc:
        return "controller"
    return "other"

# ── Indexes ────────────────────────────────────────────────────────────────────

def build_uuid_index():
    print("Building UUID index (~30s)...")
    index = {}
    for xml_file in RECORDS_DIR.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            ref  = root.get("__ref")
            if ref:
                tag = root.tag
                cls = tag.split(".", 1)[1] if "." in tag else tag
                index[ref] = {"path": xml_file, "class": cls}
        except Exception:
            pass
    print(f"  {len(index):,} UUIDs indexed")
    return index


def build_classname_index():
    print("Building class name index...")
    index = {}
    for xml_file in RECORDS_DIR.rglob("*.xml"):
        try:
            root = ET.parse(xml_file).getroot()
            tag  = root.tag
            if "." in tag:
                cls = tag.split(".", 1)[1]
                index[cls.lower()] = xml_file
        except Exception:
            pass
    print(f"  {len(index):,} class names indexed")
    return index


def build_manufacturer_index(uuid_index):
    index = {}
    mfr_dir = RECORDS_DIR / "scitemmanufacturer"
    if mfr_dir.exists():
        for xml_file in mfr_dir.rglob("*.xml"):
            try:
                root = ET.parse(xml_file).getroot()
                ref  = root.get("__ref")
                code = root.get("Code") or root.get("code") or xml_file.stem.upper()
                if ref:
                    index[ref] = code
            except Exception:
                pass
    return index


def build_localization_index():
    """Parse english/global.ini -> {key.lower(): display_string}."""
    ini_path = OUTPUT_DIR / "Data" / "Localization" / "english" / "global.ini"
    index = {}
    if not ini_path.exists():
        print("  WARNING: english/global.ini not found, names will be class names")
        return index
    try:
        text = ini_path.read_text(encoding="utf-8-sig", errors="replace")
        for line in text.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip()
                if k:
                    index[k.lower()] = v
    except Exception as e:
        print(f"  WARNING: localization load failed: {e}")
    print(f"  {len(index):,} localization strings loaded")
    return index

# ── Helpers ────────────────────────────────────────────────────────────────────

def resolve_entity(class_name, class_ref, uuid_idx, cls_idx):
    """Return (resolved_class_name, xml_path) or (None, None)."""
    if class_name:
        path = cls_idx.get(class_name.lower())
        return class_name, path
    if class_ref and class_ref != "00000000-0000-0000-0000-000000000000":
        entry = uuid_idx.get(class_ref)
        if entry:
            return entry["class"], entry["path"]
    return None, None


def _fmt(v, decimals=0, suffix=""):
    """Format a numeric string; return '' on failure."""
    try:
        f = float(v)
        s = f"{f:,.{decimals}f}" if decimals else f"{f:,.0f}"
        return s + suffix
    except (ValueError, TypeError):
        return str(v) if v else ""


def _get_attach_def(root):
    for elem in root.iter():
        if "AttachDef" in elem.tag or elem.tag == "AttachDef":
            return (
                elem.get("Type", ""),
                elem.get("SubType", ""),
                elem.get("Size", ""),
                elem.get("Grade", ""),
            )
    return "", "", "", ""


def _get_display_name(root, loc_idx):
    """Resolve the human-readable display name from a component XML root.
    Looks for <Localization Name="@item_NameXXX"/> or
    <SCItemPurchasableParams displayName="@item_NameXXX"/> then looks up
    the key in the localization index.
    """
    if not loc_idx:
        return ""
    loc_key = ""
    for elem in root.iter():
        tag = elem.tag
        if "Localization" in tag:
            n = elem.get("Name", "")
            if n and n.startswith("@") and n != "@LOC_UNINITIALIZED":
                loc_key = n[1:]; break
        dn = elem.get("displayName", "")
        if dn and dn.startswith("@") and dn != "@LOC_UNINITIALIZED":
            loc_key = dn[1:]; break
    if not loc_key:
        return ""
    return loc_idx.get(loc_key.lower(), "")

# ── Component parsers ──────────────────────────────────────────────────────────

def parse_ammo(ammo_uuid, uuid_idx):
    if not ammo_uuid or ammo_uuid == "00000000-0000-0000-0000-000000000000":
        return {}
    entry = uuid_idx.get(ammo_uuid)
    if not entry or not Path(entry["path"]).exists():
        return {}
    try:
        root = ET.parse(entry["path"]).getroot()
    except Exception:
        return {}
    info = {"speed": root.get("speed",""), "lifetime": root.get("lifetime","")}
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "DamageInfo" in elem.tag or pt == "DamageInfo":
            info["dmg_physical"]   = elem.get("DamagePhysical","0")
            info["dmg_energy"]     = elem.get("DamageEnergy","0")
            info["dmg_distortion"] = elem.get("DamageDistortion","0")
            info["dmg_thermal"]    = elem.get("DamageThermal","0")
            break
    return info


def parse_weapon(xml_path, uuid_idx, cls_idx, loc_idx=None):
    """Weapon/gun stats."""
    if not xml_path or not Path(xml_path).exists():
        return {}
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return {}
    info = {"class": root.tag.split(".", 1)[-1] if "." in root.tag else root.tag}
    for elem in root.iter():
        if "AttachDef" in elem.tag or elem.tag == "AttachDef":
            info.update({"type": elem.get("Type",""), "subtype": elem.get("SubType",""),
                         "size": elem.get("Size",""), "grade": elem.get("Grade",""),
                         "mfr_uuid": elem.get("Manufacturer","")})
            break
    # Display name: localization lookup first, fall back to plain Name attr
    info["display_name"] = _get_display_name(root, loc_idx)
    if not info["display_name"]:
        for elem in root.iter():
            n = elem.get("Name","")
            if n and not n.startswith("@") and len(n) > 2:
                info["display_name"] = n; break
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "AmmoContainer" in elem.tag or "ammoContainer" in pt:
            info["ammo_count"] = elem.get("initialAmmoCount","")
            info["ammo_uuid"]  = elem.get("ammoParamsRecord","")
            break
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if any(k in pt for k in ("SWeaponActionFireSingle", "SWeaponActionFireRapid",
                                  "SWeaponActionFireBurst", "SWeaponActionFireCharged")):
            fr = elem.get("fireRate","")
            try:
                if float(fr) > 0:
                    info["fire_rate"] = fr; break
            except (ValueError, TypeError):
                pass
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if pt == "SWeaponAIDataParams" or "WeaponAIData" in pt:
            info["ideal_range"] = elem.get("idealCombatRange","")
            info["max_range"]   = elem.get("maxFiringRange","")
            break
    return info


def parse_ifcs(xml_path):
    """Flight controller → speed stats."""
    if not xml_path or not Path(xml_path).exists():
        return {}
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return {}
    info = {}
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if pt == "IFCSParams" or "IFCSParams" in elem.tag:
            info["scm_speed"] = elem.get("scmSpeed","")
            info["boost_fwd"] = elem.get("boostSpeedForward","")
            info["boost_bwd"] = elem.get("boostSpeedBackward","")
            info["max_speed"] = elem.get("maxSpeed","")
            break
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if pt == "AfterburnerParams" or "AfterburnerParams" in elem.tag:
            info["ab_capacitor"] = elem.get("capacitorMax","")
            info["ab_regen"]     = elem.get("capacitorRegenPerSec","")
            break
    return info


def _scu_from_inv_root(inv_root):
    for elem in inv_root.iter():
        if elem.tag == "interiorDimensions" or "interiorDimensions" in elem.tag:
            try:
                x = float(elem.get("x",0)); y = float(elem.get("y",0)); z = float(elem.get("z",0))
                if x and y and z:
                    return round(x/1.25) * round(y/1.25) * round(z/1.25)
            except (ValueError, TypeError):
                pass
    for elem in inv_root.iter():
        if "SStandardCargoUnit" in elem.get("__polymorphicType",""):
            try:
                return round(float(elem.get("standardCargoUnits","0")))
            except (ValueError, TypeError):
                pass
    return 0


def parse_cargo_scu(entity_path, uuid_idx):
    if not entity_path or not Path(entity_path).exists():
        return 0
    try:
        root = ET.parse(entity_path).getroot()
    except Exception:
        return 0
    if root.tag.startswith("InventoryContainer"):
        return _scu_from_inv_root(root)
    container_uuid = None
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemInventoryContainerComponentParams" in pt or "SCItemInventoryContainerComponentParams" in elem.tag:
            container_uuid = elem.get("containerParams",""); break
    if not container_uuid or container_uuid == "00000000-0000-0000-0000-000000000000":
        return 0
    entry = uuid_idx.get(container_uuid)
    if not entry or not Path(entry["path"]).exists():
        return 0
    try:
        return _scu_from_inv_root(ET.parse(entry["path"]).getroot())
    except Exception:
        return 0


def parse_component_stats(xml_path, uuid_idx, loc_idx=None):
    """Extract component-type stats from any scitem XML.
    Returns: {display_name, type, sub_type, size, grade, stats: [(label, value), ...]}
    """
    if not xml_path or not Path(xml_path).exists():
        return {}
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        return {}

    typ, sub_typ, size, grade = _get_attach_def(root)
    info = {"display_name": _get_display_name(root, loc_idx),
            "type": typ, "sub_type": sub_typ, "size": size, "grade": grade, "stats": []}

    # ── Shield ────────────────────────────────────────────────────────────────
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemShieldGeneratorParams" in pt or "SCItemShieldGeneratorParams" in elem.tag:
            s = []
            hp    = elem.get("MaxShieldHealth","");   hp    and s.append(("HP",          _fmt(hp)))
            regen = elem.get("MaxShieldRegen","");    regen and s.append(("Regen/s",     _fmt(regen)))
            ddown = elem.get("DownedRegenDelay","");  ddown and s.append(("Delay (down)",_fmt(ddown,1)+"s"))
            ddmg  = elem.get("DamagedRegenDelay",""); ddmg  and s.append(("Delay (dmg)", _fmt(ddmg,1)+"s"))
            decay = elem.get("DecayRatio","");        decay and s.append(("Decay",       _fmt(decay,2)))
            info["stats"] = s; return info

    # ── Power Plant ───────────────────────────────────────────────────────────
    # Guard: only power plants have SCItemPowerPlantParams — prevents false matches
    # on coolers/controllers/etc that also carry EntityComponentPowerConnection (as draw)
    has_ppp = any(
        "SCItemPowerPlantParams" in elem.get("__polymorphicType","") or
        "SCItemPowerPlantParams" in elem.tag
        for elem in root.iter()
    )
    if has_ppp:
        for elem in root.iter():
            pt = elem.get("__polymorphicType","")
            if "EntityComponentPowerConnection" in pt or "EntityComponentPowerConnection" in elem.tag:
                s = []
                pw     = elem.get("PowerDraw","")
                oc_min = elem.get("OverclockThresholdMin","")
                oc_max = elem.get("OverclockThresholdMax","")
                op_p   = elem.get("OverpowerPerformance","")
                em     = elem.get("PowerToEM","")
                pw     and s.append(("Power Out",    _fmt(pw,1)))
                (oc_min and oc_max) and s.append(("OC Range",
                    f"{float(oc_min)*100:.0f}-{float(oc_max)*100:.0f}%"))
                op_p   and s.append(("Overpower",    _fmt(float(op_p)*100,1)+"%"))
                em     and s.append(("Power->EM",    _fmt(em,3)))
                info["stats"] = s; return info

    # ── Cooler ────────────────────────────────────────────────────────────────
    # Must come BEFORE the fuel/SStandardResourceUnit check — cooler XMLs also
    # contain SStandardResourceUnit (coolant capacity) which would falsely match
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemCoolerParams" in pt or "SCItemCoolerParams" in elem.tag:
            s = []
            cr = elem.get("CoolingRate",""); cr and s.append(("Cooling/s",    _fmt(cr)))
            ir = elem.get("SuppressionIRFactor",""); ir and s.append(("IR Suppress", _fmt(ir,2)))
            hf = elem.get("SuppressionHeatFactor",""); hf and s.append(("Heat Suppress",_fmt(hf,2)))
            info["stats"] = s; return info

    # ── Quantum Drive ─────────────────────────────────────────────────────────
    qd_qfr = ""
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemQuantumDriveParams" in pt or "SCItemQuantumDriveParams" in elem.tag:
            qd_qfr = elem.get("quantumFuelRequirement","")
    for elem in root.iter():
        ds = elem.get("driveSpeed",""); st = elem.get("spoolUpTime","")
        if ds and st:
            s = []
            try:
                dsv = float(ds)
                s.append(("Speed", f"{dsv/1e6:.0f} Mm/s" if dsv >= 1e6 else f"{dsv:.0f} m/s"))
            except (ValueError, TypeError):
                pass
            st and s.append(("Spool",    _fmt(st,1)+"s"))
            cd = elem.get("cooldownTime",""); cd and s.append(("Cooldown", _fmt(cd,1)+"s"))
            if qd_qfr:
                try:
                    s.append(("Fuel/Gm", f"{float(qd_qfr)*1e9:.2f}"))
                except (ValueError, TypeError):
                    pass
            info["stats"] = s; return info

    # ── Weapon Gun (must come BEFORE fuel check — weapons also have SStandardResourceUnit) ──
    # Identified by SWeaponActionFire* polymorphicType (the actual fire-mode params).
    # noPowerStats / underpowerStats also carry fireRate=0; skip those via > 0 guard.
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if any(k in pt for k in ("SWeaponActionFireSingle", "SWeaponActionFireRapid",
                                  "SWeaponActionFireBurst", "SWeaponActionFireCharged")):
            fr = elem.get("fireRate","")
            try:
                fr_val = float(fr)
                if fr_val > 0:
                    s = [("Fire Rate", f"{fr_val:.0f}/min")]
                    # Ammo → damage + count
                    for aelem in root.iter():
                        apt = aelem.get("__polymorphicType","")
                        if "SAmmoContainerComponentParams" in apt or (
                                "AmmoContainer" in aelem.tag and aelem.get("ammoParamsRecord")):
                            ammo_uuid = aelem.get("ammoParamsRecord","")
                            ammo_cnt  = aelem.get("initialAmmoCount","")
                            if ammo_cnt and ammo_cnt != "0":
                                s.append(("Ammo", ammo_cnt))
                            if ammo_uuid and ammo_uuid != "00000000-0000-0000-0000-000000000000":
                                ammo = parse_ammo(ammo_uuid, uuid_idx)
                                spd = ammo.get("speed","")
                                spd and s.append(("Spd", _fmt(spd)+"m/s"))
                                dmg_parts = []
                                for dk, dl in [("dmg_physical","P"),("dmg_energy","E"),
                                               ("dmg_distortion","D"),("dmg_thermal","T")]:
                                    try:
                                        v = float(ammo.get(dk,"0") or "0")
                                        if v > 0: dmg_parts.append(f"{dl}:{v:.1f}")
                                    except (ValueError, TypeError):
                                        pass
                                try:
                                    total = sum(float(ammo.get(k,"0") or "0")
                                                for k in ("dmg_physical","dmg_energy",
                                                          "dmg_distortion","dmg_thermal"))
                                    if total > 0:
                                        s.append(("Dmg/shot", f"{total:.1f}"))
                                        if len(dmg_parts) > 1:
                                            s.append(("Type", " ".join(dmg_parts)))
                                except (ValueError, TypeError):
                                    pass
                            break
                    # Range from weaponAIData
                    for aelem in root.iter():
                        if aelem.tag == "weaponAIData" or "weaponAIData" in aelem.tag.lower():
                            ir = aelem.get("idealCombatRange","")
                            mr = aelem.get("maxFiringRange","")
                            ir and s.append(("Ideal", _fmt(ir)+"m"))
                            mr and s.append(("Max",   _fmt(mr)+"m"))
                            break
                    info["stats"] = s; return info
            except (ValueError, TypeError):
                pass

    # ── Fuel Tank (guard: only fires if SCItemFuelTankParams is present) ──────
    # This prevents SStandardResourceUnit from firing on thrusters / coolers / etc.
    has_ftank = any(
        "SCItemFuelTankParams" in elem.get("__polymorphicType","") or
        "SCItemFuelTankParams" in elem.tag
        for elem in root.iter()
    )
    if has_ftank:
        res_type = ""
        for elem in root.iter():
            r = elem.get("resource","")
            if r in ("Fuel","QuantumFuel"):
                res_type = r; break
        # Use SStandardCargoUnit (ResourceContainer child) — 1 SCU = 1,000,000 fuel units
        # Confirmed: Avenger H 4.5 SCU x2 = 9.0M, Q 1.1 SCU = 1.1M ✓
        for elem in root.iter():
            pt = elem.get("__polymorphicType","")
            if "SStandardCargoUnit" in pt or "SStandardCargoUnit" in elem.tag:
                v = elem.get("standardCargoUnits","")
                if v:
                    try:
                        cap_m = float(v)
                        lbl   = "Q-Fuel" if "Quantum" in res_type else "Fuel"
                        cap_s = f"{cap_m:g}M"   # "4.5M", "1.1M", "6.75M"
                        info["stats"] = [(lbl, cap_s)]; return info
                    except (ValueError, TypeError):
                        pass

    # ── Thruster ──────────────────────────────────────────────────────────────
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemThrusterParams" in pt or "SCItemThrusterParams" in elem.tag:
            s = []
            tc  = elem.get("thrustCapacity","")
            fbr = elem.get("fuelBurnRatePer10KNewton","")
            tt  = elem.get("thrusterType","")
            if tc:
                try:
                    tcv = float(tc)
                    s.append(("Thrust", f"{tcv/1000:,.0f} kN" if tcv >= 1000 else f"{tcv:.0f} N"))
                except (ValueError, TypeError):
                    pass
            tt  and s.append(("Type",     tt))
            fbr and s.append(("Fuel/10kN",_fmt(fbr,4)))
            info["stats"] = s; return info

    # ── Missile ───────────────────────────────────────────────────────────────
    trk = {}
    for elem in root.iter():
        sig = elem.get("trackingSignalType","")
        if sig:
            trk = {"signal":    sig,
                   "lock_time": elem.get("lockTime",""),
                   "range_max": elem.get("lockRangeMax",""),
                   "angle":     elem.get("lockingAngle","")}
            break
    ms_speed = ""
    for elem in root.iter():
        spd = elem.get("linearSpeed","")
        if spd and elem.get("fuelTankSize") is not None:
            ms_speed = spd; break
    ms_lifetime = ""
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "SCItemMissileParams" in pt or "SCItemMissileParams" in elem.tag:
            ms_lifetime = elem.get("maxLifetime",""); break
    ms_dmg = 0
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "DamageInfo" in elem.tag or pt == "DamageInfo":
            try:
                ms_dmg = sum(float(elem.get(k,"0") or 0) for k in
                             ("DamagePhysical","DamageEnergy","DamageDistortion","DamageThermal"))
            except (ValueError, TypeError):
                pass
            break
    if trk or ms_speed:
        s = []
        ms_speed    and s.append(("Speed",  _fmt(ms_speed)+" m/s"))
        trk.get("signal")    and s.append(("Track",  trk["signal"][:3]))
        trk.get("lock_time") and s.append(("Lock",   _fmt(trk["lock_time"],1)+"s"))
        trk.get("range_max") and s.append(("Range",  _fmt(trk["range_max"])+"m"))
        trk.get("angle")     and s.append(("FOV",    _fmt(trk["angle"],0)+"deg"))
        ms_lifetime and s.append(("Life",   _fmt(ms_lifetime,0)+"s"))
        ms_dmg > 0  and s.append(("Damage", _fmt(ms_dmg,0)))
        info["stats"] = s; return info

    # ── Turret — rotation + weapon slot sizes ──────────────────────────────────
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if "Axis" in pt and elem.get("speed"):
            info["stats"].append(("Rot/s", _fmt(elem.get("speed",""),0)+"deg/s"))
    port_sizes = []
    for elem in root.iter():
        if elem.tag == "SItemPortDef":
            pname = elem.get("Name","")
            pmin  = elem.get("MinSize",""); pmax = elem.get("MaxSize","")
            if "weapon" in pname.lower() and pmin:
                port_sizes.append(f"S{pmin}" if pmin == pmax else f"S{pmin}-{pmax}")
    if port_sizes:
        info["stats"].append(("Weapon slots", " / ".join(port_sizes)))

    # ── Radar / sensor ────────────────────────────────────────────────────────
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if any(k in pt for k in ("SCItemSensorParams","SCItemRadarParams","SensorEmitter")):
            for attr, lbl in [("sensorRadius","Radius"),("detectionRadius","Detect"),("maxRange","Max Range")]:
                v = elem.get(attr,""); v and info["stats"].append((lbl, _fmt(v)+"m"))
            break

    return info

# ── Ship parser ────────────────────────────────────────────────────────────────

def parse_ship(xml_path, uuid_idx, cls_idx, mfr_idx, loc_idx=None):
    path = Path(xml_path)
    if not path.exists():
        print(f"  MISSING: {path.name}"); return None
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        print(f"  PARSE ERROR {path.name}: {e}"); return None

    ship = {
        "file":       path.name,
        "class_name": root.tag.split(".", 1)[-1] if "." in root.tag else root.tag,
        "hardpoints": [],   # guns + turrets + missiles (for weapons table)
        "systems":    [],   # all other components keyed by category
    }

    # VehicleComponentParams
    for elem in root.iter():
        pt = elem.get("__polymorphicType","")
        if pt == "VehicleComponentParams" or "VehicleComponentParams" in elem.tag:
            ship.update({
                "vehicle_def":  elem.get("vehicleDefinition",""),
                "modification": elem.get("modification",""),
                "crew":         elem.get("crewSize",""),
                "hull_hp":      elem.get("vehicleHullDamageNormalizationValue",""),
                "vehicle_name": elem.get("vehicleName",""),
                "career":       elem.get("vehicleCareer",""),
                "role":         elem.get("vehicleRole",""),
                "cargo_scu":    0,
            })
            mfr_uuid         = elem.get("manufacturer","")
            ship["mfr_code"] = mfr_idx.get(mfr_uuid,"")
            prefix           = path.stem.split("_")[0].upper()
            ship["mfr_name"] = MFR_NAMES.get(ship["mfr_code"], MFR_NAMES.get(prefix, prefix))
            for e in elem.iter():
                if e.tag == "maxBoundingBoxSize":
                    ship["size_x"] = e.get("x",""); ship["size_y"] = e.get("y",""); ship["size_z"] = e.get("z","")
                    break
            break

    vn = ship.get("vehicle_name","")
    ship["display_name"] = (vn[len("@vehicle_Name"):].replace("_"," ")
                            if vn.startswith("@vehicle_Name")
                            else ship["class_name"].replace("_"," "))
    ship["ifcs"] = {}

    # ── ALL loadout entries ────────────────────────────────────────────────────
    for entry in root.iter("SItemPortLoadoutEntryParams"):
        port     = entry.get("itemPortName","")
        cls_name = entry.get("entityClassName","")
        cls_ref  = entry.get("entityClassReference","")
        if not port:
            continue
        null_ref = cls_ref == "00000000-0000-0000-0000-000000000000"
        if not cls_name and (not cls_ref or null_ref):
            continue

        port_lc  = port.lower()
        category = get_port_category(port_lc)

        if category in ("relay", "thruster", "radar"):
            continue

        resolved_cls, resolved_path = resolve_entity(cls_name, cls_ref, uuid_idx, cls_idx)

        # ── Cargo ──────────────────────────────────────────────────────────────
        if category == "cargo":
            if resolved_path:
                ship["cargo_scu"] += parse_cargo_scu(resolved_path, uuid_idx)
            continue

        # ── Flight controller → IFCS (also show in systems) ───────────────────
        if "controller_flight" in port_lc:
            if resolved_path:
                ship["ifcs"] = parse_ifcs(resolved_path)
            cstats = parse_component_stats(resolved_path, uuid_idx, loc_idx) if resolved_path else {}
            ship["systems"].append({
                "port": port, "category": "controller",
                "class": resolved_cls or "—",
                "display_name": cstats.get("display_name",""),
                "type": "Flight Controller", "size": cstats.get("size",""), "grade": cstats.get("grade",""),
                "stats": cstats.get("stats",[]),
            })
            continue

        # ── Weapons (guns + turrets + missiles) ───────────────────────────────
        if category in ("weapon", "turret", "missile"):
            w_info  = parse_weapon(resolved_path, uuid_idx, cls_idx, loc_idx) if resolved_path else {}
            ammo    = {}
            if w_info.get("ammo_uuid"):
                ammo = parse_ammo(w_info["ammo_uuid"], uuid_idx)
            # For missiles: overlay with missile stats
            if category == "missile":
                cstats = parse_component_stats(resolved_path, uuid_idx, loc_idx) if resolved_path else {}
                w_info["missile_stats"] = cstats.get("stats",[])
            # Turret: also capture turret-level stats
            if category == "turret":
                cstats = parse_component_stats(resolved_path, uuid_idx, loc_idx) if resolved_path else {}
                w_info["turret_stats"] = cstats.get("stats",[])
            ship["hardpoints"].append({
                "port":     port,
                "category": category,
                "class":    resolved_cls or "—",
                "weapon":   w_info,
                "ammo":     ammo,
            })
            continue

        # ── Everything else → systems ──────────────────────────────────────────
        cstats = parse_component_stats(resolved_path, uuid_idx, loc_idx) if resolved_path else {}
        ship["systems"].append({
            "port":         port,
            "category":     category,
            "class":        resolved_cls or "—",
            "display_name": cstats.get("display_name",""),
            "type":         cstats.get("type",""),
            "size":         cstats.get("size",""),
            "grade":        cstats.get("grade",""),
            "stats":        cstats.get("stats",[]),
        })

    # ── Cargo fallback (SOC-loaded, e.g. Constellation) ───────────────────────
    if ship["cargo_scu"] == 0:
        stem  = path.stem; parts = stem.split("_")
        if len(parts) >= 2:
            base = "_".join(parts[:2])
            for cls_key, cls_path in cls_idx.items():
                if any(x in cls_key for x in ("_template","_dur","_max","_mis")):
                    continue
                if cls_key.startswith(base+"_cargogrid") or cls_key.startswith(base+"_cargo_grid"):
                    ship["cargo_scu"] += parse_cargo_scu(cls_path, uuid_idx)

    return ship

# ── HTML generator ─────────────────────────────────────────────────────────────

MFR_COLORS = {
    "Aegis Dynamics":           "#1a6b8a",
    "Anvil Aerospace":          "#4a7a3a",
    "Crusader":                 "#7a6030",
    "Drake Interplanetary":     "#8a3030",
    "MISC":                     "#4a4a8a",
    "Origin Jumpworks":         "#6a4a8a",
    "Roberts Space Industries": "#2a5a7a",
    "Consolidated Outland":     "#5a6a3a",
}

def _stats_badge(stats):
    """Render [(label, value), ...] as inline badges."""
    if not stats:
        return '<span class="muted">—</span>'
    parts = []
    for k, v in stats:
        parts.append(f'<span class="badge"><span class="bl">{k}</span><span class="bv">{v}</span></span>')
    return " ".join(parts)


def ship_to_html(ship):
    mfr   = ship.get("mfr_name","Unknown")
    color = MFR_COLORS.get(mfr,"#444")
    name  = ship.get("display_name", ship.get("class_name","Unknown"))
    mod   = ship.get("modification","")

    # ── Stats grid ─────────────────────────────────────────────────────────────
    def _career(v): return (v or "—").replace("@vehicle_focus_","").replace("_"," ").title()
    stats = [
        ("Manufacturer", mfr),
        ("Variant",      mod or "—"),
        ("Crew",         ship.get("crew","—")),
        ("Hull HP",      _fmt(ship.get("hull_hp","0")) or "—"),
        ("Cargo (SCU)",  ship.get("cargo_scu",0) or "0"),
        ("Career",       _career(ship.get("career",""))),
        ("Role",         _career(ship.get("role",""))),
        ("Vehicle Def",  ship.get("vehicle_def","—")),
    ]
    ifcs = ship.get("ifcs",{})
    def _ms(v): return f"{float(v):.0f} m/s" if v else "—"
    IFCS_LABELS = {"SCM Speed","AB Fwd","AB Bwd","Max Speed","AB Capacitor","AB Regen"}
    if ifcs.get("scm_speed"):
        stats += [
            ("SCM Speed",    _ms(ifcs.get("scm_speed"))),
            ("AB Fwd",       _ms(ifcs.get("boost_fwd"))),
            ("AB Bwd",       _ms(ifcs.get("boost_bwd"))),
            ("Max Speed",    _ms(ifcs.get("max_speed"))),
            ("AB Capacitor", f"{ifcs.get('ab_capacitor','—')} u" if ifcs.get("ab_capacitor") else "—"),
            ("AB Regen",     f"{ifcs.get('ab_regen','—')} u/s" if ifcs.get("ab_regen") else "—"),
        ]
    stats_html = "".join(
        f'<div class="stat{"2" if k in IFCS_LABELS else ""}"><span class="label">{k}</span><span class="val">{v}</span></div>'
        for k, v in stats
    )

    # ── Weapons table ──────────────────────────────────────────────────────────
    hp_rows = ""
    for hp in ship.get("hardpoints",[]):
        w      = hp.get("weapon",{})
        ammo   = hp.get("ammo",{})
        cat    = hp.get("category","weapon")
        cls    = hp.get("class","—")
        wtype  = w.get("type","") or w.get("subtype","")
        size   = w.get("size",""); grade = w.get("grade","")
        sg     = f"S{size}" if size else ""
        sg    += f" G{grade}" if grade else ""

        dname     = w.get("display_name","") or ""
        dname_html = f'<span class="item-name">{dname}</span>' if dname else ""

        if cat == "missile":
            ms_stats = _stats_badge(w.get("missile_stats",[]))
            tag_cls  = "missile"
            hp_rows += f"""<tr>
              <td><span class="port">{hp["port"]}</span></td>
              <td class="comp-name">{dname_html}<code class="{tag_cls}">{cls}</code></td>
              <td><span class="cat-badge cat-missile">Missile {sg}</span></td>
              <td colspan="4">{ms_stats}</td>
            </tr>"""
        elif cat == "turret":
            ts_stats = _stats_badge(w.get("turret_stats",[]))
            tag_cls  = "turret"
            hp_rows += f"""<tr>
              <td><span class="port">{hp["port"]}</span></td>
              <td class="comp-name">{dname_html}<code class="{tag_cls}">{cls}</code></td>
              <td><span class="cat-badge cat-turret">Turret {sg}</span></td>
              <td colspan="4">{ts_stats}</td>
            </tr>"""
        else:
            # Gun weapon
            dmg_parts = []
            for dk, dl in [("dmg_physical","Phys"),("dmg_energy","Enrg"),
                           ("dmg_distortion","Dist"),("dmg_thermal","Therm")]:
                v = ammo.get(dk,"0") or "0"
                try:
                    if float(v) > 0: dmg_parts.append(f"{dl}: {float(v):.2f}")
                except (ValueError, TypeError):
                    pass
            dmg_str  = " | ".join(dmg_parts) if dmg_parts else "—"
            spd      = ammo.get("speed","")
            ammo_cnt = w.get("ammo_count","")
            fr       = w.get("fire_rate","")
            r_ideal  = w.get("ideal_range",""); r_max = w.get("max_range","")
            range_   = f"{r_ideal}m / {r_max}m" if r_max else "—"
            tag_cls  = "weapon"
            hp_rows += f"""<tr>
              <td><span class="port">{hp["port"]}</span></td>
              <td class="comp-name">{dname_html}<code class="{tag_cls}">{cls}</code></td>
              <td>{wtype} {sg}</td>
              <td class="dmg">{dmg_str}</td>
              <td>{(spd+"m/s") if spd else "—"}</td>
              <td>{ammo_cnt or "—"}</td>
              <td>{range_}</td>
            </tr>"""

    weapons_section = ""
    if hp_rows:
        weapons_section = f"""
        <h4>⚔ Weapons, Turrets &amp; Missiles ({len(ship.get("hardpoints",[]))})</h4>
        <table class="dtable">
          <thead><tr>
            <th>Port</th><th>Class</th><th>Type / Size</th>
            <th>Damage (per shot)</th><th>Proj Speed</th><th>Ammo</th><th>Range (ideal/max)</th>
          </tr></thead>
          <tbody>{hp_rows}</tbody>
        </table>"""
    else:
        weapons_section = "<p class='muted'>No weapon hardpoints in base loadout.</p>"

    # ── Systems sections ───────────────────────────────────────────────────────
    # Group by category
    from collections import defaultdict
    by_cat = defaultdict(list)
    for comp in ship.get("systems",[]):
        by_cat[comp.get("category","other")].append(comp)

    systems_html = ""
    for cat in SECTION_ORDER:
        comps = by_cat.get(cat,[])
        if not comps:
            continue
        icon, label, css = SECTION_META[cat]
        rows = ""
        for c in comps:
            sg    = f"S{c['size']}" if c.get("size") else ""
            sg   += f" G{c['grade']}" if c.get("grade") else ""
            dname = c.get("display_name","") or ""
            name_html = (f'<span class="item-name">{dname}</span>' if dname else "")
            rows += f"""<tr>
              <td><span class="port">{c["port"]}</span></td>
              <td class="comp-name">{name_html}<code class="{css}">{c["class"]}</code></td>
              <td>{c.get("type","") or "—"} {sg}</td>
              <td>{_stats_badge(c.get("stats",[]))}</td>
            </tr>"""
        systems_html += f"""
        <h4>{icon} {label} ({len(comps)})</h4>
        <table class="dtable">
          <thead><tr><th>Port</th><th>Component</th><th>Type / S/G</th><th>Stats</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    n_wp   = len(ship.get("hardpoints",[]))
    n_sys  = len(ship.get("systems",[]))
    return f"""
    <div class="ship-card" id="{ship['file'].replace('.xml','')}" data-mfr="{mfr}">
      <div class="ship-header" style="border-left:4px solid {color};" onclick="toggle(this)">
        <span class="ship-name">{name}</span>
        <span class="ship-meta">{mfr} &nbsp;·&nbsp; crew: {ship.get('crew','?')} &nbsp;·&nbsp; {n_wp} weapon ports &nbsp;·&nbsp; {n_sys} system components</span>
        <span class="arrow">&#9658;</span>
      </div>
      <div class="ship-body hidden">
        <div class="stats-grid">{stats_html}</div>
        {weapons_section}
        {systems_html}
        <p class="muted file-ref">Source: {ship['file']}</p>
      </div>
    </div>"""


def generate_html(ships):
    from collections import Counter
    valid = [s for s in ships if s]
    count = len(valid)
    cards = "\n".join(ship_to_html(s) for s in valid)

    # Manufacturer tabs
    mfr_counts = Counter(s.get("mfr_name","Unknown") for s in valid)
    mfr_list   = sorted(mfr_counts.keys())
    tabs_html  = f'<button class="tab active" data-mfr="all" onclick="setTab(this)">All <span class="tc">{count}</span></button>'
    for mfr in mfr_list:
        safe = mfr.replace("'", "&#39;")
        tabs_html += f'<button class="tab" data-mfr="{safe}" onclick="setTab(this)">{safe} <span class="tc">{mfr_counts[mfr]}</span></button>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SC DataPack - Ships</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:'Segoe UI',sans-serif; font-size:13px; line-height:1.5; padding:24px; }}
h1  {{ color:#58a6ff; margin-bottom:4px; font-size:22px; }}
.subtitle {{ color:#8b949e; margin-bottom:14px; font-size:12px; }}
/* ── Manufacturer tabs ── */
.mfr-bar {{ display:flex; flex-wrap:wrap; gap:5px; margin-bottom:10px; }}
.tab {{ background:#161b22; border:1px solid #30363d; border-radius:20px; padding:3px 10px;
        color:#8b949e; font-size:11px; cursor:pointer; transition:all 0.15s; }}
.tab:hover {{ border-color:#8b949e; color:#c9d1d9; }}
.tab.active {{ background:#1f6feb; border-color:#388bfd; color:#fff; }}
.tc {{ opacity:0.7; font-size:10px; }}
/* ── Search ── */
.search-row {{ display:flex; align-items:center; gap:10px; margin-bottom:16px; }}
#ship-search {{ background:#161b22; border:1px solid #30363d; border-radius:6px;
                padding:5px 10px; color:#c9d1d9; font-size:12px; width:280px; }}
#ship-search:focus {{ outline:none; border-color:#388bfd; }}
.result-count {{ color:#8b949e; font-size:11px; }}
/* ── Ship cards ── */
.ship-card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; margin-bottom:8px; overflow:hidden; }}
.ship-header {{ padding:12px 18px; cursor:pointer; display:flex; align-items:center; gap:16px; user-select:none; transition:background 0.15s; }}
.ship-header:hover {{ background:#1c2128; }}
.ship-name {{ font-size:15px; font-weight:600; color:#e6edf3; flex:0 0 auto; min-width:240px; }}
.ship-meta  {{ color:#8b949e; font-size:12px; flex:1; }}
.arrow {{ color:#8b949e; font-size:10px; transition:transform 0.2s; }}
.arrow.open {{ transform:rotate(90deg); }}
.ship-body {{ padding:0 18px 18px; }}
.hidden {{ display:none; }}
.stats-grid {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; padding:10px; background:#0d1117; border-radius:6px; }}
.stat,.stat2 {{ display:flex; flex-direction:column; min-width:120px; }}
.stat  .label {{ font-size:10px; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px; }}
.stat2 .label {{ font-size:10px; color:#3fb950; text-transform:uppercase; letter-spacing:0.5px; }}
.stat  .val   {{ font-size:12px; color:#e6edf3; word-break:break-all; }}
.stat2 .val   {{ font-size:12px; color:#7ee787; word-break:break-all; }}
h4 {{ color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin:14px 0 6px; }}
.dtable {{ width:100%; border-collapse:collapse; font-size:12px; }}
.dtable th {{ background:#0d1117; color:#8b949e; text-align:left; padding:5px 8px; font-weight:500; border-bottom:1px solid #30363d; }}
.dtable td {{ padding:4px 8px; border-bottom:1px solid #21262d; vertical-align:middle; }}
.dtable tr:last-child td {{ border-bottom:none; }}
.dtable tr:hover td {{ background:#1c2128; }}
code {{ background:#1c2128; border:1px solid #30363d; border-radius:3px; padding:1px 4px; font-size:11px; font-family:Consolas,monospace; color:#79c0ff; }}
code.missile  {{ color:#ffa657; }}
code.turret   {{ color:#d2a8ff; }}
code.sec-shield  {{ color:#58a6ff; }}
code.sec-power   {{ color:#e3b341; }}
code.sec-cooler  {{ color:#79c0ff; }}
code.sec-quantum {{ color:#bc8cff; }}
code.sec-fuel    {{ color:#7ee787; }}
code.sec-other   {{ color:#8b949e; }}
.port {{ color:#6e7681; font-size:11px; font-family:Consolas,monospace; }}
.item-name {{ display:block; color:#e6edf3; font-weight:600; font-size:12px; line-height:1.3; }}
.comp-name code {{ display:block; margin-top:1px; }}
.dmg  {{ color:#f85149; }}
.muted {{ color:#484f58; font-size:11px; margin-top:8px; }}
.file-ref {{ margin-top:6px; }}
.badge {{ display:inline-flex; background:#21262d; border:1px solid #30363d; border-radius:4px;
          padding:1px 0; font-size:11px; vertical-align:middle; margin:1px 2px 1px 0; }}
.badge .bl {{ padding:0 4px; color:#8b949e; border-right:1px solid #30363d; }}
.badge .bv {{ padding:0 5px; color:#e6edf3; }}
.cat-badge {{ display:inline-block; border-radius:3px; padding:1px 6px; font-size:11px; font-weight:600; }}
.cat-missile {{ background:#332500; color:#ffa657; border:1px solid #5a3a00; }}
.cat-turret  {{ background:#2d1f52; color:#d2a8ff; border:1px solid #4a3080; }}
</style>
</head>
<body>
<h1>&#x1F680; SC DataPack — Ships</h1>
<p class="subtitle">All loadout ports resolved &nbsp;·&nbsp; base loadouts only &nbsp;·&nbsp; {count} ships</p>
<div class="mfr-bar">{tabs_html}</div>
<div class="search-row">
  <input id="ship-search" type="text" placeholder="Search ship name..." oninput="applyFilters()">
  <span class="result-count" id="vis-count">{count} shown</span>
</div>
{cards}
<script>
function toggle(h) {{
  h.nextElementSibling.classList.toggle('hidden');
  h.querySelector('.arrow').classList.toggle('open');
}}
function setTab(btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function applyFilters() {{
  const mfr = document.querySelector('.tab.active').dataset.mfr;
  const q   = document.getElementById('ship-search').value.toLowerCase().trim();
  let vis = 0;
  document.querySelectorAll('.ship-card').forEach(c => {{
    const mok = mfr === 'all' || c.dataset.mfr === mfr;
    const nok = !q || c.querySelector('.ship-name').textContent.toLowerCase().includes(q);
    const show = mok && nok;
    c.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById('vis-count').textContent = vis + ' shown';
}}
</script>
</body>
</html>"""


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    uuid_idx  = build_uuid_index()
    cls_idx   = build_classname_index()
    mfr_idx   = build_manufacturer_index(uuid_idx)
    loc_idx   = build_localization_index()

    ship_paths = scan_all_ships()
    print(f"\nParsing {len(ship_paths)} ships (all manufacturers, no AI variants)...")
    ships = []
    for i, path in enumerate(ship_paths, 1):
        print(f"  [{i}/{len(ship_paths)}] {path.name}...", end=" ", flush=True)
        ship = parse_ship(path, uuid_idx, cls_idx, mfr_idx, loc_idx)
        if ship:
            print(f"ok ({len(ship['hardpoints'])} wp, {len(ship['systems'])} sys)")
        else:
            print("SKIP")
        ships.append(ship)

    html = generate_html(ships)
    out  = REPORTS_DIR / "ships_preview.html"
    out.write_text(html, encoding="utf-8")

    good = len([s for s in ships if s])
    print(f"\nDone. {good}/{len(ship_paths)} ships.")
    print(f"Report -> {out}")
    return out

if __name__ == "__main__":
    run()
