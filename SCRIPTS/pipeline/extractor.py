"""
Phase 1: Full extraction from Data.p4k into Data_Extraction/.

Extracts all files from the archive (~3.5 hours, ~223 GB on disk).
unp4k does not support path filtering so the full archive is extracted.

Uses unp4k.exe as a subprocess (C# native tool).
Configure paths in .env at the repo root before running.

Skips extraction if Data_Extraction/.version already matches current version.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import P4K_PATH, OUTPUT_DIR, LOGS_DIR, UNP4K_EXE, UNFORGE_EXE

# Selective extraction — only what the pipeline actually needs
EXTRACT_PATHS = [
    "Data/Libs/Foundry",
    "Data/Localization",
]


def _detect_version():
    """Read build_manifest.id if present, fall back to parent folder name."""
    manifest = P4K_PATH.parent / "build_manifest.id"
    if manifest.exists():
        version = manifest.read_text(encoding="utf-8").strip()
        if version:
            return version
    return P4K_PATH.parent.name


def _kill_any_running_unp4k():
    """Kill any orphaned unp4k.exe processes before we start."""
    subprocess.run(
        ["taskkill", "/f", "/im", "unp4k.exe"],
        capture_output=True,
    )


def _clear_output():
    """Remove Data_Extraction contents before a fresh extract."""
    print(f"Clearing {OUTPUT_DIR} ...")
    sys.stdout.flush()
    import tempfile
    try:
        trash = Path(tempfile.mkdtemp(dir=OUTPUT_DIR.parent, prefix=".trash_"))
        OUTPUT_DIR.rename(trash)
    except OSError:
        trash = OUTPUT_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmd", "/c", f"rd /s /q \"{trash}\""], capture_output=True)


def run():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    unp4k_log = LOGS_DIR / "unp4k_output.log"
    error_log  = LOGS_DIR / "extraction_errors.log"

    _kill_any_running_unp4k()

    version = _detect_version()

    version_file = OUTPUT_DIR / ".version"
    if version_file.exists() and version_file.read_text().strip() == version:
        print(f"Already extracted version {version}, skipping.")
        return

    print(f"Version  : {version}")
    print(f"P4K      : {P4K_PATH}")
    print(f"Output   : {OUTPUT_DIR}")
    print(f"Note     : Full extraction (~3.5 hrs). Go get a coffee.")
    sys.stdout.flush()

    start = time.time()

    # unp4k does not support path filtering — extracts full archive
    cmd = [str(UNP4K_EXE), str(P4K_PATH)]

    with open(str(unp4k_log), "w", encoding="utf-8", errors="replace") as log_out:
        proc = subprocess.Popen(
            cmd,
            cwd=str(OUTPUT_DIR),
            stdout=log_out,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Poll log file for progress — no hardcoded total needed
        AVG_LINE_BYTES = 80
        last_reported  = 0

        while proc.poll() is None:
            time.sleep(5)
            try:
                fsize = os.path.getsize(str(unp4k_log))
            except OSError:
                continue
            estimated = fsize // AVG_LINE_BYTES
            if estimated - last_reported >= 500:
                elapsed = time.time() - start
                rate = estimated / elapsed if elapsed > 0 else 0
                print(f"  ~{estimated:,} files extracted  ({rate:.0f}/s, {elapsed/60:.1f}m elapsed)")
                sys.stdout.flush()
                last_reported = estimated

        stderr_out = proc.stderr.read().strip()

    # Count extracted files from log
    try:
        with open(str(unp4k_log), "r", encoding="utf-8", errors="replace") as f:
            extracted = sum(1 for l in f if " | " in l)
    except OSError:
        extracted = 0

    if stderr_out:
        with open(str(error_log), "a", encoding="utf-8") as f:
            f.write(f"--- stderr ---\n{stderr_out}\n")

    elapsed = time.time() - start

    if proc.returncode != 0:
        print(f"WARNING: unp4k exited {proc.returncode} — check {error_log}")
        print(f"\n--- Extraction failed ---")
        print(f"  Exit code : {proc.returncode}")
        print(f"  Elapsed   : {elapsed/60:.1f} min")
        sys.stdout.flush()
        return

    # ── Convert any CryXML binary files to plain XML ─────────────────────────
    print(f"\nConverting CryXML files...")
    sys.stdout.flush()
    forge_result = subprocess.run(
        [str(UNFORGE_EXE), str(OUTPUT_DIR)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if forge_result.returncode != 0:
        print(f"WARNING: unforge exited {forge_result.returncode}")
        with open(str(error_log), "a", encoding="utf-8") as f:
            f.write(f"--- unforge stderr ---\n{forge_result.stderr}\n")
    else:
        print(f"CryXML conversion done.")
    sys.stdout.flush()

    version_file.write_text(version)

    print(f"\n--- Extraction complete ---")
    print(f"  Version   : {version}")
    print(f"  Extracted : {extracted:,} files")
    print(f"  Exit code : {proc.returncode}")
    print(f"  Elapsed   : {elapsed/60:.1f} min")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
