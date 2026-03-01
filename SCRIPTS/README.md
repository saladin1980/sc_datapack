# SCRIPTS

Pipeline source code. All scripts read configuration from the `.env` file in the repo root.

## Structure

```
SCRIPTS\
  config\
    settings.py           <- path configuration + GAME_VERSION parser (reads from .env)
  pipeline\
    extractor.py          <- Phase 1: DataCore XML dump + localization extraction
    ships.py              <- ships HTML report + ships.json
    components.py         <- ship components HTML report + components.json
    armor.py              <- armor HTML report + armor.json
    weapons.py            <- weapons HTML report + weapons.json
    groundvehicles.py     <- ground vehicles HTML report + ground_vehicles.json
    items.py              <- items/consumables HTML report + items.json
    export_json.py        <- shared JSON export utility (called by all report scripts)
```

## Running individual scripts

The venv is activated automatically when you run via `runner.py`.
To run a single script manually, use the venv Python directly:

```bash
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\extractor.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\ships.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\components.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\armor.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\weapons.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\groundvehicles.py
Tools\venv\Scripts\python.exe SCRIPTS\pipeline\items.py
```

Or use `runner.py --only <name>` to run one report in context — see the main README.

## Import structure

Each script adds `SCRIPTS\` to `sys.path` and imports from `config.settings` (for paths + GAME_VERSION).
Report scripts also import shared helpers from `pipeline.ships` (localization index, UUID index builders).
All JSON export is handled by `pipeline.export_json` — called at the end of each report script's `run()`.

## Dependencies

`scdatatools` is the only non-stdlib dependency — auto-installed by `runner.py` on first run from the
upstream git repo (PyPI version 1.0.4 is broken on Python 3.12).
Everything else is Python 3.12 stdlib: `xml.etree`, `pathlib`, `json`, `zipfile`, `re`.
