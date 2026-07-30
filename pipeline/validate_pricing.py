"""Verifies every listing_pricing row's price actually appears in its own
source_snippet before it's allowed to stay. Caught after the fact: the 8B
extraction model sometimes hallucinated a price (e.g. "$0.00" for generic
marketing copy with no real number, or misread a UI counter like "0 items"
as a price) instead of following the "only extract if explicitly stated"
rule. This is a real accuracy bug, not a hypothetical one — found via manual
spot-check of the exported site. Real per-item prices (even genuinely low
ones like $1.75/chair) are preserved; anything whose source_snippet doesn't
actually contain a matching dollar figure is removed.
"""
import re
import sqlite3
import sys
from pathlib import Path

# Real bug, found live 2026-07-23: the print loop below can crash on Windows'
# default console codepage (cp1252) whenever a snippet/item_type contains a
# character outside it (e.g. the "inches" double-prime, U+2033). Because the
# DELETE ran AFTER the print loop, every crash silently skipped deletion
# entirely — hallucinated $0 rows this script correctly *identified* were
# never actually removed from the DB across however many prior runs hit this.
# Fixed two ways: force utf-8 output, and reorder so DELETE always runs first.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).parent / "directory.db"

# \s* (not \s?) — some sites (Webflow-built ones especially) render "$" and the
# figure as separate DOM nodes, which Firecrawl's markdown captures as
# "$\n\n185.00". A single optional whitespace char misses that entirely,
# silently causing validate_pricing.py to treat a real, correctly-quoted
# price as unsupported and delete it. Found live 2026-07-23 debugging why
# ACC Rental's real Webflow pricing kept vanishing.
MONEY_RE = re.compile(r"\$\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)")

# Some sites write the figure before the symbol ("20$ ea.") instead of after
# ("$20"). Found live 2026-07-25, North Beach Rentals (Tybee Island) --
# real, correctly-quoted prices, just reversed order.
MONEY_RE_SUFFIX = re.compile(r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*\$")


def extract_dollar_amounts(text):
    if not text:
        return []
    # PDF-extracted price lists (found live 2026-07-25, Show Time Event
    # Rentals) sometimes render "$3.50" as "$3. 50" -- a stray space after
    # the decimal point from the original document's leader-dot formatting.
    # Without this, the regex below only ever captures "3", not "3.50",
    # and a 100% real price gets flagged unsupported. Normalize before
    # matching rather than trying to make the regex itself uglier.
    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)
    amounts = []
    for m in list(MONEY_RE.finditer(text)) + list(MONEY_RE_SUFFIX.finditer(text)):
        try:
            amounts.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return amounts


# A product-page URL inside a snippet names exactly which product the price
# belongs to, so it's the one case where the item_type can be checked against
# something authoritative rather than taken on trust.
PRODUCT_URL_RE = re.compile(r"/(?:product-page|product|rentals|items|shop)/([a-z0-9][a-z0-9\-_]*)", re.I)


def item_type_matches_snippet_url(item_type, snippet):
    """Guards a real blind spot in this script's main check: verifying the price
    appears in the snippet proves the NUMBER is real, never that it belongs to
    the item it's filed under. Found live 2026-07-26 — Sage Hill Rentals had 13
    rows (a third of its data) where the model reused one product's snippet
    across unrelated item_types: a `tent_10x10` priced $120 that is actually a
    pre-lit tree, a `table_round_60in` at $400 that is a sofa. Every one passed
    the price check cleanly, and the bogus tent price fed the site's tent-size
    stats.

    Only judges rows whose snippet carries a product URL with a genuinely
    descriptive slug (2+ real tokens). Slugs like `/items/med` say nothing
    about the product, so those rows pass through untouched rather than being
    deleted on weak evidence. Verified against the full DB before shipping:
    43 pass, 11 skipped as non-descriptive, and exactly the 13 known-bad rows
    flagged — no collateral damage to any other listing.
    """
    m = PRODUCT_URL_RE.search(snippet or "")
    if not m:
        return True
    slug_tokens = {t for t in re.split(r"[-_]", m.group(1)) if len(t) > 2}
    if len(slug_tokens) < 2:
        return True
    type_tokens = {t for t in re.split(r"[^a-z0-9]+", (item_type or "").lower()) if len(t) > 2}
    return bool(slug_tokens & type_tokens)


def price_is_supported(price, snippet_amounts, tolerance=0.01):
    if price is None:
        return True  # nothing to verify
    if price <= 0:
        # No real rental item costs $0 — this is virtually always a broken
        # price-widget display on the business's own site (a JS placeholder
        # captured mid-load), not a real price, even when it's technically
        # quoted verbatim in the source snippet.
        return False
    return any(abs(price - amt) <= tolerance for amt in snippet_amounts)


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, listing_id, item_type, price_low, price_high, source_snippet FROM listing_pricing"
    ).fetchall()

    kept, unsupported, mislabeled = 0, [], []
    for pid, listing_id, item_type, price_low, price_high, snippet in rows:
        amounts = extract_dollar_amounts(snippet)
        ok = price_is_supported(price_low, amounts) and price_is_supported(price_high, amounts)
        if not (ok and amounts):
            unsupported.append((pid, listing_id, item_type, price_low, snippet))
        elif not item_type_matches_snippet_url(item_type, snippet):
            # Price is real, but it belongs to a different product than the one
            # this row claims — publishing it would misattribute a real price.
            mislabeled.append((pid, listing_id, item_type, price_low, snippet))
        else:
            kept += 1

    removed = unsupported + mislabeled

    # Delete BEFORE printing — a print-loop crash (encoding, whatever) must
    # never be able to block the actual data-integrity fix, which is the one
    # part of this script that actually matters.
    if removed:
        conn.executemany("DELETE FROM listing_pricing WHERE id = ?", [(r[0],) for r in removed])
        conn.commit()

    print(f"Checked {len(rows)} pricing rows: {kept} verified, {len(unsupported)} unsupported by their own source_snippet.")
    if mislabeled:
        print(
            f"{len(mislabeled)} more removed as MISLABELED — real price, but the snippet's "
            f"product URL names a different item than the row claims:"
        )
        for pid, listing_id, item_type, price_low, snippet in mislabeled:
            url = PRODUCT_URL_RE.search(snippet or "")
            print(f"  MISLABEL listing_id={listing_id} {item_type} ${price_low} is actually: {url.group(1) if url else '?'}")
    for pid, listing_id, item_type, price_low, snippet in unsupported:
        safe_snippet = (snippet or "")[:80]
        print(f"  REMOVE listing_id={listing_id} {item_type} price_low={price_low} snippet=\"{safe_snippet}\"")

    # A listing that loses its only real pricing row should also lose its
    # published status next time export_json runs — no page with no real
    # value.
    orphaned = conn.execute(
        "SELECT id, name FROM listings WHERE id NOT IN (SELECT DISTINCT listing_id FROM listing_pricing) AND published = 1"
    ).fetchall()
    if orphaned:
        print(f"\n{len(orphaned)} listing(s) will lose published status on next export_json run (no verified pricing left):")
        for lid, name in orphaned:
            print(f"  - {name.encode('ascii', 'replace').decode()}")

    conn.close()


if __name__ == "__main__":
    main()
