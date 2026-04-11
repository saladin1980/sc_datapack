# SC DataPack — Asset Extracts

CryEngine model files extracted from Star Citizen for use in Blender, videos, and renders.

---

## Folder structure

```
extractions/    full armor set dumps — complete meshes, materials, textures for an entire armor set
extras/         specific pieces pulled on request — targeted extracts for individual items
```

### `extractions/`

Full set exports. Everything you need for a complete character or armor in one place.

| What | Path inside extractions/ |
|---|---|
| **Male base body** (mesh + all skin tones) | `Data/Objects/Characters/Human/male_v7/body/` |
| **Female base body** (mesh + all skin tones) | `Data/Objects/Characters/Human/female_v2/body/` |
| **Player heads — male** (archetypes v001–v015) | `Data/Objects/Characters/Human/heads/male/pu/archetypes/` |
| **Player heads — female** (archetypes v001–v014) | `Data/Objects/Characters/Human/heads/female/pu/archetypes/` |
| Defiance Hailstorm armor (female) | `Data/Objects/Characters/Human/female_v2/armor/cds/` |
| Defiance Hailstorm armor (male base mesh) | `Data/Objects/Characters/Human/male_v7/armor/cds/` |

### `extras/`

Specific pieces requested individually.

| What | Path inside extras/ |
|---|---|
| Slaver heavy legs mesh (CDS base) | `Data/Objects/Characters/Human/male_v7/armor/cds/` |
| Slaver heavy legs materials + textures | `Data/Objects/Characters/Human/male_v7/armor/slaver/` |
| VGL Specialist Sangar helmet (9tails, male) | `Data/Objects/Characters/Human/male_v7/armor/vgl/` |
| VGL Specialist Sangar helmet (female) | `Data/Objects/Characters/Human/female_v2/armor/vgl/` |

---

## Getting it into Blender

### Step 1 — Install Noesis (free)

Download: https://richwhitehouse.com/index.php?postid=45

Noesis reads CryEngine `.skin` and `.cgf` files and converts them to FBX.
No extra plugin needed — CryEngine support is built in.

---

### Step 2 — Convert mesh to FBX

1. Open Noesis
2. Navigate to the `.skin` file you want (see **Which files to use** below)
3. Right-click → **Export** → format **FBX** → Export

---

### Step 3 — Import into Blender

**File → Import → FBX** → select the exported FBX.
Mesh comes in without textures — apply them in Step 4.

---

### Step 4 — Apply textures

Textures live in the `textures/` folder alongside each mesh.
Use only the **base `.dds`** file — ignore `.dds.1` through `.dds.7` (game streaming mip levels, Blender doesn't need them).

| Texture suffix | Type | Blender node input |
|---|---|---|
| `_ddna.dds` | Diffuse + normal packed | Base Color |
| `_ddn.dds` | Normal map | Normal Map node |
| `_blend.dds` | Albedo / blend | Base Color |
| `_wear.dds` | Wear / damage layer | Mix over base color |
| `_hal.dds` | Holographic / emission | Emission |

In Shader Editor: **Image Texture** node → plug into **Principled BSDF**.

---

## Which files to use

### Base body mesh — `extractions/`

The body mesh is what armor and clothing attach to. Import it first, then import armor pieces on top — they share the same rig so they auto-align.

**Male:**
```
extractions/Data/Objects/Characters/Human/male_v7/body/
  m_body.skin        ← import this in Noesis -> FBX -> Blender (standard build)
  m_body.skinm       ← keep next to it (material sidecar)
  m_body.cdf         ← reference only (links mesh + skeleton)
  m_body_thin.skin   ← slim body type variant
  m_body_fat.skin    ← heavy body type variant
  m_body.mtl         ← base material (points to textures)
  m_body_01.mtl – m_body_15.mtl  ← numbered skin tone variants
  m_body_cau.mtl, m_body_blk.mtl, m_body_brwn.mtl, ...  ← named skin tone variants
  textures/
    m_body_ddna.dds         ← normal map (use Normal Map node in Blender)
    m_body_diff.dds         ← default skin diffuse
    m_body_01_diff.dds – m_body_15_diff.dds  ← numbered skin tone diffuse maps
    m_body_fat_diff.dds, m_body_fat_ddna.dds ← heavy body type textures
```

**Female:**
```
extractions/Data/Objects/Characters/Human/female_v2/body/
  f_body.skin        ← import this in Noesis
  f_body.skinm
  f_body.cdf
  textures/
    f_body_ddna.dds
    f_body_diff.dds
    f_body_01_diff.dds – f_body_14_diff.dds  ← skin tone variants
```

---

### Player heads (character creator) — `extractions/`

These are the actual heads players choose in the character creator. 15 male, 14 female, each with their own textures.

```
extractions/Data/Objects/Characters/Human/heads/male/pu/archetypes/
  male_archetype_v001/
    male_archetype_v001_t1_head.skin    ← import in Noesis
    male_archetype_v001_t1_head.skinm
    textures/                           ← head-specific skin + normal maps
  male_archetype_v002/ ... male_archetype_v015/

extractions/Data/Objects/Characters/Human/heads/female/pu/archetypes/
  female_archetype_v001/ ... female_archetype_v014/
```

**Note on heads:** In SC the head attaches at the neck — it's a separate mesh from the body. Import both `m_body.skin` and the head `.skin` into the same Blender scene and they should align automatically (same rig origin).

---

### Defiance Hailstorm — `extractions/`

Use the **base LOD0** file for each piece (no `_lod` suffix — those are lower-quality distance variants):

```
extractions/Data/Objects/Characters/Human/female_v2/armor/cds/
  f_cds_heavy_armor_01_legs.skin       ← import this in Noesis
  f_cds_heavy_armor_01_legs.skinm      ← keep next to the .skin (Noesis needs it)
  textures/                            ← apply base .dds files in Blender
```

Repeat for helmet, torso, arms using the same naming pattern.

---

### Slaver heavy legs — `extras/`

The slaver legs reuse the CDS base mesh with slaver-specific textures.
You need files from **two folders**:

**1 — Mesh (CDS base):**
```
extras/Data/Objects/Characters/Human/male_v7/armor/cds/
  m_cds_heavy_armor_01_legs.skin       ← import this in Noesis
  m_cds_heavy_armor_01_legs.skinm      ← keep next to it
```

**2 — Material + textures (slaver skin):**
```
extras/Data/Objects/Characters/Human/male_v7/armor/slaver/
  m_slaver_heavy_armor_legs_01_01_01.mtl                      ← open in text editor to see texture list
  mtl_var/m_slaver_heavy_armor_legs_01_01_01/
    m_slaver_heavy_armor_legs_01_01_13.mtl                    ← Hailstorm color variant
  textures/                                                   ← apply base .dds files in Blender
```

---

### VGL Specialist Sangar helmet (9tails) — `extras/`

```
extras/Data/Objects/Characters/Human/male_v7/armor/vgl/
  m_vgl_specialist_heavy_helmet_01_prop.skin     ← import this in Noesis (rigged version)
  m_vgl_specialist_heavy_helmet_01_prop.skinm    ← keep next to it
  mtl_var/m_vgl_specialist_heavy_helmet_01_01_01/
    m_vgl_specialist_heavy_helmet_01_01_tint.mtl ← 9tails color variant
  textures/                                      ← apply base .dds files in Blender
```

Female version: same process using `female_v2/armor/vgl/f_vgl_specialist_heavy_helmet_01.skin`

---

## File type reference

| Extension | What it is | Use it? |
|---|---|---|
| `.skin` | Rigged character mesh — Noesis input | Yes — main mesh file |
| `.cgf` | Static prop mesh — Noesis input | Yes — use for non-rigged version |
| `.skinm` / `.cgfm` | Material sidecar — must sit next to the mesh | Yes — keep alongside |
| `.cdf` | Character definition — links mesh + skeleton + material | Reference only |
| `.chr` | Skeleton / rig | Optional for static renders |
| `.mtl` | Material XML — lists which textures to apply | Reference only |
| `.dds` | Texture — use this in Blender | Yes |
| `.dds.1` – `.dds.7` | Streaming mip levels — game engine only | No — ignore |

---

## Download just one folder (sparse checkout)

```bash
git clone --branch Tech-zip --single-branch --depth 1 --filter=blob:none --sparse \
  https://github.com/saladin1980/sc_datapack.git
cd sc_datapack

# Male base body
git sparse-checkout set "extractions/Data/Objects/Characters/Human/male_v7/body"

# Female base body
git sparse-checkout set "extractions/Data/Objects/Characters/Human/female_v2/body"

# All player heads (male + female archetypes)
git sparse-checkout set "extractions/Data/Objects/Characters/Human/heads"

# Single head (e.g. male archetype 3)
git sparse-checkout set "extractions/Data/Objects/Characters/Human/heads/male/pu/archetypes/male_archetype_v003"

# Hailstorm female armor
git sparse-checkout set "extractions/Data/Objects/Characters/Human/female_v2/armor/cds"

# Slaver legs (needs both)
git sparse-checkout set "extras/Data/Objects/Characters/Human/male_v7/armor/cds" \
                        "extras/Data/Objects/Characters/Human/male_v7/armor/slaver"

# VGL Sangar helmet
git sparse-checkout set "extras/Data/Objects/Characters/Human/male_v7/armor/vgl"
```
