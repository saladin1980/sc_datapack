# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k` (~150 GB, 1.28 M files).
Produces human-readable HTML reference reports from raw game data.

> **Live reports →** <https://saladin1980.github.io/sc_datapack/>

---

## Reports

| Report | Items | Description |
|---|---|---|
| [Ships](https://saladin1980.github.io/sc_datapack/ships_preview.html) | 276 ships | Full loadout breakdown — every port resolved to its component with stats (shields, power, cooling, QD, thrusters, weapons, cargo SCU, IFCS speeds) |
| [Components](https://saladin1980.github.io/sc_datapack/components_preview.html) | 2,516 components | All equippable ship components by type — searchable with key stats per item |
| [Armor](https://saladin1980.github.io/sc_datapack/armor_preview.html) | 2,200+ items | All player armor by slot (Helmet/Torso/Arms/Legs/Undersuit/Backpack) and tier — damage resistances, temperature range, radiation, signatures, storage |

---

## Stack

- **unp4k.exe** — bulk P4K extraction (~97 files/sec, C# native)
- **Python 3.12** + stdlib only (`xml.etree`, `pathlib`) — XML parsing and HTML generation
- No runtime dependencies for the HTML reports (fully self-contained)

> `scdatatools` is installed in the venv for optional DCB exploration but is **not used** by any pipeline script.

## Setup

```bash
# 1. Clone
git clone https://github.com/saladin1980/sc_datapack.git
cd sc_datapack

# 2. Edit paths
#    config/settings.py  →  BASE_DIR = Path("X:/SC_DataPack")

# 3. Create venv (stdlib only — no extra packages needed for the pipeline)
python -m venv venv
venv\Scripts\activate

# 4. Extract (requires unp4k.exe — see EXTRACTION_PLAN.md for selective extraction)
python pipeline/extractor.py

# 5. Generate reports
python pipeline/ships_preview.py
python pipeline/components_preview.py
python pipeline/armor_preview.py
```

## What gets extracted

The pipeline only needs ~2.5 GB out of the full ~223 GB archive:

```
Data/Libs/Foundry/       2.3 GB  — all entity/item XML records
Data/Localization/        79 MB  — display name strings (global.ini)
```

See [`EXTRACTION_PLAN.md`](EXTRACTION_PLAN.md) for the full breakdown and selective extraction approach for future version updates.

## Pipeline phases

| Phase | Script | Status |
|---|---|---|
| Extract P4K | `pipeline/extractor.py` | ✅ Done |
| Ship report | `pipeline/ships_preview.py` | ✅ Done |
| Component report | `pipeline/components_preview.py` | ✅ Done |
| Armor report | `pipeline/armor_preview.py` | ✅ Done |
| Weapons report | `pipeline/weapons_preview.py` | 🔜 Next |

---

*Reports are generated from game data files and shared for community research purposes.*
