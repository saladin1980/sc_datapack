# SC DataPack Pipeline

Extraction and parsing pipeline for Star Citizen's `Data.p4k`.
Produces human-readable HTML reference reports from raw game data — no AI, pure Python stdlib.

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

```
1. git clone https://github.com/saladin1980/sc_datapack.git
2. Place Data.p4k in the repo root folder
3. python runner.py
```

That's it. unp4k is downloaded automatically on first run. Reports land in `HTML\` when done.

**Only requirement:** Python 3.12+ — [python.org](https://www.python.org/downloads/)

---

## Folder structure

```
sc_datapack\
  Data.p4k           <- put your game data file here
  runner.py          <- run this to start everything

  DOCS\              <- documentation and reference files
  SCRIPTS\           <- pipeline source code
  Tools\             <- unp4k + venv (auto-created on first run)
  Data_Extraction\   <- extracted game files (created on first run)
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

## Custom paths (optional)

By default everything is relative to the repo root. To override (e.g. Data.p4k
is on a different drive), copy `.env.example` to `.env` and uncomment the lines
you need. No code editing required.

---

## What gets extracted

Only ~2.4 GB of the archive is needed for report generation:

```
Data/Libs/Foundry/    2.3 GB  — all entity/item XML records
Data/Localization/     79 MB  — display name strings
```

See [`DOCS/EXTRACTION_PLAN.md`](DOCS/EXTRACTION_PLAN.md) for the full breakdown.

---

## Stack

- **[unp4k](https://github.com/dolkensp/unp4k)** — P4K extraction (C# native, auto-downloaded)
- **Python 3.12 stdlib only** — `xml.etree`, `pathlib`, `urllib`, `zipfile`
- No pip dependencies, no AI

---

*Data extracted from Star Citizen game files for community research purposes.*
