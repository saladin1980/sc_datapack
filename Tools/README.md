# Tools

This folder holds external tools required by the pipeline.
**Nothing here is committed to git** — you install these yourself.

---

## unp4k — P4K extractor

Used by `extractor.py` to unpack `Data.p4k`.

1. Download the latest release from: <https://github.com/dolkensp/unp4k/releases>
2. Extract the zip into this folder so you have:
   ```
   Tools\
     unp4k-suite\
       unp4k.exe
   ```
3. Set `SC_UNP4K_EXE` in your `.env` to the full path of `unp4k.exe`

---

## Python venv

The virtual environment for running the pipeline scripts.

```bash
# Create (from repo root)
python -m venv Tools\venv

# Activate (Windows)
Tools\venv\Scripts\activate

# No packages to install — pipeline uses stdlib only
```

Set up once. Activate before running any pipeline script or `runner.py`.
