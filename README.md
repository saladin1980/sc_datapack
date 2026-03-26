# SC DataPack — Asset Extracts

CryEngine model files extracted from Star Citizen for use in Blender, videos, and renders.

---

## Folder structure

```
extractions/    full armor set dumps — complete meshes, materials, textures for an entire armor set
extras/         specific pieces pulled on request — targeted extracts for individual items
```

### `extractions/`

Full set exports. Everything you need for a complete armor in one place.

| What | Path inside extractions/ |
|---|---|
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

# Hailstorm female armor
git sparse-checkout set "extractions/Data/Objects/Characters/Human/female_v2/armor/cds"

# Slaver legs (needs both)
git sparse-checkout set "extras/Data/Objects/Characters/Human/male_v7/armor/cds" \
                        "extras/Data/Objects/Characters/Human/male_v7/armor/slaver"

# VGL Sangar helmet
git sparse-checkout set "extras/Data/Objects/Characters/Human/male_v7/armor/vgl"
```
