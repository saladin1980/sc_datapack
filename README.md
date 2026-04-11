# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k`.
Produces human-readable HTML reference reports and machine-readable JSON exports from raw game data — no AI, pure Python.

> **Live reports →** <https://saladin1980.github.io/sc_datapack/>

---

## Reports

| Report | Items | Description |
|---|---|---|
| [Ships](https://saladin1980.github.io/sc_datapack/ships_preview.html) | 257 | Full loadout — every hardpoint and system port resolved to its component, with stats (shields, power, cooling, QD, thrusters, weapons, cargo, IFCS speeds), insurance times. Includes purchase locations and prices where available. |
| [Components](https://saladin1980.github.io/sc_datapack/components_preview.html) | 1,791 | All equippable ship components by type — searchable, key stats per item, sold-at locations inline |
| [Armor](https://saladin1980.github.io/sc_datapack/armor_preview.html) | 2,208 | All player armor by slot and tier — damage resistances, temperature, radiation, signatures, storage, purchase locations |
| [Weapons](https://saladin1980.github.io/sc_datapack/weapons_preview.html) | 618 | Ship weapons, FPS personal weapons, and attachments — damage, fire rate, bullet speed, mag capacity, range, purchase locations |
| [Ground Vehicles](https://saladin1980.github.io/sc_datapack/groundvehicles.html) | 27 | All player ground vehicles — specs, dimensions, insurance times |
| [Items](https://saladin1980.github.io/sc_datapack/items_preview.html) | 501 | Consumables, food & drink, melee weapons, throwables, tools, hacking chips — purchase locations where available |
| [Shops](https://saladin1980.github.io/sc_datapack/shops.html) | 6,300+ | All shop terminal inventories — what sells where and at what price. Filterable by location and category. |
| [Mining](https://saladin1980.github.io/sc_datapack/mining_report.html) | — | Mineable elements with base values, resistance, and instability. Rock compositions by planet/moon. FPS mineable locations. |
| [Mining Gear](https://saladin1980.github.io/sc_datapack/mining_attachments_report.html) | — | Ship mining lasers, active/passive laser modules with stat modifiers, FPS mining gadgets |
| [Crafting](https://saladin1980.github.io/sc_datapack/crafting_report.html) | 998 | All crafting blueprints — material requirements, craft times, stat modifier slots, item families and variants by manufacturer |
| [Crafting Calculator](https://saladin1980.github.io/sc_datapack/crafting_calculator.html) | — | Interactive browser tool — enter your mineral inventory, see exactly what you can craft. No server required. |
| [Loot Tables](https://saladin1980.github.io/sc_datapack/loot_report.html) | 190 | Loot tables by location type (UGF, derelict, distribution center, contested zone, etc.) with archetype slot breakdown and weights |

All reports are also exported as JSON (`reports/JSON/`) — see [JSON exports](#json-exports) below.

---

## Quick start

**Step 1 — Clone the repo:**
```
git clone https://github.com/saladin1980/sc_datapack.git
cd sc_datapack
```

**Step 2 — Point it at your game files (no copying needed):**

> If you installed Star Citizen to the default location (`C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\`) you can **skip this step entirely** — the pipeline finds `Data.p4k` automatically.

If you installed to a custom path, copy `.env.example` to `.env` and set:
```
SC_P4K_PATH=D:\StarCitizen\LIVE\Data.p4k
```

> Data.p4k is ~150 GB. Do **not** copy it — just point the pipeline at your existing install.

**Step 3 — Run:**
```
python runner.py
```

That's it. Dependencies are installed automatically on first run (~1-2 min).
Reports land in `reports\` when done (~12 min first run on NVMe, longer on SATA SSD/HDD, significantly longer on portable/USB drives — ~5 min cached regardless of drive speed).

**Only requirement:** Python 3.12+ — [python.org](https://www.python.org/downloads/)

---

## Folder structure

```
sc_datapack\
  runner.py          <- run this to start everything
  .env               <- your config (copy from .env.example, gitignored)

  patches\           <- bundled scdatatools fixes applied automatically on first run
  SCRIPTS\           <- pipeline source code
  Tools\             <- venv (auto-created on first run, gitignored)
  Data_Extraction\   <- extracted XML cache (created on first run, ~1.6 GB, gitignored)
  reports\           <- generated HTML reports + JSON exports (gitignored)
    JSON\            <- machine-readable JSON for all datasets
```

---

## Runner flags

```bash
python runner.py                       # full run: extract + all reports
python runner.py --skip-extract        # reports only (extraction already cached)
python runner.py --force               # rebuild all reports (extraction cache respected)
python runner.py --only ships          # run a single report (always runs it)
```

Valid `--only` names: `ships` · `components` · `armor` · `weapons` · `vehicles` · `items` · `shops` · `mining` · `mining gear` · `crafting` · `crafting calc` · `loot tables`

**Smart caching — the pipeline skips work it's already done:**
- Re-running after reports are built is instant (HTML exists → skip)
- A new game patch auto-clears stale reports so they rebuild against fresh data
- `--force` rebuilds all reports without re-extracting

**Crash recovery:**
If the run is interrupted mid-way, just re-run with no flags. Extraction is skipped if the version already matches, and only the missing HTML reports are rebuilt. Nothing is ever re-done unnecessarily.

---

## Individual scripts

All scripts can be run standalone with the venv active:

```bash
python SCRIPTS\pipeline\extractor.py                   # extraction only
python SCRIPTS\pipeline\shops.py                       # shops report + shops.json
python SCRIPTS\pipeline\ships.py                       # ships report + ships.json
python SCRIPTS\pipeline\components.py                  # components report + components.json
python SCRIPTS\pipeline\armor.py                       # armor report + armor.json
python SCRIPTS\pipeline\weapons.py                     # weapons report + weapons.json
python SCRIPTS\pipeline\groundvehicles.py              # ground vehicles + ground_vehicles.json
python SCRIPTS\pipeline\items.py                       # items report + items.json
python SCRIPTS\pipeline\mining_report.py               # mining report + mining.json
python SCRIPTS\pipeline\mining_attachments_report.py   # mining gear report + mining_gear.json
python SCRIPTS\pipeline\crafting_report.py             # crafting report + crafting.json
python SCRIPTS\pipeline\crafting_calculator.py         # crafting calculator (no JSON)
python SCRIPTS\pipeline\loot_report.py                 # loot tables report + loot_tables.json
```

> Run `shops.py` before other reports — it writes `shops.json` which the other scripts use for "Available at" sections.

---

## JSON exports

Every report (except the interactive calculator) also writes a JSON file to `reports\JSON\`.
All files share the same envelope:

```json
{
  "meta": { "game_version": "4.7.0-live.11592622", "generated_at": "...", "count": 257 },
  "data": [ { ... } ]
}
```

| File | Records | Key fields |
|---|---|---|
| `ships.json` | 257 | `class_name`, `canonical_name`, `manufacturer_code`, `career`, `role`, `ins_wait_min`, `hardpoints[]`, `systems[]` |
| `components.json` | 1,791 | `class`, `name`, `manufacturer_code`, `stats [{label, value}]` |
| `armor.json` | 2,208 | `damage_resistance {}`, `signatures`, `temp_range`, `radiation` |
| `weapons.json` | 618 | `category` (ship/fps/attachment), `damage_by_type {}`, `fire_rate`, `range` |
| `ground_vehicles.json` | 27 | `dimensions`, `insurance`, `crew`, `drive_type` |
| `items.json` | 501 | `category`, `manufacturer`, `size`, `grade` |
| `shops.json` | 6,300+ | Flat join: one row per shop × item. `shop`, `location`, `class_name`, `buy_auec`, `sell_auec` |
| `mining.json` | — | Multi-section: `elements []`, `compositions []`, `planet_mineables []` |
| `mining_gear.json` | — | `category` (laser/active_module/passive_module/fps_gadget), stat modifiers |
| `crafting.json` | 998 | `family`, `part`, `craft_time`, `materials [{slot, mineral, quantity_scu}]` |
| `loot_tables.json` | 190 | `category`, `archetypes [{name, weight, max_results}]` |

---

## What gets extracted

Only ~1.6 GB of the archive is read and cached for report generation:

```
Data/Game2.dcb                          ~285 MB  — DataCore binary (all entity records)
Data/Localization/*/global.ini           ~79 MB  — display name strings (12 language files)
Data/Scripts/ShopInventories/*.json       ~2 MB  — shop terminal inventories (~120 files)
```

The extractor parses `Game2.dcb` in-memory (~75s load time) and dumps ~26,000 XML records to disk covering:

```
entities/spaceships/      — ship definitions and loadouts
entities/scitem/          — all player items, weapons, armor, components
entities/groundvehicles/  — ground vehicle definitions
scitemmanufacturer/       — manufacturer names and codes
damage/ + ammoparams/     — damage tables and ammo parameters
crafting/                 — blueprints, recipes, material requirements
lootgeneration/           — loot tables by location type
mining/                   — mineable elements, rock compositions
commodityconfiguration/   — commodity and resource type indexes
```

ShopInventories JSON files are extracted directly from the archive — no DataCore parsing needed.
No full archive extraction ever happens — `Data.p4k` is never modified or fully unpacked.

---

## scdatatools and compatibility

The pipeline uses [scdatatools](https://gitlab.com/scmodding/frameworks/scdatatools) for DataCore binary parsing and P4K archive access. It is installed automatically from PyPI on first run.

Because the PyPI release (1.0.4) predates several Star Citizen format changes, the pipeline bundles patch files in `patches/scdatatools/` that are applied automatically over the PyPI install on every first run:

- **`forge/`** — DataCore v6 parser support (SC 4.7+ changed the DCB binary format)
- **`sc/`** — `Game2.dcb` path fix + additional modules missing from PyPI
- **`engine/`** — `constants.py` and `model_utils.py` missing from PyPI release

No manual patching needed — `runner.py` handles this automatically.

---

## Stack

- **[scdatatools](https://gitlab.com/scmodding/frameworks/scdatatools)** — DataCore binary parsing and P4K access (auto-installed + patched on first run)
- **Python 3.12 stdlib** — `xml.etree`, `pathlib`, `json`, `zipfile`
- No AI, no heavy dependencies, no database required

---

*Data extracted from Star Citizen game files for community research purposes.*
