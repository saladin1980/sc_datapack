# Data Sources

How the pipeline reads from `Data.p4k` (153.8 GB, 1,287,040 files).

---

## Extraction approach

The pipeline does NOT perform a bulk file extraction from Data.p4k.
Instead it uses two targeted methods:

**1. DataCore binary (primary — ~24,700 records)**
`scdatatools` opens `Data.p4k` and reads `Data/Game2.dcb` (285 MB, DataCore binary) in-memory.
Records are filtered by prefix, converted to XML, sanitised, and written to `Data_Extraction/`.
This avoids touching the 150+ GB of meshes, textures, audio, and other assets entirely.

**2. Localization files (direct extract — 12 files)**
`Data/Localization/*/global.ini` files are extracted directly from the archive.
These contain all display name strings keyed by UUID.

---

## DataCore record prefixes extracted (`extractor.py`)

```
libs/foundry/records/entities/spaceships/           ← ship entity XMLs
libs/foundry/records/entities/scitem/               ← all equippable items (components, armor, weapons, etc.)
libs/foundry/records/entities/groundvehicles/       ← ground vehicle entity XMLs
libs/foundry/records/scitemmanufacturer/            ← manufacturer name + code records
libs/foundry/records/damage/                        ← damage resistance macros (for armor)
libs/foundry/records/ammoparams/                    ← weapon ammo parameters
libs/foundry/records/commodityconfiguration/        ← commodity config
libs/foundry/records/commoditytypedatabase/         ← commodity type definitions
libs/foundry/records/resourcetypedatabase/          ← resource type definitions
```

Total extracted: ~24,700 XML records, ~400 MB on disk.

---

## Which scripts read which records

```
Data_Extraction/Data/Libs/foundry/records/
├── entities/
│   ├── spaceships/                     ← ships.py (257 flyable ships)
│   ├── groundvehicles/                 ← groundvehicles.py (27 vehicles)
│   └── scitem/
│       ├── ships/                      ← components.py (ship-mounted components)
│       ├── characters/human/armor/
│       │   ├── pu_armor/               ← armor.py (torso, arms, legs, undersuit, backpack)
│       │   └── starwear/helmet/        ← armor.py (helmets)
│       ├── weapons/
│       │   ├── ship/                   ← weapons.py (166 ship weapons)
│       │   └── fps/                    ← weapons.py (333 FPS weapons)
│       ├── fps_devices/                ← items.py
│       ├── consumables/                ← items.py (medical, food, stims)
│       ├── carryables/                 ← items.py (tools, gadgets)
│       └── (all other scitem/)         ← UUID index (uuid → file path resolution)
├── scitemmanufacturer/                 ← all scripts (manufacturer name lookup)
├── damage/                             ← armor.py (damage resistance macros)
├── ammoparams/                         ← weapons.py (ammo stats: damage, speed, lifetime)
└── inventorycontainers/                ← armor.py (backpack container sizes)

Data_Extraction/Data/Localization/*/
└── global.ini                          ← all scripts (display name string lookup)
```

---

## Not currently used

Data that could expand future pipeline stages:

```
Data/Scripts/Loadouts/           13 MB   — default ship component loadouts (what ships spawn with)
Data/Scripts/ShopInventories/    1.6 MB  — buy/sell locations per item
libs/foundry/records/ui/         556 MB  — UI config XMLs (swept for UUID index only, not queried)
libs/foundry/records/actor/      215 MB  — actor records (swept for UUID index only, not queried)
libs/foundry/records/missionbroker/       — mission definitions
libs/foundry/records/contracts/           — contract definitions
```

---

## Skipped entirely

```
Data/Objects/                    156.8 GB — 3D meshes
Data/Textures/                    29.7 GB — textures
Data/UI/                          10.2 GB — UI image assets
Data/Sounds/                       9.7 GB — audio
Data/Animations/                   6.6 GB — animations
Data/ObjectContainers/             4.2 GB — level geometry
Data/Prefabs/                      1.2 GB — prefab data
Data/Materials/                    0.4 GB — material definitions
Data/Game2.xml                     2.3 GB — legacy DataCore XML (superseded by Game2.dcb)
```

**Total archive: 153.8 GB | Actually read: ~365 MB (Game2.dcb + global.ini files)**
