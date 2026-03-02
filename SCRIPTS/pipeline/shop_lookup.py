"""
shop_lookup.py -- Shared shop-availability helper (no pipeline imports).

Reads reports/JSON/shops.json (built by shops.py) and provides:
  load_shop_lookup()    ->  {class_name_lower: [entry_dicts]}
  shop_html(entries)    ->  HTML for an "Available at" section (returns "" if empty)
  SHOP_CSS              ->  CSS string to splice into each report's <style> block

Kept import-free from the rest of the pipeline so any script can safely import
this without creating circular dependencies.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import REPORTS_DIR


def load_shop_lookup():
    """
    Load shops.json, return {class_name.lower(): [row_dicts]}.
    Returns {} silently if shops.json doesn't exist yet
    (allows report scripts to run independently before Shops step).
    """
    path = REPORTS_DIR / "JSON" / "shops.json"
    if not path.exists():
        return {}
    try:
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for row in data.get("data", []):
        cn = row.get("class_name")
        if cn:
            out.setdefault(cn.lower(), []).append(row)
    return out


def shop_html(entries):
    """
    Render a compact "Available at (N)" section for an item card.
    entries : list of shop row dicts (shop, location, buy_auec, sell_auec)
    Returns "" when entries is falsy.
    """
    if not entries:
        return ""

    # Deduplicate by (shop, location, buy_auec, sell_auec)
    seen = set()
    deduped = []
    for e in entries:
        key = (e.get("shop", ""), e.get("location", ""),
               e.get("buy_auec", 0), e.get("sell_auec", 0))
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    n      = len(deduped)
    limit  = 5
    shown  = deduped[:limit]
    extra  = deduped[limit:]

    def _row_html(e):
        buy  = e.get("buy_auec", 0)
        sell = e.get("sell_auec", 0)
        shop = e.get("shop", "—")
        loc  = e.get("location", "")
        price = ""
        if buy:
            price += f'<span class="sh-buy">{buy:,} aUEC</span>'
        if sell:
            price += f'<span class="sh-sell">sell {sell:,}</span>'
        return (
            f'<div class="sh-row">'
            f'<span class="sh-name">{shop}</span>'
            f'<span class="sh-loc">{loc}</span>'
            f'{price}'
            f'</div>'
        )

    rows_html = "".join(_row_html(e) for e in shown)

    extra_html = ""
    if extra:
        extra_rows = "".join(_row_html(e) for e in extra)
        extra_html = (
            f'<div class="sh-more" style="display:none">{extra_rows}</div>'
            f'<button class="sh-toggle" '
            f'onclick="this.previousElementSibling.style.display=\'block\';'
            f'this.style.display=\'none\'">+ {len(extra)} more</button>'
        )

    return (
        f'<div class="shop-avail">'
        f'<div class="sh-hdr">Available at ({n})</div>'
        f'{rows_html}{extra_html}'
        f'</div>'
    )


# ── CSS to splice into each report's <style> block ──────────────────────────

SHOP_CSS = """
/* ── Shop availability (injected by shop_lookup.py) ── */
.shop-avail { margin-top:10px; padding:8px 10px; background:rgba(0,0,0,.18);
              border-radius:4px; border:1px solid #2a2f3d; }
.sh-hdr  { font-size:10px; font-weight:700; color:#8b949e; text-transform:uppercase;
           letter-spacing:.08em; margin-bottom:6px; }
.sh-row  { display:flex; gap:6px; align-items:baseline; font-size:11px;
           padding:2px 0; border-bottom:1px solid rgba(255,255,255,.04); flex-wrap:wrap; }
.sh-row:last-child { border-bottom:none; }
.sh-name { color:#c9d1d9; font-weight:500; min-width:110px; }
.sh-loc  { color:#8b949e; flex:1; }
.sh-buy  { color:#4caf82; white-space:nowrap; }
.sh-sell { color:#e8a030; white-space:nowrap; font-size:10px; }
.sh-toggle { background:none; border:1px solid #2a2f3d; border-radius:3px;
             color:#8b949e; font-size:10px; cursor:pointer; padding:1px 6px; margin-top:4px; }
.sh-toggle:hover { border-color:#58a6ff; color:#58a6ff; }
/* components table sub-line */
.comp-shops { margin-top:3px; font-size:10px; color:#8b949e; line-height:1.4; }
.comp-shops .cs-entry { white-space:nowrap; }
.comp-shops .cs-price { color:#4caf82; }
"""
