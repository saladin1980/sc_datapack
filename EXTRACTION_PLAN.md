# P4K Selective Extraction Plan

## Why selective extraction?

Full extraction of Data.p4k dumps ~223 GB across 1.28M files.
The pipeline only reads **XML records + one localization file**.
We can cut that down to ~2.5 GB with a targeted extract.

---

## Directory size breakdown (current full extract)

| Directory            | Size      | Files     | Needed? |
|----------------------|-----------|-----------|---------|
| Objects/             | 156.8 GB  | 1,015,909 | NO — 3D meshes |
| Textures/            | 29.7 GB   | 82,663    | NO — texture files |
| UI/                  | 10.2 GB   | 15,229    | NO — UI image assets |
| Sounds/              | 9.7 GB    | 110,609   | NO — audio |
| Animations/          | 6.6 GB    | 62,271    | NO — animation data |
| ObjectContainers/    | 4.2 GB    | 9,454     | NO — level geometry |
| **Libs/**            | **2.4 GB**| **63,491**| **YES** — Foundry records |
| Game2.xml            | 2.3 GB    | 1         | MAYBE — legacy DCB XML |
| Prefabs/             | 1.2 GB    | 509       | NO — prefab data |
| Materials/           | 370 MB    | 10,571    | NO — material defs |
| Game2.dcb            | 285 MB    | 1         | MAYBE — binary DataCore |
| **Localization/**    | **79 MB** | **36**    | **YES** — global.ini |
| **Scripts/**         | **27 MB** | **4,032** | **PARTIAL** — Loadouts + ShopInventories |
| Levels/              | 0.1 MB    | 2         | NO |

**Result: ~2.5 GB needed out of ~223 GB — 99% reduction**

---

## Minimal extraction set

### Required (current pipeline)

```
Data/Libs/Foundry/**          2.3 GB, 63,491 files
Data/Localization/**          79 MB,  36 files
```

`Libs/Foundry/` contains all entity XML records, manufacturers, damage macros,
inventory containers, etc. The pipeline currently rglobs the entire directory.

Note: `Libs/Foundry/records/ui/` (556 MB) and `records/actor/` (215 MB) are inside
Foundry but not currently queried. Could be pruned further if needed, but safest
to include for UUID index completeness (ships_preview.py rglobs all of records/).

### Optional (future pipeline stages)

```
Data/Scripts/Loadouts/        13 MB   — default ship loadout XMLs (what components ships spawn with)
Data/Scripts/ShopInventories/ 1.6 MB  — buy/sell inventories per location
Data/Game2.dcb                285 MB  — DataCore binary (advanced: NPC/mission/economy data)
```

`Game2.dcb` is the Star Citizen DataCore Book — a separate database that stores
mission data, NPCs, economy tables, etc. Not currently used but potentially
very useful. The `.dcb` format requires scdatatools' DCB reader to parse.

---

## How to implement selective extraction

### Option A: unp4k path patterns (test first)

unp4k's arg parsing may support extra args as glob patterns. Worth testing:

```bash
# Test: extract only one directory
unp4k.exe Data.p4k "Data/Libs/Foundry/*"
```

If unp4k supports this, update `extractor.py` to pass the required patterns.
**Status: UNTESTED — do before next re-extract**

### Option B: scdatatools selective extract (fallback)

Use `sc.p4k._extract_member()` but only for files matching our patterns:

```python
KEEP_PREFIXES = (
    "Data/Libs/Foundry/",
    "Data/Localization/",
    "Data/Scripts/Loadouts/",
    "Data/Scripts/ShopInventories/",
)
files = [f for f in sc.p4k.filelist if f.filename.startswith(KEEP_PREFIXES)]
# ~67K files instead of 1.28M
```

~67K files at ~97/sec = ~11 minutes vs 3.5 hours.

---

## Records subdirs and their pipeline usage

| records/ subdir        | Size   | Used by             | Notes |
|------------------------|--------|---------------------|-------|
| entities/spaceships/   | 216 MB | ships_preview.py    | Ship entity XMLs |
| entities/scitem/       | 1.1 GB | components, armor   | All equippable items |
| entities/groundvehicles| 3.6 MB | (future)            | Vehicles |
| scitemmanufacturer/    | 4.5 MB | ships_preview.py    | Manufacturer names |
| damage/                | <1 MB  | armor_preview.py    | Damage resistance macros |
| inventorycontainers/   | 2.0 MB | armor_preview.py    | Backpack container sizes |
| ui/                    | 556 MB | (UUID index only)   | Could skip if we limit UUID scan |
| actor/                 | 215 MB | (UUID index only)   | Could skip if we limit UUID scan |
| missionbroker/         | 71 MB  | unused              | Mission data |
| contracts/             | 60 MB  | unused              | Contract definitions |

---

## Action plan for next re-extract (new SC version)

1. **Test unp4k pattern args** — run a quick test extraction with path patterns
2. If unp4k supports it: update `extractor.py` to pass the 2-3 required patterns
3. If not: write `selective_extractor.py` using scdatatools with prefix filtering
4. Estimated extract time with selective: ~11 min (67K files) vs 3.5 hr (1.28M files)
5. Disk space: ~2.5 GB vs ~223 GB

---

## Future pipeline stages (for reference)

These are data sources that would expand what we can show:

| Stage | Data source | What it unlocks |
|-------|-------------|-----------------|
| Weapons | entities/scitem/weapons/ | FPS guns, ship weapons |
| Vehicles | entities/groundvehicles/ | Buggies, Cyclone, etc. |
| Shop data | Scripts/ShopInventories/ | Where to buy items |
| Loadouts | Scripts/Loadouts/ | What components ships come with by default |
| Commodities | entities/commodities/ | Trade goods, prices |
| DataCore | Game2.dcb | NPC data, missions, economy |
