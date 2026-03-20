# SC DataPack — Asset Extracts

CryEngine model files extracted from Star Citizen for use in videos, renders, and art.

---

## Downloads

| Folder | Contents |
|---|---|
| `hailstorm_export/` | Defiance Hailstorm armor — geometry, materials, textures (male + female) |

---

## How to use in Blender

**Option A — Blender CryEngine Importer** (imports .skin / .cgf directly)
https://github.com/chrislunt/blender_cryengine_importer

**Option B — Noesis** (freeware, converts to FBX)
1. Open Noesis, navigate to the `.skin` or `.cgf` file
2. Export as FBX
3. Import FBX into Blender

---

## Downloading a folder

```bash
git clone --branch Tech-zip --single-branch --depth 1 --filter=blob:none --sparse https://github.com/saladin1980/sc_datapack.git
cd sc_datapack
git sparse-checkout set hailstorm_export
```
