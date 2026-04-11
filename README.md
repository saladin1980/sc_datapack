# SC DataPack — Asset Extracts

CryEngine model files extracted from Star Citizen for use in Blender, videos, and renders.

---

## Folder structure

```
extractions/    full character/armor dumps — body meshes, heads, complete armor sets
extras/         specific pieces pulled on request — targeted extracts for individual items
person_export.zip   base body + all player heads, ready to unzip and use
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

### Full character (body + head + armor) — `person_export.zip`

> **Quickest start:** download `person_export.zip` from this branch — everything below is already inside it, ready to unzip and use.

The body, head, and armor are all separate `.skin` files in Star Citizen but they share the same armature. Import them all into the same Blender scene and they snap together automatically — no manual positioning needed.

---

#### Step 1 — Get the files

Either:
- Download `person_export.zip` from this branch and extract it, **or**
- Use the files directly from `extractions/Data/Objects/Characters/Human/`

---

#### Step 2 — Convert body to FBX in Noesis

Open Noesis, navigate to the body `.skin` file, right-click → **Export** → format **FBX** → Export.

| Body type | File |
|---|---|
| Male standard | `…/male_v7/body/m_body.skin` |
| Male slim | `…/male_v7/body/m_body_thin.skin` |
| Male heavy | `…/male_v7/body/m_body_fat.skin` |
| Female | `…/female_v2/body/f_body.skin` |

Keep the `.skinm` file next to each `.skin` — Noesis needs it to read materials.

---

#### Step 3 — Convert a head to FBX in Noesis

Pick any archetype — these are the same heads from the in-game character creator:

```
…/heads/male/pu/archetypes/
  male_archetype_v001/male_archetype_v001_t1_head.skin   ← v001 through v015
…/heads/female/pu/archetypes/
  female_archetype_v001/female_archetype_v001_t1_head.skin  ← v001 through v014
```

Export to FBX the same way as the body.

---

#### Step 4 — Import into Blender

1. **File → Import → FBX** → import the body FBX
2. **File → Import → FBX** → import the head FBX into the **same scene**

The head sits at the neck automatically — both use the same root armature.

---

#### Step 5 — Apply skin textures to the body

Textures are in `body/textures/`. The numbered files match the character creator skin tone slots.

In **Shader Editor**, select the body mesh and connect:

| Node | File | Socket |
|---|---|---|
| Image Texture | `m_body_01_diff.dds` (pick any tone 01–15) | Base Color |
| Image Texture → Normal Map node | `m_body_ddna.dds` | Normal |

Named skin tone files if you prefer:

| `.mtl` / texture | Tone |
|---|---|
| `m_body_cau` / `*_cau_diff.dds` | Caucasian light |
| `m_body_cau_yllw` / `*_cau_yllw_diff.dds` | Caucasian warm |
| `m_body_brwn` / `*_brwn_diff.dds` | Brown |
| `m_body_blk` / `*_blk_diff.dds` | Dark |

Female uses the same pattern — `f_body_01_diff.dds` through `f_body_14_diff.dds`.

---

#### Step 6 — Apply skin textures to the head

Each head folder has its own `textures/` subfolder:

```
…/male_archetype_v001/textures/
  male_archetype_v001_t1_head_*_diff.dds   ← Base Color
  male_archetype_v001_t1_head_*_ddna.dds   ← Normal map
```

Same Shader Editor setup as the body.

---

#### Step 7 — Add armor on top

Import any armor `.skin` from this repo the same way (Noesis → FBX → Blender). Because all SC character meshes share the same armature, every armor piece drops straight onto the body with zero repositioning.

---

#### What's inside person_export.zip

```
person_export/Data/Objects/Characters/Human/
  male_v7/body/
    m_body.skin + .skinm          standard male body
    m_body_thin.skin + .skinm     slim variant
    m_body_fat.skin + .skinm      heavy variant
    m_body.cdf                    character def (reference only)
    m_body.mtl + m_body_*.mtl     material files — one per skin tone
    textures/
      m_body_diff.dds             default diffuse
      m_body_01_diff.dds – m_body_15_diff.dds    numbered skin tones
      m_body_ddna.dds             normal map
      m_body_fat_diff.dds + _fat_ddna.dds         heavy body textures

  female_v2/body/
    f_body.skin + .skinm
    f_body.cdf
    f_body.mtl + f_body_*.mtl
    textures/
      f_body_diff.dds
      f_body_01_diff.dds – f_body_14_diff.dds
      f_body_ddna.dds

  heads/male/pu/archetypes/
    male_archetype_v001/ – male_archetype_v015/
      <name>_t1_head.skin + .skinm
      textures/

  heads/female/pu/archetypes/
    female_archetype_v001/ – female_archetype_v014/
      <name>_t1_head.skin + .skinm
      textures/
```

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
