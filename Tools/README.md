# Tools

This folder holds external tools required by the pipeline.
**Nothing here is committed to git** — you install these yourself.

---

## Python venv

The virtual environment for running the pipeline scripts.

```bash
# Create (from repo root)
python -m venv Tools\venv

# Activate (Windows)
Tools\venv\Scripts\activate

# Install scdatatools (used for selective P4K extraction)
pip install numpy>=1.24.3
pip install scdatatools
```

Set up once. Activate before running any pipeline script or `runner.py`.

> **Note:** `runner.py` will auto-install scdatatools if it's missing,
> as long as the venv is active.

---

## unp4k — CryXML converter

`unforge.exe` (part of the unp4k suite) converts CryXML binary files
to plain XML after extraction. Downloaded automatically by `runner.py`
on first run.

If auto-download fails, get it manually:
1. Download from: <https://github.com/dolkensp/unp4k/releases>
2. Extract the `unp4k-suite-*.zip` into this folder so you have:
   ```
   Tools\
     unp4k-suite\
       unp4k.exe
       unforge.exe
   ```
