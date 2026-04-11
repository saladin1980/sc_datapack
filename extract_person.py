"""
Human Character Base Mesh Extractor
=====================================
Extracts the base human body meshes and player-selectable head archetypes
from Data.p4k — the "person" that armor and clothing attaches to in Blender.

What this grabs:
  Male (male_v7):
    - body/m_body.skin/.skinm/.cdf + all .mtl skin tone variants
    - body/m_body_thin.skin/.skinm  (thin body type variant)
    - body/m_body_fat.skin/.skinm   (fat body type variant, if present)
    - body/textures/*.dds           (skin tone diffuse + normal maps, LODs stripped)
    - heads/male/pu/archetypes/male_archetype_v001-v015 (player character creator heads)
    - heads/male/pu/archetypes/*/textures/*.dds

  Female (female_v2):
    - body/f_body.skin/.skinm/.cdf + all .mtl skin tone variants
    - body/textures/*.dds
    - heads/female/pu/archetypes/female_archetype_v001-v014
    - heads/female/pu/archetypes/*/textures/*.dds

What this does NOT grab:
  - LOD meshes (lod1, lod2, ...) — Blender only needs the base mesh
  - NPC-specific heads (female01-44, named NPCs) — archetypes are the player ones
  - .dds.1 through .dds.7 mip levels — game streaming only, Blender ignores them
  - Anatomy sub-parts (separate torso/arm/leg skinning meshes) — not needed for rendering

Run with the venv Python:
  Tools\\venv\\Scripts\\python.exe extract_person.py

Output folder: person_export/
  Preserves full Data.p4k path structure so CryEngine importers can resolve
  cross-file references (materials -> textures, CDF -> skeleton -> mesh).

After extraction, open in Blender via Noesis:
  1. Noesis -> navigate to m_body.skin -> Export -> FBX
  2. Blender -> File -> Import -> FBX
  3. Apply textures from body/textures/ — use _diff.dds for skin tone Base Color,
     _ddna.dds for normals (separate R/G channels — use Normal Map node)
  4. Attach armor pieces: import armor .skin files, they share the same rig/skeleton
"""
import sys
import time
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"
sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH

OUTPUT = ROOT / "person_export"

# ── Match patterns (all case-insensitive, forward-slash normalised) ──────────

# Body mesh patterns — base mesh only, no LODs
BODY_PATTERNS = [
    # Male body meshes
    "objects/characters/human/male_v7/body/m_body.skin",
    "objects/characters/human/male_v7/body/m_body.skinm",
    "objects/characters/human/male_v7/body/m_body.cdf",
    "objects/characters/human/male_v7/body/m_body.mtl",
    "objects/characters/human/male_v7/body/m_body_thin.skin",
    "objects/characters/human/male_v7/body/m_body_thin.skinm",
    "objects/characters/human/male_v7/body/m_body_fat.skin",
    "objects/characters/human/male_v7/body/m_body_fat.skinm",
    # Female body meshes
    "objects/characters/human/female_v2/body/f_body.skin",
    "objects/characters/human/female_v2/body/f_body.skinm",
    "objects/characters/human/female_v2/body/f_body.cdf",
    "objects/characters/human/female_v2/body/f_body.mtl",
]

# Body .mtl variants (skin tones _01 through _15 etc) — prefix match
BODY_MTL_PREFIXES = [
    "objects/characters/human/male_v7/body/m_body_",
    "objects/characters/human/female_v2/body/f_body_",
]

# Body textures — the textures/ subfolder, base .dds only (no mip .dds.N)
BODY_TEXTURE_DIRS = [
    "objects/characters/human/male_v7/body/textures/",
    "objects/characters/human/female_v2/body/textures/",
]

# Player archetype heads — all variants v001 through v999
HEAD_ARCHETYPE_DIRS = [
    "objects/characters/human/heads/male/pu/archetypes/",
    "objects/characters/human/heads/female/pu/archetypes/",
]


def _is_lod(filename: str) -> bool:
    """Return True for LOD variants we don't need."""
    low = filename.lower()
    # Skip lod1, lod2, etc. suffix before extension: _lod1.skin, _lod2.cgf
    import re
    return bool(re.search(r'_lod\d+\.(skin|skinm|cgf|cgfm)$', low))


def _is_mip(filename: str) -> bool:
    """Return True for .dds.N streaming mip levels."""
    import re
    return bool(re.search(r'\.dds\.[0-9a-z]+$', filename.lower()))


def _matches(filename: str) -> bool:
    low = filename.lower().replace("\\", "/")

    # Skip mip levels always
    if _is_mip(filename):
        return False

    # Exact body mesh matches
    for pat in BODY_PATTERNS:
        if low.endswith(pat):
            return True

    # Body .mtl variants (m_body_01.mtl, m_body_cau.mtl, etc.)
    for prefix in BODY_MTL_PREFIXES:
        if prefix in low and low.endswith(".mtl"):
            return True

    # Body textures — base .dds only
    for tdir in BODY_TEXTURE_DIRS:
        if tdir in low and low.endswith(".dds"):
            return True

    # Head archetypes — everything inside archetype folders, no LODs, no mips
    for hdir in HEAD_ARCHETYPE_DIRS:
        if hdir in low:
            if _is_lod(filename):
                return False
            return True

    return False


def main():
    if not P4K_PATH.exists():
        print(f"ERROR: Data.p4k not found at {P4K_PATH}")
        print("Set SC_P4K_PATH in .env or place Data.p4k in the repo root.")
        sys.exit(1)

    print("=" * 60)
    print("  SC DataPack — Human Character Base Mesh Extractor")
    print("=" * 60)
    print(f"P4K    : {P4K_PATH}")
    print(f"Output : {OUTPUT}")
    print()
    print("Loading P4K file list ...")
    sys.stdout.flush()

    from scdatatools.sc import StarCitizen
    sc = StarCitizen(str(P4K_PATH))

    print("Scanning for character files ...")
    sys.stdout.flush()

    entries = [info for info in sc.p4k.infolist() if _matches(info.filename)]

    if not entries:
        print("ERROR: No matching files found. Check that Data.p4k is the correct SC install.")
        sys.exit(1)

    # Categorise for summary
    male_body   = [e for e in entries if "male_v7/body" in e.filename.lower().replace("\\", "/")]
    female_body = [e for e in entries if "female_v2/body" in e.filename.lower().replace("\\", "/")]
    male_heads  = [e for e in entries if "heads/male/pu/archetypes" in e.filename.lower().replace("\\", "/")]
    female_heads = [e for e in entries if "heads/female/pu/archetypes" in e.filename.lower().replace("\\", "/")]

    print(f"Found {len(entries)} files total:")
    print(f"  Male body   : {len(male_body)}")
    print(f"  Female body : {len(female_body)}")
    print(f"  Male heads  : {len(male_heads)}  (archetypes only)")
    print(f"  Female heads: {len(female_heads)}  (archetypes only)")
    print()
    print("Extracting ...")
    sys.stdout.flush()

    OUTPUT.mkdir(parents=True, exist_ok=True)

    extracted = []
    errors    = []
    start     = time.time()

    for i, info in enumerate(entries, 1):
        try:
            sc.p4k._extract_member(info, OUTPUT)
            extracted.append(info.filename)
            print(f"  + {info.filename}")
            sys.stdout.flush()
        except Exception as e:
            errors.append((info.filename, str(e)))
            print(f"  ! SKIP {info.filename}: {e}")
            sys.stdout.flush()

    elapsed = time.time() - start
    print()
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"  Extracted : {len(extracted)}")
    print(f"  Errors    : {len(errors)}")
    print(f"  Output    : {OUTPUT}")
    print()
    print("--- WHAT TO GIVE TECHMAN ---")
    print()
    print("Zip the entire person_export/ folder.")
    print()
    print("KEY FILES (open these in Noesis -> Export FBX -> import to Blender):")
    print()
    print("  MALE BODY:")
    print("    person_export/Data/Objects/Characters/Human/male_v7/body/m_body.skin")
    print("    (keep m_body.skinm next to it — material sidecar)")
    print("    (m_body.cdf = character definition linking mesh+rig — reference only)")
    print("    Skin tones: body/textures/m_body_01_diff.dds through m_body_15_diff.dds")
    print("    Normals:    body/textures/m_body_ddna.dds")
    print()
    print("  FEMALE BODY:")
    print("    person_export/Data/Objects/Characters/Human/female_v2/body/f_body.skin")
    print("    Skin tones: body/textures/f_body_01_diff.dds through f_body_14_diff.dds")
    print("    Normals:    body/textures/f_body_ddna.dds")
    print()
    print("  PLAYER HEADS (character creator archetypes):")
    print("    person_export/Data/Objects/Characters/Human/heads/male/pu/archetypes/")
    print("      male_archetype_v001/ through male_archetype_v015/")
    print("      Each: <name>_t1_head.skin + .skinm + textures/")
    print("    person_export/Data/Objects/Characters/Human/heads/female/pu/archetypes/")
    print("      female_archetype_v001/ through female_archetype_v014/")
    print()
    print("  BODY TYPE VARIANTS (male only):")
    print("    m_body_thin.skin — slim body type")
    print("    m_body_fat.skin  — heavy body type (if present)")
    print()
    print("BLENDER WORKFLOW:")
    print("  1. Open Noesis, navigate to m_body.skin")
    print("  2. Right-click -> Export -> FBX")
    print("  3. Blender -> File -> Import -> FBX")
    print("  4. Shader Editor: Image Texture -> _diff.dds -> Base Color")
    print("                    Image Texture -> _ddna.dds -> Normal Map node")
    print("  5. Import armor .skin files same way — they use the same skeleton,")
    print("     so they auto-align to the body in pose mode.")
    print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for path, err in errors:
            print(f"  {path}: {err}")


if __name__ == "__main__":
    main()
