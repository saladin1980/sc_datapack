# Field Mapping — DataCore XML → JSON Output

This document maps every DataCore XML attribute the pipeline reads to the JSON field
it produces. Use this to understand exactly where each output value comes from in the
raw game data, or to diagnose unexpected values.

---

## Shared infrastructure (all scripts)

### Localization index (`build_localization_index`)
Built once per script from `Data/Localization/english/global.ini`.
All display names are stored as loc keys in XML (e.g. `@vehicle_Name_AEGS_Gladius`).
The index strips the leading `@` and lowercases the key for lookup.

```
XML attribute value : "@vehicle_Name_AEGS_Gladius"
          ↓ strip @, lowercase
global.ini key      : "vehicle_name_aegs_gladius"
          ↓ lookup
Display name        : "AEGS Gladius"
```

### UUID index (`build_uuid_index`)
Built once per script from all `~24,360 XML` files in `Data_Extraction/`.
Maps `__id` attribute value → file path.
Used to resolve any UUID reference to its source XML.

```
XML attribute value : "a8b3c9d2-..."  (UUID)
          ↓ uuid_idx lookup
File path           : "Data_Extraction/Data/Libs/foundry/records/entities/scitem/ships/..."
          ↓ parse XML
Source record data  : type, size, grade, display name, stats, etc.
```

### Manufacturer index (`build_mfr_index`)
Built from `Data/Libs/foundry/records/scitemmanufacturer/*.xml`.
Maps manufacturer UUID → `Code` field (e.g. `"AEG"`, `"MIS"`).
Then `MFR_NAMES` dict maps code → display name (e.g. `"Aegis"`, `"MISC"`).

> **Note:** DataCore `Code` field is truncated (`AEGS→AEG`, `BEHR→BEH`, `MISC→MIS`).
> Ships correct this via class_name prefix. Components use `_COMP_MFR_CODE_NORM` dict.

---

## ships.py → ships.json

Records source: `Data_Extraction/Data/Libs/foundry/records/entities/spaceships/*.xml`

| XML element / attribute | Notes | JSON field |
|---|---|---|
| Root `__id` | DataCore class name (e.g. `AEGS_Gladius`) | `class_name` |
| Root `__id` prefix (`AEGS_`, `ANVL_`, ...) | Split on `_`, lookup in `_CLASS_TO_MFR_CODE` | `manufacturer_code` |
| `VehicleComponentParams.vehicleName` | Loc key → global.ini | `name` |
| `name` stripped of mfr prefix | e.g. `"AEGS Gladius"` → `"Gladius"` | `canonical_name` |
| Always `null` | Populated later via UEX API | `uex_id` |
| `VehicleComponentParams.manufacturer` (UUID) | UUID → mfr_idx → MFR_NAMES | `manufacturer` |
| `VehicleComponentParams.vehicleCareer` | Loc key → cleaned by `_clean_career()` | `career` |
| `VehicleComponentParams.vehicleRole` | Loc key → cleaned by `_clean_career()` | `role` |
| `VehicleComponentParams.crewSize` | Integer | `crew` |
| `VehicleComponentParams.vehicleHullDamageNormalizationValue` | Float | `hull_hp` |
| Cargo component `SCItemCargoGridParams.totalCapacityInSCU` | Via hardpoint/systems traversal | `cargo_scu` |
| `shipInsuranceParams.baseWaitTimeMinutes` | Float, rounded 2dp | `ins_wait_min` |
| `shipInsuranceParams.baseExpeditingFee` | Integer aUEC | `ins_fee_auec` |
| `VehicleComponentParams.maxBoundingBoxSize.x` | Float metres | `width_m` |
| `VehicleComponentParams.maxBoundingBoxSize.y` | Float metres | `length_m` |
| `VehicleComponentParams.maxBoundingBoxSize.z` | Float metres | `height_m` |
| `SEntityComponentDefaultLoadout` → `SItemPortLoadoutEntryParams` | Recursively resolved via UUID chain | `hardpoints[]` |
| `SEntityComponentDefaultLoadout` → system ports | Same as hardpoints, different port categories | `systems[]` |

**Hardpoint / system port record:**
```
SItemPortLoadoutEntryParams.itemPortName  → port
SItemPortLoadoutEntryParams.entityClassName → class
  ↓ class name → cls_idx → XML
    AttachDef.Type/SubType  → category, type
    AttachDef.Size          → size
    AttachDef.Grade         → grade
    Localization.Name       → display_name
```

**Skip patterns** (non-flyable world objects removed before parsing):
`_derelict`, `_wreck`, `_template`, `_pu_gamemaster`, `_pu_invictus`, `_drug_`, `_pu_pirate_`

---

## components.py → components.json

Records source: `Data_Extraction/Data/Libs/foundry/records/entities/scitem/ships/` +
               `Data_Extraction/Data/Libs/foundry/records/entities/scitem/` (weapons, etc.)

| XML element / attribute | Notes | JSON field |
|---|---|---|
| Root element tag name | DataCore class name | `class` |
| `AttachDef.Type` | e.g. `Shield`, `QuantumDrive`, `PowerPlant` | `type` |
| `AttachDef.SubType` | Sub-category within type | `sub_type` |
| `AttachDef.Size` | Integer 1–9 | `size` |
| `AttachDef.Grade` | Letter A–F or empty | `grade` |
| `AttachDef.Manufacturer` (UUID) | UUID → mfr_idx → MFR_NAMES; stored raw for norm | `manufacturer` |
| `AttachDef.Manufacturer` (UUID) | Normalized via `_COMP_MFR_CODE_NORM` | `manufacturer_code` |
| `AttachDef.Localization.Name` | Loc key → global.ini | `name` |
| `parse_component_stats()` | Reads type-specific child elements; returns `[(label, value)]` | `stats[]` |

**Stats parsing** — `parse_component_stats()` reads type-specific XML elements per component type.
Output is human-readable label/value pairs, e.g. `{"label": "EM Resistance", "value": "87%"}`.

---

## armor.py → armor.json

Records source: `Data_Extraction/Data/Libs/foundry/records/entities/scitem/characters/human/armor/` +
               `Data_Extraction/Data/Libs/foundry/records/entities/scitem/characters/human/starwear/helmet/`

| XML element / attribute | Notes | JSON field |
|---|---|---|
| File stem | Source XML filename without extension | `file` |
| `AttachDef.Localization.Name` | Loc key → global.ini; falls back to `file` | `name` |
| `AttachDef.Type` | Mapped via `SLOT_FROM_TYPE` dict | `slot` |
| `AttachDef.SubType` | e.g. `"Tier1"`, `"Tier2"`, `"Tier3"` | `tier` |
| `AttachDef.Manufacturer` (UUID) | UUID → mfr_idx → display name | `manufacturer` |
| `AttachDef.microSCU` (child element) | Integer micro-SCU capacity | `micro_scu` |
| `SCItemSuitArmorParams.damageResistance` (UUID) | UUID → uuid_idx → damage/\*.xml | `damage_resistance{}` |
| `DamageResistance.Multiplier` per damage type | `(1 - Multiplier) * 100` = resistance % | `damage_resistance.Physical/Energy/Distortion/Thermal/Biochemical/Stun` |
| `DamageResistance.impactForceResistance` | `(1 - value) * 100` = Force resistance % | `damage_resistance.Force` |
| `SCItemSuitArmorParams > ItemSuitArmorSignatureParams.signatureType` | e.g. `"CS"`, `"IR"`, `"EM"` | `signatures[].type` |
| `ItemSuitArmorSignatureParams.signatureEmission` | Float | `signatures[].emission` |
| `ItemSuitArmorSignatureParams.signatureReductionWeighted` | Float | `signatures[].reduce_weighted` |
| `ItemSuitArmorSignatureParams.signatureReductionAbsolute` | Float | `signatures[].reduce_absolute` |
| `SCItemClothingParams.TemperatureResistance.MinResistance` | Float °C or `null` | `temp_min_c` |
| `SCItemClothingParams.TemperatureResistance.MaxResistance` | Float °C or `null` | `temp_max_c` |
| `SCItemClothingParams.RadiationResistance.MaximumRadiationCapacity` | Float or `null` | `rad_capacity` |
| `SCItemClothingParams.RadiationResistance.RadiationDissipationRate` | Float or `null` | `rad_diss_rate` |
| `SCItemInventoryContainerComponentParams.containerParams` (UUID) | UUID → uuid_idx → container XML | `container_scu` |

**Slot mapping** (`SLOT_FROM_TYPE` dict):
```
"Char_Armor_Torso"      → "Torso"
"Char_Armor_Arms"       → "Arms"
"Char_Armor_Legs"       → "Legs"
"Char_Armor_Helmet"     → "Helmet"
"Char_Armor_Undersuit"  → "Undersuit"
"Char_Armor_Backpack"   → "Backpack"
 (anything else)        → "Other"  ← filtered out before JSON export
```

---

## weapons.py → weapons.json

Records sources:
- Ship weapons: `Data_Extraction/Data/Libs/foundry/records/entities/scitem/weapons/ship/`
- FPS weapons:  `Data_Extraction/Data/Libs/foundry/records/entities/scitem/weapons/fps/`
- Attachments:  `Data_Extraction/Data/Libs/foundry/records/entities/scitem/weapons/fps_modifiers/`
- Ammo params:  `Data_Extraction/Data/Libs/foundry/records/ammoparams/`

**Shared fields (all three categories):**

| XML element / attribute | Notes | JSON field |
|---|---|---|
| File stem | DataCore class name | `class_name` |
| `AttachDef.Localization.Name` | Loc key → global.ini | `name` |
| `AttachDef.Manufacturer` (UUID) | UUID → mfr_idx → display name | `manufacturer` |
| `AttachDef.Size` | Integer | `size` |
| `AttachDef.SubType` | e.g. `"Gun"`, `"Missile"`, `"Rocket"` | `subtype` |
| `AttachDef.Tags` | Space-separated tag string | `tags` (attachments only) |
| `SCItemPurchasableParams.microSCU` | Inventory size | `inventory_scu` |

**Ship weapons (`AttachDef.Type == "WeaponGun"`) and FPS weapons (`"WeaponPersonal"`) — additional fields:**

| XML element / attribute | Notes | JSON field |
|---|---|---|
| `SCWeaponActionFireSingleParams.fireRate` | Rounds per minute | `fire_rate_rpm` |
| `SAmmoContainerComponentParams.ammoParamsRecord` (UUID) | UUID → ammoparams/*.xml | (ammo chain) |
| `ammoparams.speed` | m/s, rounded 1dp | `ammo_speed_ms` |
| `ammoparams.lifetime` | seconds, rounded 3dp | `ammo_lifetime_s` |
| `ammoparams > damage.DamagePhysical` | Float, rounded 2dp | `dmg_physical` |
| `ammoparams > damage.DamageEnergy` | Float, rounded 2dp | `dmg_energy` |
| `ammoparams > damage.DamageDistortion` | Float, rounded 2dp | `dmg_distortion` |
| `ammoparams > damage.DamageThermal` | Float, rounded 2dp | `dmg_thermal` |
| `ammoparams > damage.DamageBiochemical` | Float, rounded 2dp | `dmg_biochemical` |
| Sum of all dmg_* fields | Rounded 2dp | `total_damage` |
| `weaponAIData.idealCombatRange` | Metres, rounded 1dp | `ideal_range_m` |
| `weaponAIData.maxFiringRange` | Metres, rounded 1dp | `max_range_m` |
| `SAmmoContainerComponentParams.maxAmmoCount` | Via magazine XML chain (FPS only) | `mag_capacity` |
| `SItemPortDef` child elements | Port tag values enumerate accepted attachment types | `attachment_slots[]` |

**FPS display type** — resolved via `SCItemPurchasableParams.displayName` loc key
(e.g. `"@ui_AMRS_WeaponClass_Rifle"` → `"Rifle"`).

**Ammo chain for FPS weapons:**
```
weapon XML
  SCItemWeaponComponentParams.ammoContainerRecord (UUID)
          ↓
  magazine XML
    SAmmoContainerComponentParams.maxAmmoCount     → mag_capacity
    SAmmoContainerComponentParams.ammoParamsRecord (UUID)
          ↓
  ammoparams XML
    speed, lifetime, damage.*                      → ammo_* fields
```

---

## groundvehicles.py → ground_vehicles.json

Records source: `Data_Extraction/Data/Libs/foundry/records/entities/groundvehicles/*.xml`
Filtered: NPC/AI variants removed (same `_SKIP_PATTERNS` logic as ships.py).

| XML element / attribute | Notes | JSON field |
|---|---|---|
| File stem | DataCore class name | `file` |
| `VehicleComponentParams.vehicleName` | Loc key → global.ini | `name` |
| `VehicleComponentParams.vehicleCareer` | Loc key → display string | `career` |
| `VehicleComponentParams.vehicleRole` | Loc key → display string | `role` |
| `VehicleComponentParams.crewSize` | Integer | `crew` |
| `VehicleComponentParams.vehicleHullDamageNormalizationValue` | Integer | `hull_hp` |
| `VehicleComponentParams.movementClass` | Mapped via `MOVEMENT_LABELS` dict | `drive` |
| `VehicleComponentParams.manufacturer` (UUID) | UUID → mfr_idx → code + name | `manufacturer` / `manufacturer_code` |
| `VehicleComponentParams.maxBoundingBoxSize.x` | Float metres | `width_m` |
| `VehicleComponentParams.maxBoundingBoxSize.y` | Float metres | `length_m` |
| `VehicleComponentParams.maxBoundingBoxSize.z` | Float metres | `height_m` |
| `shipInsuranceParams.baseWaitTimeMinutes` | Float, rounded 2dp | `ins_wait_min` |
| `shipInsuranceParams.baseExpeditingFee` | Integer aUEC | `ins_fee_auec` |
| `SItemPortLoadoutEntryParams.itemPortName` contains weapon/gun/turret/rack | Count of weapon ports | `weapon_ports` |

---

## items.py → items.json

Records sources (multiple scitem subdirectories):
- `entities/scitem/consumables/` — medical items, stims, food, drink
- `entities/scitem/fps_devices/` — tools and gadgets
- `entities/scitem/weapons/melee/` — melee weapons
- `entities/scitem/weapons/throwable/` — grenades, throwables
- `entities/scitem/carryables/1h/` and `carryables/2h/` — misc carryables (type-filtered)

| XML element / attribute | Notes | JSON field |
|---|---|---|
| File stem | DataCore class name | `file` |
| `AttachDef.Localization.Name` | Loc key → global.ini | `name` |
| `AttachDef.Type` | Raw DataCore type | `type` |
| `AttachDef.SubType` | Raw DataCore sub-type | `subtype` |
| `AttachDef.Size` | Integer | `size` |
| `AttachDef.Grade` | Letter | `grade` |
| `AttachDef.Tags` | Space-separated tags | `tags` |
| `AttachDef.Manufacturer` (UUID) | UUID → mfr_idx → code + name | `manufacturer` / `manufacturer_code` |
| `AttachDef.microSCU` | Integer | `micro_scu` |
| `_display_category(type, subtype)` | Logic function mapping raw types to display categories | `category` |

**Category mapping logic** (`_display_category`):
```
SubType "Medical" or "Stim"                → "Medical / Stim"
SubType "Hacking"                           → "Hacking Tool"
Type "FPS_Consumable" + "Food"/"Drink"     → "Food & Drink"
Type "Melee"                               → "Melee"
Type "Grenade" / "Throwable"               → "Throwable"
SubType "Tool" / "Gadget"                  → "Tool / Gadget"
Type "RemovableChip"                       → "RemovableChip"
(fallthrough)                              → "Misc"
```

---

## shops.py → shops.json

Source: `Data_Extraction/Data/Scripts/ShopInventories/Inv_*.json` (119 files)
Cross-referenced via: `build_uuid_index()` from ships.py

Shop JSON files contain a `ShopID` field (`"uuid,uuid,..."`) that encodes both the shop
terminal name and its location. The pipeline splits on `,`, strips outer quotes, and
resolves each segment via localization to produce `shop` and `location` display names.

Item UUIDs inside `Collection.Inventory[].ID.ID[]` are resolved against the UUID index
to find the DataCore XML for each item. The XML path stem becomes `class_name` and the
localization name becomes `name`. The item's XML directory path determines `category`.

| Source field | Notes | JSON field |
|---|---|---|
| Filename stem | e.g. `Inv_GrimHex_Shop_Deakins` | `shop_file` |
| `ShopID` first UUID segment | Loc key → global.ini → shop terminal name | `shop` |
| `ShopID` second UUID segment | Loc key → global.ini → station / location name | `location` |
| `Collection.Inventory[].ID.ID[]` | UUID → uuid_idx → XML file path | (item lookup) |
| XML file path stem | DataCore class name (e.g. `amrs_lasercannon_s1`) | `class_name` |
| XML `AttachDef.Localization.Name` | Loc key → global.ini → display name | `name` |
| XML directory path | e.g. `weapons/ship/` → `"Ship Weapon"` | `category` |
| `Collection.Inventory[].BuyPrice` | Float → int (0 = not purchasable) | `buy_auec` |
| `Collection.Inventory[].SellPrice` | Float → int (0 = not sellable) | `sell_auec` |

**Unresolved UUIDs:** 323 items across the 119 files could not be resolved via the UUID index
(commodity/resource terminal items not present in the DataCore extraction). These are dropped.

**Output:** flat join table — one row per shop × item. 5,994 rows total.

---

## shop_lookup.py — cross-report shop injection

`shop_lookup.py` is a standalone shared module (no pipeline imports — avoids circular dependencies).
It reads `shops.json` at report-generation time and is imported by all five report scripts.

| Function / constant | Purpose |
|---|---|
| `load_shop_lookup()` | Reads shops.json → `{class_name.lower(): [row_dicts]}`. Returns `{}` silently if shops.json not yet built. |
| `shop_html(entries)` | Renders deduplicated "Available at (N)" HTML block with "show X more" toggle at 5 entries. |
| `SHOP_CSS` | CSS string injected into each report's `<style>` block (`.shop-avail`, `.sh-row`, etc.) |

Lookup key normalization: all class names are `.lower()`-ed before dict insertion so that
`AEGS_Gladius` from DataCore matches `aegs_gladius` from the shops.json `class_name` field.

---

## Common data quality notes

| Issue | Affected fields | Fix applied |
|---|---|---|
| 32-bit float noise (e.g. `97.19999694824219`) | `dmg_*`, `total_damage`, `ammo_lifetime_s`, `ins_wait_min` | `round(v, 2)` via `_rnd()` |
| DataCore `Code` truncated (`AEGS→AEG`) | `manufacturer_code` in components | `_COMP_MFR_CODE_NORM` dict |
| `MISC` and `Mirai` both map to `MIS` | Ships `manufacturer_code` | Derived from class_name prefix instead |
| Raw loc keys in career/role (e.g. `@item_ShipFocus_LuxuryTouring`) | `career`, `role` | `_clean_career()` with compound word dict |
| Joined compound words (e.g. `Heavygunship`) | `career`, `role` | `_CAREER_COMPOUND_FIXES` dict |
| Non-flyable world objects in spaceships/ | ships count | `_SKIP_PATTERNS` list in ships.py |
| DataCore XML invalid attributes / empty elements | All parsed XML | Three sanitisation regexes in extractor.py |
