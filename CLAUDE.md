# SC DataPack Pipeline — Claude Project Instructions

## CRITICAL: Deployment workflow

GitHub Pages is served from the ROOT of the `gh-pages` branch.
NOT from `docs/` on main. NOT from `main` at all.

```
gh-pages branch root/
  index.html              <- live index page
  ships_preview.html      <- live ships report
  components_preview.html <- live components report
  armor_preview.html      <- live armor report
  weapons_preview.html    <- live weapons report
```

### To deploy a new or updated report:

```bash
git checkout gh-pages
cp X:/SC_DataPack/reports/<report>.html X:/SC_DataPack/sc-pipeline/<report>.html
# edit index.html to add/update the card
git add <report>.html index.html
git commit -m "feat: ..."
git push origin gh-pages
git checkout main
```

The `docs/` folder on `main` is NOT served — it exists only as a leftover from
a mistaken prior session. Do not commit report HTML to `docs/` or `main`.

---

## Repo layout

```
X:\SC_DataPack\sc-pipeline\   <- git repo root (main branch)
  pipeline/                   <- Python scripts
    ships_preview.py
    components_preview.py
    armor_preview.py
    weapons_preview.py
    extractor.py
  config/
    settings.py
  docs/                       <- IGNORED for deployment (do not use)
  CLAUDE.md                   <- this file
  EXTRACTION_PLAN.md
  README.md

X:\SC_DataPack\reports\       <- generated HTML output (source for gh-pages)
X:\SC_DataPack\output\        <- extracted P4K files
X:\SC_DataPack\venv\          <- Python venv
```

## Phase status (all complete as of 2026-02-27)

- [x] extractor.py — unp4k full extract done
- [x] ships_preview.py — 276 ships, gh-pages live
- [x] components_preview.py — 2,516 components, gh-pages live
- [x] armor_preview.py — 2,230+ items, gh-pages live
- [x] weapons_preview.py — 166 ship + 333 FPS + 102 attachments, gh-pages live

## Index card style (gh-pages)

Match the existing `.card` pattern in `index.html` on `gh-pages`:
- `display: flex; flex-wrap: wrap` container, cards are `width: 380px`
- `card-icon` (emoji) / `card-title` / `card-desc` / `card-meta` with `.tag` spans
- href = `<report>_preview.html` (no path prefix — same directory)
