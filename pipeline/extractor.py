"""
Phase 1: Extract all files from Data.p4k into output/.
Mirrors internal p4k directory structure.

Uses unp4k.exe as a subprocess (C# native, ~97 files/sec).
Version derived from P4K parent folder name — no scdatatools import needed.
unp4k extracts relative to cwd, so we set cwd=OUTPUT_DIR.

Skips extraction if output/.version already matches current version.
"""
import os
import sys
import time
import signal
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import P4K_PATH, OUTPUT_DIR, LOGS_DIR, UNP4K_EXE

# Known total from test_open.py — update if P4K changes
TOTAL_FILES = 1_287_040


def _kill_any_running_unp4k():
    """Kill any orphaned unp4k.exe processes before we start."""
    subprocess.run(
        ["taskkill", "/f", "/im", "unp4k.exe"],
        capture_output=True,  # suppress output whether found or not
    )


def _clear_output():
    """Remove output dir contents. Does NOT run concurrently with unp4k."""
    print(f"Clearing {OUTPUT_DIR} ...")
    sys.stdout.flush()
    # Rename first so the directory is gone instantly, delete tree in background
    import tempfile
    trash = Path(tempfile.mkdtemp(dir=OUTPUT_DIR.parent, prefix=".trash_"))
    try:
        OUTPUT_DIR.rename(trash)
    except OSError:
        # Fallback: delete in place
        trash = OUTPUT_DIR
    # Recreate empty output dir immediately so unp4k can start
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Now delete the renamed trash dir (blocking — contents are already moved)
    subprocess.run(["cmd", "/c", f"rd /s /q \"{trash}\""], capture_output=True)


def run():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    error_log = LOGS_DIR / "extraction_errors.log"
    unp4k_log = LOGS_DIR / "unp4k_output.log"

    # Safety: kill any leftover unp4k.exe from a previous interrupted run
    _kill_any_running_unp4k()

    version = P4K_PATH.parent.name

    version_file = OUTPUT_DIR / ".version"
    if version_file.exists() and version_file.read_text().strip() == version:
        print(f"Already extracted version {version}, skipping.")
        return

    # No cleanup needed — unp4k overwrites existing files.
    # Manual cleanup of output/ should be done outside this script if required.
    total = TOTAL_FILES

    print(f"Extracting {total:,} files (version: {version}) -> {OUTPUT_DIR}")
    print(f"P4K: {P4K_PATH}")
    sys.stdout.flush()

    start = time.time()

    # Write unp4k stdout directly to a log file — avoids .NET pipe-buffering
    # blocking Python. We poll the log file size for progress instead.
    with open(str(unp4k_log), "w", encoding="utf-8", errors="replace") as log_out:
        proc = subprocess.Popen(
            [str(UNP4K_EXE), str(P4K_PATH)],
            cwd=str(OUTPUT_DIR),
            stdout=log_out,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # Poll log file size for progress — each line ~80 bytes on average
        AVG_LINE_BYTES = 80
        last_reported = 0

        while proc.poll() is None:
            time.sleep(5)
            try:
                fsize = os.path.getsize(str(unp4k_log))
            except OSError:
                continue
            estimated = fsize // AVG_LINE_BYTES
            if estimated - last_reported >= 1000:
                elapsed = time.time() - start
                rate = estimated / elapsed if elapsed > 0 else 0
                eta = (total - estimated) / rate if rate > 0 else 0
                print(f"  ~{estimated:,} / {total:,}  ({rate:.0f} files/s, ETA {eta/60:.1f}m)")
                sys.stdout.flush()
                last_reported = estimated

        stderr_out = proc.stderr.read().strip()

    # Exact count from log file
    try:
        with open(str(unp4k_log), "r", encoding="utf-8", errors="replace") as f:
            lines = [l for l in f if " | " in l]
        extracted = len(lines)
    except OSError:
        extracted = 0

    failed = total - extracted

    if stderr_out or failed > 100:
        with open(str(error_log), "a", encoding="utf-8") as f:
            if stderr_out:
                f.write(f"--- stderr ---\n{stderr_out}\n")

    if proc.returncode != 0:
        print(f"WARNING: unp4k exited {proc.returncode} — check {error_log}")
    else:
        version_file.write_text(version)

    elapsed = time.time() - start

    print(f"\n--- Extraction complete ---")
    print(f"  Version   : {version}")
    print(f"  Extracted : {extracted:,}")
    print(f"  Missing   : {failed:,}")
    print(f"  Exit code : {proc.returncode}")
    print(f"  Elapsed   : {elapsed/60:.1f} min")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
