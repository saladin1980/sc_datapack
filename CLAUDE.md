# SC DataPack Pipeline — Claude Project Instructions

## CRITICAL: Deployment workflow

GitHub Pages is served from the ROOT of the `gh-pages` branch.
NOT from any folder on main. NOT from main at all.

```
gh-pages branch root/
  index.html                  <- live landing page (separate from runner.py's reports/index.html)
  ships_preview.html
  components_preview.html
  armor_preview.html
  weapons_preview.html
  groundvehicles.html
  items_preview.html
  JSON/
    ships.json
    components.json
    armor.json
    weapons.json
    ground_vehicles.json
    items.json
```

### To deploy a new or updated report:

```bash
git checkout gh-pages
cp <reports_dir>\<report>.html .
# edit index.html to add/update the card (match existing card style)
git add <report>.html index.html
git commit -m "feat: ..."
git push origin gh-pages
git checkout main
```

Index card style: `display: flex; flex-wrap: wrap` container, cards `width: 380px`.
Match `.card-icon / .card-title / .card-desc / .card-meta` pattern exactly.

---

## Repo structure (main branch)

```
repo root/
  runner.py           <- entry point (runs full pipeline, manages venv + caching)
  .env                <- user config (gitignored — never commit)
  .env.example        <- config template (committed)
  .gitignore
  README.md
  CLAUDE.md           <- this file

  DOCS\
    README.md
    EXTRACTION_PLAN.md
    DATA_SOURCES.md

  SCRIPTS\
    README.md
    config\
      settings.py     <- env config reader + GAME_VERSION parser
    pipeline\
      extractor.py        <- phase 1: DataCore XML dump + localization extraction
      ships.py            <- ships report + ships.json
      components.py       <- components report + components.json
      armor.py            <- armor report + armor.json
      weapons.py          <- weapons report + weapons.json
      groundvehicles.py   <- ground vehicles report + ground_vehicles.json
      items.py            <- items report + items.json
      export_json.py      <- shared JSON export utility (called by all report scripts)

  Tools\
    README.md
    unp4k-suite\      <- gitignored (user installs)
    venv\             <- gitignored (auto-created on first run)

  Data_Extraction\    <- gitignored (created on run, ~400 MB)
  reports\            <- gitignored (created on run — HTML + JSON outputs)
    JSON\             <- JSON exports of all datasets
```

---

## Settings / config

`SCRIPTS\config\settings.py` reads `.env` from repo root, then env vars.

| Variable | Default | Notes |
|---|---|---|
| `SC_P4K_PATH` | auto-detected RSI LIVE path | Required if not at default RSI install |
| `SC_OUTPUT_DIR` | `Data_Extraction\` | Extracted XML cache |
| `SC_REPORTS_DIR` | `reports\` | HTML + JSON output |
| `SC_LOGS_DIR` | `Data_Extraction\logs\` | Pipeline logs |

`SC_UNP4K_EXE` is NOT required — extraction is done via scdatatools (Python, auto-installed).

`GAME_VERSION` is parsed from `build_manifest.id` next to Data.p4k and displayed in all report subtitles.

---

## Runner flags

```bash
python runner.py                         # full run: extract + all reports
python runner.py --skip-extract          # reports only (extraction already cached)
python runner.py --force                 # rebuild all reports (extraction cache respected)
python runner.py --only ships            # single report — ships | components | armor
python runner.py --only weapons          #               weapons | vehicles | items
```

Cache logic (three layers):
1. **Extraction** — skips if `Data_Extraction/.version` matches current game version
2. **Version bump** — if new game patch detected, clears stale HTML reports before re-extracting
3. **Reports** — each HTML skips independently if its file already exists; `--force` overrides

---

## Pipeline status (SC 4.6.0-live.11319298, 2026-03-01)

All steps confirmed working — two clean back-to-back test runs.

| Script | Count | HTML output | JSON output |
|---|---|---|---|
| `extractor.py` | 24,667 XML records | — | — |
| `ships.py` | 257 flyable ships | `ships_preview.html` | `ships.json` |
| `components.py` | 1,791 components | `components_preview.html` | `components.json` |
| `armor.py` | 2,208 armor pieces | `armor_preview.html` | `armor.json` |
| `weapons.py` | 601 weapons (166/333/102) | `weapons_preview.html` | `weapons.json` |
| `groundvehicles.py` | 27 vehicles | `groundvehicles.html` | `ground_vehicles.json` |
| `items.py` | 501 items | `items_preview.html` | `items.json` |
| `export_json.py` | shared utility | — | called by all above |

Total pipeline runtime: ~15 min first run (extraction), ~3 min reports-only (cached).

Non-flyable ships excluded from `ships.py`: `_Derelict`, `_Wreck`, `_Template`,
`_PU_GameMaster`, `_PU_Invictus`, `_Drug_`, `_PU_Pirate_` patterns.

---

## JSON schema (postgres-ready, 2026-03-01)

All JSON files share the same envelope:
```json
{ "meta": { "game_version", "generated_at", "count" }, "data": [ {...} ] }
```

Key cross-file fields for Postgres joining:
- `ships.manufacturer_code` — canonical 4-letter code (AEGS, ANVL, MISC...) derived from class_name prefix
- `ships.canonical_name` — ship name without mfr prefix ("Gladius") — UEX API join key
- `ships.uex_id` — null placeholder, populated later via UEX Corp API match
- `weapons.class_name` — DataCore XML stem — links to ship hardpoint class references
- `components.manufacturer_code` — normalized from DataCore's truncated codes (AEG→AEGS, BEH→BEHR)

DataCore Code field is TRUNCATED in game data (AEGS→AEG, BEHR→BEH, MISC→MIS, MRAI collides with MISC on MIS).
Fix: ships use class_name prefix as authoritative code source. Components use `_COMP_MFR_CODE_NORM` dict.

---

## CRITICAL: P4K data structure

Individual game records are NOT individual files in Data.p4k.
They live INSIDE `Data/Game2.dcb` (DataCore binary, ~285 MB).

```python
sc.datacore          # DataCoreBinary — 68-112s to load
dc.records           # 108,864 total records
dc.dump_record_xml(record)  # XML string (needs sanitization)
```

Extraction writes XML to `Data_Extraction/Data/Libs/foundry/records/...`
Version is tracked in `Data_Extraction/.version` — matches against `build_manifest.id`.

---

## Windows notes

- Terminal is CP1252 — no Unicode arrows in `print()`, use ASCII (`->`)
- Add `sys.stdout.flush()` after progress prints
- Python 3.12 f-strings: can't use escaped quotes inside f-strings — use intermediate vars
- Stray `nul` file: Windows artifact from redirected commands — in `.gitignore`
