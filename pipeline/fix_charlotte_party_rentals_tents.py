"""One-off correction, not a general pipeline step.

Fable-5 audit (B8) found `listing_id=1` (Charlotte Party Rentals) published
with a single mislabeled pricing row: item_type `tent_frame`, $1,000, sourced
from "Minimum project size: $1,000." — that's an order minimum, not a tent
price, and it made the listing look like a company that only rents one
$1,000 tent. Their real inventory page
(https://charlottepartyrentals.net/inventory/tents/) publishes 33 real,
itemized tent prices. Re-scraped via Firecrawl 2026-07-14, parsed
deterministically below (no LLM — the source markdown is already clean
structured product listings, a regex is more reliable than an extraction
model for this exact format and stays traceable to the exact source text).

Run once: `python fix_charlotte_party_rentals_tents.py`
"""
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).parent / "directory.db"
LISTING_ID = 1
SOURCE_URL = "https://charlottepartyrentals.net/inventory/tents/"

# Raw markdown from the Firecrawl scrape, 2026-07-14. Each product block is
# `[Name\\...from$Price](url)` — captures (name, price).
RAW_MARKDOWN = Path(__file__).parent / "charlotte_party_rentals_tents_raw.md"

PRODUCT_RE = re.compile(
    r"\[(\d+.?x\d+.?\s+[^\\\[\]]+?)\\+.*?from\$([0-9,]+\.\d{2})\]",
    re.DOTALL | re.IGNORECASE,
)


def slugify_item(name: str) -> str:
    # e.g. "40’x80′ Gable End Tent" -> tent_40x80_gable_end
    clean = re.sub(r"[''’′]", "", name).strip()
    m = re.match(r"(\d+)x(\d+)\s+(.*)", clean, re.IGNORECASE)
    if not m:
        return "tent_" + re.sub(r"[^a-z0-9]+", "_", clean.lower()).strip("_")
    w, h, rest = m.groups()
    rest = re.sub(r"\btent\b", "", rest, flags=re.IGNORECASE).strip()
    rest_slug = re.sub(r"[^a-z0-9]+", "_", rest.lower()).strip("_")
    return f"tent_{w}x{h}_{rest_slug}"


def main():
    markdown = RAW_MARKDOWN.read_text(encoding="utf-8")
    seen = {}
    for m in PRODUCT_RE.finditer(markdown):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        price = float(m.group(2).replace(",", ""))
        item_type = slugify_item(name)
        # A few sizes appear twice in the page (once as gallery card, once as
        # a duplicate calendar-widget reference) — keep the first, real, value.
        if item_type not in seen:
            seen[item_type] = (name, price)

    if not seen:
        print("No products parsed — check RAW_MARKDOWN content/regex before touching the DB.")
        return

    print(f"Parsed {len(seen)} real tent products:")
    for item_type, (name, price) in seen.items():
        print(f"  {item_type}: ${price:.2f}  (\"{name}\")")

    conn = sqlite3.connect(DB_PATH)
    old = conn.execute(
        "SELECT id, item_type, price_low, source_snippet FROM listing_pricing WHERE listing_id = ?",
        (LISTING_ID,),
    ).fetchall()
    print(f"\nRemoving {len(old)} old row(s): {old}")
    conn.execute("DELETE FROM listing_pricing WHERE listing_id = ?", (LISTING_ID,))

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            LISTING_ID,
            item_type,
            price,
            None,
            "per event",
            f"from${price:,.2f}",
            SOURCE_URL,
            "manual-scrape-session21-deterministic-parse",
            now,
        )
        for item_type, (name, price) in seen.items()
    ]
    conn.executemany(
        """INSERT INTO listing_pricing
           (listing_id, item_type, price_low, price_high, unit, source_snippet, source_url, extracted_by_model, last_checked)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    print(f"\nInserted {len(rows)} real pricing rows for listing_id={LISTING_ID}.")
    conn.close()


if __name__ == "__main__":
    main()
