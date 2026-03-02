# P4K Extraction — Architecture & Reference

## How the pipeline extracts data

The pipeline uses `scdatatools` to read `Data.p4k` — it does **not** do a bulk
file extraction (which would dump ~223 GB to disk and take hours).

### What actually happens

```
Data.p4k (153.8 GB, 1,287,040 files)
       │
       ├── Data/Game2.dcb (285 MB, DataCore binary)
       │         │
       │         └── scdatatools reads in-memory (~90s)
       │                   │
       │                   └── dc.records (108,864 total records)
       │                             │
       │                             └── filter by RECORD_PREFIXES
       │                                       │
       │                                       └── ~24,700 records
       │                                                 │
       │                                                 └── sanitise XML → write to disk
       │                                                           (~400 MB, Data_Extraction/)
       │
       ├── Data/Localization/*/global.ini (12 files, ~79 MB total)
       │         │
       │         └── extracted directly via sc.p4k._extract_member()
       │
       └── Data/Scripts/ShopInventories/*.json (119 files, ~2 MB)
                 │
                 └── extracted directly via sc.p4k._extract_member()
                           │
                           └── UUID cross-referenced with DataCore UUID index
                                     │
                                     └── 5,994 entries (class_name, shop, location, price)
```

This approach reads only ~367 MB from the 153.8 GB archive and avoids touching
the 3D meshes, textures, audio, and other assets entirely.

---

## P4K directory breakdown

Reference table showing what's in the archive and why we skip most of it:

| Directory            | Size      | Files     | Status |
|----------------------|-----------|-----------|--------|
| Objects/             | 156.8 GB  | 1,015,909 | SKIP — 3D meshes |
| Textures/            | 29.7 GB   | 82,663    | SKIP — texture files |
| UI/                  | 10.2 GB   | 15,229    | SKIP — UI image assets |
| Sounds/              | 9.7 GB    | 110,609   | SKIP — audio |
| Animations/          | 6.6 GB    | 62,271    | SKIP — animation data |
| ObjectContainers/    | 4.2 GB    | 9,454     | SKIP — level geometry |
| **Game2.xml**        | **2.3 GB**| **1**     | SKIP — legacy DataCore XML, superseded by Game2.dcb |
| Prefabs/             | 1.2 GB    | 509       | SKIP — prefab data |
| Materials/           | 370 MB    | 10,571    | SKIP — material defs |
| **Game2.dcb**        | **285 MB**| **1**     | **PRIMARY** — DataCore binary (our main data source) |
| **Localization/**    | **79 MB** | **36**    | **YES** — global.ini display name strings |
| **Scripts/**         | **27 MB** | **4,032** | **PARTIAL** — ShopInventories/ implemented; Loadouts/ future |
| Libs/                | 2.4 GB    | 63,491    | INDIRECT — records exist inside Game2.dcb, written here after extraction |
| Levels/              | 0.1 MB    | 2         | SKIP |

---

## DataCore version tracking

`extractor.py` reads `build_manifest.id` from the same directory as `Data.p4k`.
This file contains the game version (e.g. `4.6.0-live.11319298`).

On each run, the extracted version is written to `Data_Extraction/.version`.
If `.version` already matches the current game version, extraction is skipped entirely.
On a new game patch, runner.py detects the mismatch, clears stale HTML reports, and re-extracts.

---

## XML sanitisation

DataCore XML dumps require sanitisation before Python's `xml.etree` can parse them:

```python
_INVALID_ATTR = re.compile(r'\s+(?:[0-9][^\s=]*)?\s*=\s*"[^"]*"')  # attrs starting with digit
_EMPTY_ELEM   = re.compile(r"[ \t]*< +/>[ \t]*\n?")                  # bare < />
_EMPTY_TAG    = re.compile(r"[ \t]*<>[^<]*</>[ \t]*\n?")             # bare <>text</>
```

Result: 24,316 / 24,317 records parse cleanly after sanitisation.

---

## Implemented: ShopInventories

`Data/Scripts/ShopInventories/*.json` — 119 files, ~2 MB.

Shop files use the format:
```json
{
  "ShopID": "uuid,uuid,...",
  "Collection": {
    "Inventory": [
      { "ID": { "ID": ["item-uuid"] }, "BuyPrice": 4250.0, "SellPrice": 0.0 }
    ]
  }
}
```

Item UUIDs are cross-referenced with the DataCore UUID index (`build_uuid_index()` from `ships.py`)
to resolve each UUID to a class name and display name. Unresolved UUIDs (commodity/resource terminal
items not in DataCore extraction) are dropped — 323 entries across the 119 files.

Output: `shops.json` — flat join table, one row per shop × item:
```
{ shop_file, shop, location, class_name, name, category, buy_auec, sell_auec }
```

`shop_lookup.py` reads `shops.json` at report-generation time and injects "Available at (N)" sections
into every ship, armor, weapon, item, and component page.

---

## Future data sources

| Source | Extract method | Size | What it unlocks |
|--------|---------------|------|-----------------|
| `Data/Scripts/Loadouts/` | Direct p4k extract | 13 MB | Default ship component loadouts (what each ship spawns with) |
| DataCore records: `missionbroker/` | scdatatools DataCore | ~71 MB | Mission definitions |
| DataCore records: `contracts/` | scdatatools DataCore | ~60 MB | Contract definitions |
