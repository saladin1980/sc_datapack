# Data Sources

Paths used from the extracted `Data.p4k` archive.

## Currently used

```
Data/Libs/Foundry/records/
├── entities/
│   ├── spaceships/                     ← ship stats (ships page)
│   └── scitem/
│       ├── ships/                      ← ship-mounted components (components page)
│       ├── characters/human/armor/
│       │   ├── pu_armor/               ← Torso, Arms, Legs, Undersuit, Backpack
│       │   └── starwear/helmet/        ← Helmets
│       └── (all other scitem/)         ← UUID index (uuid → file resolution)
├── scitemmanufacturer/                 ← manufacturer names + logos
├── damage/                             ← damage resistance macros (armor stats)
└── inventorycontainers/                ← backpack container sizes

Data/Localization/english/
└── global.ini                          ← all display name strings
```

## Not currently used (but extracted)

These are in the output directory but the pipeline doesn't read them yet:

```
Data/Scripts/Loadouts/                  ← default ship component loadouts
Data/Scripts/ShopInventories/           ← buy/sell locations per item
Data/Game2.dcb                          ← DataCore binary (NPC/mission/economy data)
Data/Libs/Foundry/records/
├── ui/                                 ← UI config XMLs (in UUID index sweep only)
├── actor/                              ← actor records (in UUID index sweep only)
├── missionbroker/                      ← mission definitions
└── contracts/                          ← contract definitions
```

## Skipped entirely (not needed)

```
Data/Objects/                           156.8 GB — 3D meshes
Data/Textures/                           29.7 GB — textures
Data/UI/                                 10.2 GB — UI image assets
Data/Sounds/                              9.7 GB — audio
Data/Animations/                          6.6 GB — animations
Data/ObjectContainers/                    4.2 GB — level geometry
Data/Prefabs/                             1.2 GB — prefab data
Data/Materials/                           0.4 GB — material definitions
Data/Game2.xml                            2.3 GB — legacy DataCore XML
```

**Total extracted: ~223 GB | Actually used: ~2.5 GB**

> See `EXTRACTION_PLAN.md` in the repo root for the selective extraction plan
> to avoid pulling the full archive on future game version updates.
