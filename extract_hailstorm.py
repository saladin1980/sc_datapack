"""
Defiance Hailstorm Armor — Model Extractor
============================================
Pulls all geometry, material, and texture files for the Defiance Hailstorm armor
set from Data.p4k and writes them to hailstorm_export/.

Run with the venv Python:
  Tools\\venv\\Scripts\\python.exe extract_hailstorm.py

Output folder: hailstorm_export/
  Preserves the full path structure from Data.p4k so Blender importers can
  resolve cross-file references (materials pointing to textures, etc.)

NOTE: Files are CryEngine format (.cdf, .skin, .cgf, .mtl, .dds).
Blender cannot open these natively. Your friend needs one of:
  - Blender CryEngine Importer addon: https://github.com/chrislunt/blender_cryengine_importer
  - Noesis (freeware converter) with the CryEngine plugin
"""
import sys
import time
from pathlib import Path

ROOT    = Path(__file__).parent
SCRIPTS = ROOT / "SCRIPTS"
sys.path.insert(0, str(SCRIPTS))
from config.settings import P4K_PATH

OUTPUT = ROOT / "hailstorm_export"

# Path fragments to match (case-insensitive).
# Any p4k entry whose lowercased filename contains one of these is extracted.
PATTERNS = [
    # Male geometry + materials
    "objects/characters/human/male_v7/armor/slaver/",
    # Female geometry
    "objects/characters/human/female_v2/armor/slaver/",
    # Female legs (shares CDS model folder — grab only the hailstorm pieces)
    "objects/characters/human/female_v2/armor/cds/f_cds_heavy_armor_01_legs",
    # Textures — slaver set
    "textures/characters/human/male_v7/armor/slaver",
    "textures/characters/human/female_v2/armor/slaver",
]


def _matches(filename: str) -> bool:
    low = filename.lower().replace("\\", "/")
    return any(p in low for p in PATTERNS)


def main():
    if not P4K_PATH.exists():
        print(f"ERROR: Data.p4k not found at {P4K_PATH}")
        print("Set SC_P4K_PATH in .env or place Data.p4k in the repo root.")
        sys.exit(1)

    print(f"Data.p4k : {P4K_PATH}")
    print(f"Output   : {OUTPUT}")
    print()
    print("Loading p4k file list ...")
    sys.stdout.flush()

    from scdatatools.sc import StarCitizen
    sc = StarCitizen(str(P4K_PATH))

    print("Scanning for Hailstorm armor files ...")
    sys.stdout.flush()

    entries = [info for info in sc.p4k.infolist() if _matches(info.filename)]

    if not entries:
        print("No matching files found. Check that Data.p4k is the correct version.")
        sys.exit(1)

    print(f"Found {len(entries)} files. Extracting ...")
    sys.stdout.flush()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    extracted = []
    errors    = []

    for info in entries:
        try:
            sc.p4k._extract_member(info, OUTPUT)
            extracted.append(info.filename)
            print(f"  + {info.filename}")
            sys.stdout.flush()
        except Exception as e:
            errors.append((info.filename, str(e)))
            print(f"  ! SKIP {info.filename}: {e}")
            sys.stdout.flush()

    print()
    print(f"Done: {len(extracted)} extracted, {len(errors)} errors")
    print(f"Output: {OUTPUT}")
    print()
    print("--- FILES FOR YOUR FRIEND ---")
    print("Format: CryEngine (.cdf / .skin / .cgf / .mtl / .dds)")
    print("To open in Blender:")
    print("  Option A: Blender CryEngine Importer addon")
    print("            https://github.com/chrislunt/blender_cryengine_importer")
    print("  Option B: Convert with Noesis (freeware) -> FBX -> Blender")
    print()
    print("Zip the entire hailstorm_export/ folder and send it over.")


if __name__ == "__main__":
    main()
