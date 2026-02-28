# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k`.
Produces human-readable HTML reference reports from raw game data — no AI, pure Python.

> **Live reports →** <https://saladin1980.github.io/sc_datapack/>

---

## Reports

| Report | Items | Description |
|---|---|---|
| [Ships](https://saladin1980.github.io/sc_datapack/ships_preview.html) | 276 | Full loadout — every port resolved to its component with stats (shields, power, cooling, QD, thrusters, weapons, cargo, IFCS speeds) |
| [Components](https://saladin1980.github.io/sc_datapack/components_preview.html) | 2,516 | All equippable ship components by type — searchable, key stats per item |
| [Armor](https://saladin1980.github.io/sc_datapack/armor_preview.html) | 2,200+ | All player armor by slot and tier — damage resistances, temperature, radiation, signatures, storage |
| [Weapons](https://saladin1980.github.io/sc_datapack/weapons_preview.html) | 601 | Ship weapons, FPS personal weapons, and attachments — damage, fire rate, bullet speed, mag capacity, range, attachment slots |

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
> Star Citizen install. The default LIVE path is shown above.

**Step 3 — Run:**
```
python runner.py
```

That's it. Dependencies are installed automatically on first run (~1-2 min).
Reports land in `HTML\` when done (~10 min total).

**Only requirement:** Python 3.12+ — [python.org](https://www.python.org/downloads/)

---

## Folder structure

```
sc_datapack\
  runner.py          <- run this to start everything
  .env               <- your config (copy from .env.example)

  DOCS\              <- documentation and reference files
  SCRIPTS\           <- pipeline source code
  Tools\             <- venv (auto-created on first run)
  Data_Extraction\   <- extracted game data (created on first run, ~400 MB)
  HTML\              <- generated HTML reports (created on first run)
```

---

## Runner flags

```bash
python runner.py                    # full run: extract + all reports
python runner.py --skip-extract     # reports only (already extracted)
python runner.py --only ships       # one report: ships / components / armor / weapons
```

## Individual scripts

```bash
python SCRIPTS\pipeline\extractor.py
python SCRIPTS\pipeline\ships_preview.py
python SCRIPTS\pipeline\components_preview.py
python SCRIPTS\pipeline\armor_preview.py
python SCRIPTS\pipeline\weapons_preview.py
```

---

## What gets extracted

Only ~400 MB of the archive is read for report generation:

```
Data/Game2.dcb        285 MB  — DataCore binary (ships, items, weapons, armor)
Data/Localization/     79 MB  — display name strings
```

The extractor parses Game2.dcb in-memory and dumps ~25,000 XML records to disk.
No full archive extraction required — Data.p4k is never modified.

---

## Stack

- **[scdatatools](https://gitlab.com/scmodding/frameworks/scdatatools)** — DataCore binary parsing (auto-installed on first run)
- **Python 3.12 stdlib** — `xml.etree`, `pathlib`, `urllib`, `zipfile`
- No AI

---

*Data extracted from Star Citizen game files for community research purposes.*
