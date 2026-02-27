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

## Folder structure

```
sc_datapack\
  runner.py          <- START HERE — runs the full pipeline
  .env               <- your config (copy from .env.example, not committed)
  .env.example       <- config template

  DOCS\              <- documentation and reference files
  SCRIPTS\           <- pipeline source code (settings + individual scripts)
  Tools\             <- unp4k tool + Python venv (you install these)
  Data_Extraction\   <- extracted game files (created on first run)
  HTML\              <- generated HTML reports (created on first run)
```

---

## Quick start

### 1. Prerequisites
- **Python 3.12+** — [python.org](https://www.python.org/downloads/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **unp4k** — [github.com/dolkensp/unp4k](https://github.com/dolkensp/unp4k/releases) — download latest release, extract to `Tools\unp4k-suite\`

### 2. Clone
```bash
git clone https://github.com/saladin1980/sc_datapack.git
cd sc_datapack
```

### 3. Set up Python environment
```bash
python -m venv Tools\venv
Tools\venv\Scripts\activate
```

### 4. Configure paths
```bash
copy .env.example .env
```
Open `.env` and set your two required paths:
- `SC_P4K_PATH` — full path to your `Data.p4k` file
- `SC_UNP4K_EXE` — full path to `unp4k.exe`

### 5. Run
```bash
python runner.py
```

That's it. Reports land in `HTML\` when complete.

---

## Individual scripts

Run just one step at a time if needed:

```bash
python SCRIPTS\pipeline\extractor.py          # extract game files only
python SCRIPTS\pipeline\ships_preview.py      # ships report only
python SCRIPTS\pipeline\components_preview.py # components report only
python SCRIPTS\pipeline\armor_preview.py      # armor report only
python SCRIPTS\pipeline\weapons_preview.py    # weapons report only
```

Runner flags:
```bash
python runner.py --skip-extract       # re-run reports only (data already extracted)
python runner.py --only ships         # run just one report
```

---

## What gets extracted

Only ~2.4 GB out of the full archive is needed:

```
Data/Libs/Foundry/    2.3 GB  — all entity/item XML records
Data/Localization/     79 MB  — display name strings
```

See [`DOCS/EXTRACTION_PLAN.md`](DOCS/EXTRACTION_PLAN.md) for the full breakdown.

---

## Stack

- **[unp4k](https://github.com/dolkensp/unp4k)** — P4K extraction (C# native)
- **Python 3.12 stdlib only** — `xml.etree`, `pathlib`, `zipfile`
- No runtime pip dependencies, no AI

---

*Data extracted from Star Citizen game files for community research purposes.*
