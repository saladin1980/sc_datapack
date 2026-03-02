# SC DataPack — Docker Pipeline

Self-contained extraction pipeline for Star Citizen's `Data.p4k`.
Drop in the game file, get JSON data out. Runs continuously and re-processes automatically when `Data.p4k` changes.

---

## Setup

```bash
# 1. Build the image (one time, ~5 min)
docker build -t sc-datapack .

# 2. Create your data folder and drop Data.p4k into it
mkdir sc-data
cp /path/to/Data.p4k sc-data/

# 3. Start the container
docker run -d --restart unless-stopped \
  -v ./sc-data:/data \
  --name sc-datapack \
  sc-datapack
```

That's it. JSON files appear in `sc-data/JSON/` when the pipeline finishes (~8–10 min first run).

---

## With docker-compose (recommended)

```bash
cp .env.example .env
# edit .env: set DATA_DIR to your folder
docker compose up -d
```

`.env`:
```env
DATA_DIR=/path/to/your/folder
```

---

## How it works

The container watches `/data/Data.p4k` for changes every 5 minutes.
When a new or updated file is detected it runs the full pipeline automatically.
Drop a new `Data.p4k` in the folder after a game patch and it will re-process on its own.

```
sc-data/                   ← your folder (DATA_DIR)
  Data.p4k                 ← drop game file here
  build_manifest.id        ← optional, for proper version string in JSON meta
  JSON/                    ← output appears here
    ships.json
    components.json
    armor.json
    weapons.json
    ground_vehicles.json
    items.json
    shops.json
  .last_mtime              ← internal: tracks last processed version (do not delete)
```

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

All files use the same envelope:
```json
{
  "meta": { "game_version": "4.6.0-live.11319298", "generated_at": "...", "count": 257 },
  "data": [ { ... } ]
}
```

---

## Getting the game version string

Copy `build_manifest.id` from your SC install folder into `DATA_DIR` alongside `Data.p4k`.
This provides the proper version string (e.g. `4.6.0-live.11319298`) in every JSON file's `meta.game_version`.
Without it, version falls back to the `Data.p4k` modification date (`p4k-2026-03-01`).

Default SC install locations:
- **Windows:** `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\`
- **Linux:** `~/.local/share/Star Citizen/LIVE/`

---

## Logs

```bash
docker logs sc-datapack          # follow output
docker logs -f sc-datapack       # live tail
```

---

## Flags

```bash
# Run once and exit instead of staying in watch loop
docker run -v ./sc-data:/data sc-datapack python entrypoint.py --run-once

# Skip P4K extraction, re-run report scripts only
docker run -v ./sc-data:/data sc-datapack python entrypoint.py --run-once --skip-extract
```

---

## Environment variables

All optional.

| Variable | Default | Description |
|---|---|---|
| `SC_P4K_PATH` | `/data/Data.p4k` | Path to `Data.p4k` inside the container |
| `SC_OUTPUT_DIR` | `/work/extraction` | Intermediate DataCore XML (ephemeral) |
| `SC_REPORTS_DIR` | `/data` | Where JSON output is written |
| `SC_LOGS_DIR` | `/data/logs` | Log directory |

---

## Requirements

- Docker (any recent version)
- `Data.p4k` from your Star Citizen install (~154 GB)
- ~20 GB free disk space for intermediate extraction
- ~200 MB for the output JSON files
