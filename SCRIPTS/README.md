# SCRIPTS

Pipeline source code. All scripts read configuration from the `.env` file in the repo root.

## Structure

```
SCRIPTS\
  config\
    settings.py       <- path configuration (reads from .env)
  pipeline\
    extractor.py      <- Phase 1: selective P4K extraction
    ships_preview.py  <- Phase 2: ships HTML report
    components_preview.py  <- Phase 3: ship components HTML report
    armor_preview.py  <- Phase 4: armor HTML report
    weapons_preview.py     <- Phase 5: weapons HTML report
```

## Running individual scripts

Activate your venv first, then run from the repo root:

```bash
python SCRIPTS\pipeline\extractor.py
python SCRIPTS\pipeline\ships_preview.py
python SCRIPTS\pipeline\components_preview.py
python SCRIPTS\pipeline\armor_preview.py
python SCRIPTS\pipeline\weapons_preview.py
```

Or use the root `runner.py` to run everything in sequence — see the main README.

## Import structure

Each script adds `SCRIPTS\` to `sys.path` and imports from `config.settings`.
No pip packages required — Python 3.12 stdlib only.
