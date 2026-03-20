# SC DataPack — Asset Extracts

CryEngine model files extracted from Star Citizen for use in Blender, videos, and renders.

---

## What's in here

| Folder | Contents |
|---|---|
| `hailstorm_export/` | Defiance Hailstorm armor — base CDS heavy armor (male + female) |
| `extras_export/` | Slaver heavy legs + VGL Specialist Sangar 9tails helmet (male + female) |

---

## Getting it into Blender

### Step 1 — Install Noesis (free)

Download from https://richwhitehouse.com/index.php?postid=45

Noesis reads CryEngine `.skin` and `.cgf` files and converts them to FBX for Blender.
No plugin needed — Noesis handles CryEngine natively.

---

### Step 2 — Convert the mesh to FBX

1. Open Noesis
2. Navigate to the mesh file you want (see **Which files to use** below)
3. Right-click → **Export**
4. Set format to **FBX** → Export
5. Note where the FBX was saved

---

### Step 3 — Import into Blender

1. Blender → **File → Import → FBX**
2. Import the FBX you exported from Noesis
3. The mesh will come in without textures — apply them manually (Step 4)

---

### Step 4 — Apply textures

Textures are in the `textures/` subfolder alongside each mesh.
Use the base `.dds` file for each texture type — ignore the `.dds.1` through `.dds.7` files
(those are mip levels the game engine uses for streaming, Blender doesn't need them).

| Texture suffix | Type | Blender node |
|---|---|---|
| `_ddna.dds` | Diffuse + normal packed | Base Color (or split channels) |
| `_ddn.dds` | Normal map | Normal Map node |
| `_blend.dds` | Blend/albedo | Base Color |
| `_wear.dds` | Wear/damage overlay | Mix with base color |
| `_hal.dds` | Holographic/emission | Emission |

In Blender's Shader Editor: add an **Image Texture** node for each map,
plug into the appropriate input on a **Principled BSDF**.

---

## Which files to use

### Defiance Hailstorm armor — `hailstorm_export/`

```
hailstorm_export/Data/Objects/Characters/Human/
  female_v2/armor/cds/    ← female mesh + textures
  male_v7/armor/cds/      ← (use extras_export male CDS for male version)
```

**For each piece, use the base LOD0 file** (no `_lod` suffix):
- `f_cds_heavy_armor_01_legs.skin` — female legs mesh
- `f_cds_heavy_armor_01_helmet.skin` — female helmet
- etc.

Ignore `_lod1` through `_lod5` — those are lower-quality distant LODs.

---

### Slaver heavy legs — `extras_export/`

The slaver legs use the **CDS heavy base mesh** with a slaver-specific material.
You need files from two places:

**Mesh (CDS base):**
```
extras_export/Data/Objects/Characters/Human/male_v7/armor/cds/
  m_cds_heavy_armor_01_legs.skin          ← import this into Noesis
  m_cds_heavy_armor_01_legs.skinm         ← keep next to the .skin (Noesis needs it)
```

**Material + textures (slaver skin):**
```
extras_export/Data/Objects/Characters/Human/male_v7/armor/slaver/
  m_slaver_heavy_armor_legs_01_01_01.mtl  ← material definition
  mtl_var/m_slaver_heavy_armor_legs_01_01_01/
    m_slaver_heavy_armor_legs_01_01_13.mtl   ← color variant (the Hailstorm skin)
  textures/                                  ← DDS textures, use the base .dds files
```

**Workflow:**
1. Open `m_cds_heavy_armor_01_legs.skin` in Noesis → export FBX
2. Import FBX into Blender
3. Open the `.mtl` file in a text editor to see which texture files it references
4. Apply those textures from the `slaver/textures/` folder

---

### VGL Specialist Sangar helmet (9tails variant) — `extras_export/`

```
extras_export/Data/Objects/Characters/Human/male_v7/armor/vgl/
  vgl_specialist_heavy_helmet_01_9tails_01.cdf     ← character definition (entry point)
  m_vgl_specialist_heavy_helmet_01_prop.skin       ← rigged mesh — import this
  m_vgl_specialist_heavy_helmet_01_prop.skinm      ← keep next to the .skin
  m_vgl_specialist_heavy_helmet_01_prop_skeleton.chr  ← skeleton (optional for static renders)
  mtl_var/m_vgl_specialist_heavy_helmet_01_01_01/
    m_vgl_specialist_heavy_helmet_01_01_tint.mtl   ← 9tails color variant material
  textures/                                        ← DDS textures
```

**Workflow:**
1. Open `m_vgl_specialist_heavy_helmet_01_prop.skin` in Noesis → export FBX
2. Import FBX into Blender
3. Apply textures from `vgl/textures/` — use `*_ddna.dds` for diffuse, `*_ddn.dds` for normals

Female version is in `female_v2/armor/vgl/` — same process with `f_vgl_specialist_heavy_helmet_01.skin`.

---

## File type reference

| Extension | What it is | Needed? |
|---|---|---|
| `.skin` | Rigged character mesh (Noesis input) | Yes — main mesh |
| `.cgf` | Static prop mesh (Noesis input) | Yes — prop/detached version |
| `.skinm` / `.cgfm` | Material sidecar — Noesis needs this next to the mesh | Yes — keep alongside |
| `.cdf` | Character definition — links mesh + material + skeleton | Reference only |
| `.chr` | Skeleton/rig | Optional for static renders |
| `.mtl` | Material definition (XML) — lists which textures to use | Reference only |
| `.dds` | Base texture (use this in Blender) | Yes |
| `.dds.1`–`.dds.7` | Streaming mip levels (game engine only) | No — ignore |
| `.cga` / `.cgam` | Animated geometry | Optional |

---

## Downloading individual folders

```bash
git clone --branch Tech-zip --single-branch --depth 1 --filter=blob:none --sparse \
  https://github.com/saladin1980/sc_datapack.git
cd sc_datapack

# grab just the helmet
git sparse-checkout set "extras_export/Data/Objects/Characters/Human/male_v7/armor/vgl"

# grab just the slaver legs
git sparse-checkout set "extras_export/Data/Objects/Characters/Human/male_v7/armor/cds" \
                        "extras_export/Data/Objects/Characters/Human/male_v7/armor/slaver"
```
