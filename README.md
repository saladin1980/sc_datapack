# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k`.
Produces human-readable HTML reference reports and machine-readable JSON exports from raw game data — no AI, pure Python.

> **Live reports →** <https://saladin1980.github.io/sc_datapack/>

---

## Reports

| Report | Items | Description |
|---|---|---|
| [Ships](https://saladin1980.github.io/sc_datapack/ships_preview.html) | 257 | Full loadout — every hardpoint and system port resolved to its component, with stats (shields, power, cooling, QD, thrusters, weapons, cargo, IFCS speeds), insurance times |
| [Components](https://saladin1980.github.io/sc_datapack/components_preview.html) | 1,791 | All equippable ship components by type — searchable, key stats per item |
| [Armor](https://saladin1980.github.io/sc_datapack/armor_preview.html) | 2,208 | All player armor by slot and tier — damage resistances, temperature, radiation, signatures, storage |
| [Weapons](https://saladin1980.github.io/sc_datapack/weapons_preview.html) | 601 | Ship weapons, FPS personal weapons, and attachments — damage, fire rate, bullet speed, mag capacity, range, attachment slots |
| [Ground Vehicles](https://saladin1980.github.io/sc_datapack/groundvehicles.html) | 27 | All player ground vehicles — specs, dimensions, insurance times |
| [Items](https://saladin1980.github.io/sc_datapack/items_preview.html) | 501 | Consumables, food & drink, melee weapons, throwables, tools, hacking chips |

All reports are also exported as JSON (`reports/JSON/`) — see [JSON exports](#json-exports) below.

---

## Quick start

**Step 1 — Clone the repo:**
```
git clone https://github.com/saladin1980/sc_datapack.git
cd sc_datapack
```

**Step 2 — Point it at your game files (no copying needed):**

Copy `.env.example` to `.env`, then open it and set your path:
```
SC_P4K_PATH=C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k
```

> Data.p4k is ~150 GB. Do **not** copy it — just point the pipeline at your existing
> Star Citizen install. The default LIVE path is auto-detected if not set.

**Step 3 — Run:**
```
python runner.py
```

That's it. Dependencies are installed automatically on first run (~1-2 min).
Reports land in `reports\` when done (~15 min first run, ~3 min cached).

**Only requirement:** Python 3.12+ — [python.org](https://www.python.org/downloads/)

---

## Folder structure

```
sc_datapack\
  runner.py          <- run this to start everything
  .env               <- your config (copy from .env.example, gitignored)

  DOCS\              <- documentation and reference files
  SCRIPTS\           <- pipeline source code
  Tools\             <- venv (auto-created on first run)
  Data_Extraction\   <- extracted XML cache (created on first run, ~400 MB)
  reports\           <- generated HTML reports + JSON exports (created on first run)
    JSON\            <- machine-readable JSON for all datasets
```

---

## Runner flags

```bash
python runner.py                    # full run: extract + all reports
python runner.py --skip-extract     # reports only (extraction already cached)
python runner.py --force            # rebuild all reports (extraction cache respected)
python runner.py --only ships       # single report: ships | components | armor
python runner.py --only weapons     #               weapons | vehicles | items
```

Smart caching — the pipeline skips work it's already done:
- Re-running after reports are built is instant (HTML exists → skip)
- A new game patch auto-clears stale reports and re-extracts
- `--force` rebuilds all reports without re-extracting

---

## Individual scripts

```bash
python SCRIPTS\pipeline\extractor.py       # extraction only
python SCRIPTS\pipeline\ships.py           # ships report + ships.json
python SCRIPTS\pipeline\components.py      # components report + components.json
python SCRIPTS\pipeline\armor.py           # armor report + armor.json
python SCRIPTS\pipeline\weapons.py         # weapons report + weapons.json
python SCRIPTS\pipeline\groundvehicles.py  # ground vehicles report + ground_vehicles.json
python SCRIPTS\pipeline\items.py           # items report + items.json
```

---

## JSON exports

Every report script also writes a JSON file to `reports\JSON\` alongside its HTML.
All files share the same envelope:

```json
{
  "meta": { "game_version": "4.6.0-live.11319298", "generated_at": "...", "count": 257 },
  "data": [ { ... } ]
}
```

| File | Records | Notes |
|---|---|---|
| `ships.json` | 257 | Includes hardpoints[], systems[], manufacturer_code, canonical_name, uex_id |
| `components.json` | 1,791 | Includes manufacturer_code (normalized), stats [{label, value}] |
| `armor.json` | 2,208 | Includes damage_resistance dict, signatures, temp/radiation |
| `weapons.json` | 601 | Includes class_name (DataCore identifier), dmg by type, ranges |
| `ground_vehicles.json` | 27 | Includes insurance, dimensions |
| `items.json` | 501 | Includes category, manufacturer, size, grade |

---

## What gets extracted

Only ~400 MB of the archive is read for report generation:

```
Data/Game2.dcb        285 MB  — DataCore binary (ships, items, weapons, armor, components)
Data/Localization/     79 MB  — display name strings (12 language files)
```

The extractor parses Game2.dcb in-memory and dumps ~24,700 XML records to disk.
No full archive extraction required — Data.p4k is never modified.

---

## Stack

- **[scdatatools](https://gitlab.com/scmodding/frameworks/scdatatools)** — DataCore binary parsing (auto-installed on first run via git)
- **Python 3.12 stdlib** — `xml.etree`, `pathlib`, `json`, `zipfile`
- No AI, no heavy dependencies

---

*Data extracted from Star Citizen game files for community research purposes.*
