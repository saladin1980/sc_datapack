# SC DataPack — Docker Pipeline

Self-contained extraction pipeline for Star Citizen's `Data.p4k`.
Drop in the game file, get JSON data out. No install required beyond Docker.

---

## What it produces

| File | Contents |
|---|---|
| `ships.json` | 257 flyable ships — loadout, dimensions, insurance, hardpoints |
| `components.json` | 1,791 ship components — type, size, grade, stats |
| `armor.json` | 2,208 armor pieces — resistances, signatures, storage |
| `weapons.json` | 601 weapons — ship, FPS, attachments, damage breakdown |
| `ground_vehicles.json` | 27 ground vehicles — specs, dimensions, insurance |
| `items.json` | 501 items — consumables, food, melee, tools, gadgets |
| `shops.json` | 5,994 shop inventory rows — what sells where and at what price |

All files follow the same envelope:
```json
{
  "meta": { "game_version": "4.6.0-live.11319298", "generated_at": "...", "count": 257 },
  "data": [ { ... } ]
}
```

---

## Requirements

- Docker (any recent version)
- `Data.p4k` from your Star Citizen install (`~154 GB`)
- ~20 GB free disk space for intermediate extraction
- ~200 MB for the output JSON files

---

## Quick start

```bash
# 1. Build the image (one time, ~5 min)
docker build -t sc-datapack .

# 2. Run — swap in your actual paths
docker run \
  -v /path/to/Data.p4k:/input/Data.p4k:ro \
  -v /path/to/output:/output \
  sc-datapack
```

JSON files will be at `/path/to/output/JSON/` when complete.

**First run takes ~8–10 min** (extraction + all reports).
Subsequent runs on the same game version take the same time — extraction always runs fresh inside the container.

---

## With docker-compose

Copy `.env.example` to `.env` and fill in your paths:

```env
# .env
P4K_PATH=/path/to/Data.p4k
OUTPUT_DIR=/path/to/output

# Optional — provides the game version string in JSON meta
MANIFEST_PATH=/path/to/build_manifest.id
```

Then:

```bash
docker compose up
```

---

## Output structure

```
/path/to/output/
  JSON/
    ships.json
    components.json
    armor.json
    weapons.json
    ground_vehicles.json
    items.json
    shops.json
```

HTML report files are also written alongside `JSON/` — these are for reference only and can be ignored.

---

## Environment variables

All optional. Defaults work with the standard volume mounts above.

| Variable | Default | Description |
|---|---|---|
| `SC_P4K_PATH` | `/input/Data.p4k` | Path to `Data.p4k` inside the container |
| `SC_OUTPUT_DIR` | `/work/extraction` | Where DataCore XML is extracted (ephemeral) |
| `SC_REPORTS_DIR` | `/output` | Where JSON and HTML output is written |
| `SC_LOGS_DIR` | `/work/logs` | Log output directory |

---

## Flags

```bash
# Skip P4K extraction — re-run report scripts only
# (only useful if you mount the extraction cache from a previous run)
docker run ... sc-datapack python entrypoint.py --skip-extract
```

---

## Including the game manifest (recommended)

The `build_manifest.id` file sits next to `Data.p4k` in your SC install folder.
Mounting it gives you the proper version string (`4.6.0-live.11319298`) in every JSON file's `meta.game_version`.
Without it, version falls back to the `Data.p4k` modification date (`p4k-2026-03-01`).

```bash
docker run \
  -v /path/to/Data.p4k:/input/Data.p4k:ro \
  -v /path/to/build_manifest.id:/input/build_manifest.id:ro \
  -v /path/to/output:/output \
  sc-datapack
```

Default SC install location:
- **Windows:** `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\`
- **Linux:** `~/.local/share/Star Citizen/LIVE/`
