# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k` (~150 GB, 1.28 M files).
Produces human-readable HTML reference reports from raw game data.

> **Live reports →** <https://saladin1980.github.io/sc_datapack/>

---

## Reports

| Report | Description |
|---|---|
| [Ship Preview](https://saladin1980.github.io/sc_datapack/ships_preview.html) | Full loadout breakdown for a sample of ships — every port resolved to its component with stats (shields, power, cooling, QD, thrusters, weapons, cargo SCU, IFCS speeds) |
| [Component Reference](https://saladin1980.github.io/sc_datapack/components_preview.html) | 4,000+ equippable components by type — searchable, sortable, with key stats per item |

---

## Stack

- **Python 3.12** + [`scdatatools`](https://github.com/aegisx/scdatatools) (patched) for P4K access
- **unp4k.exe** for bulk extraction (~97 files/sec)
- **ElementTree** for XML parsing
- Zero runtime dependencies for the HTML reports (self-contained)

## Setup

```bash
# 1. Clone
git clone https://github.com/saladin1980/sc_datapack.git
cd sc_datapack

# 2. Edit paths to match your local SC data location
#    config/settings.py  →  BASE_DIR = Path("X:/SC_DataPack")

# 3. Create venv and install scdatatools
python -m venv venv
venv\Scripts\activate
pip install numpy>=1.24.3 line_profiler
pip install -e path/to/scdatatools-src

# 4. Extract (requires unp4k.exe)
python pipeline/extractor.py

# 5. Generate reports (after extraction)
python pipeline/ships_preview.py
python pipeline/components_preview.py
```

## Pipeline phases

| Phase | Script | Status |
|---|---|---|
| Extract P4K | `pipeline/extractor.py` | ✅ Done |
| Ship report | `pipeline/ships_preview.py` | ✅ Done |
| Component report | `pipeline/components_preview.py` | ✅ Done |
| Discovery / file map | `pipeline/discovery.py` | 🔜 Next |
| Converter | `pipeline/converter.py` | ⬜ TBD |

---

*Reports are generated from game data files and shared for community research purposes.*
