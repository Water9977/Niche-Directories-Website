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

MONEY_RE = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")


def extract_dollar_amounts(text):
    if not text:
        return []
    amounts = []
    for m in MONEY_RE.finditer(text):
        try:
            amounts.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return amounts


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

    kept, removed = 0, []
    for pid, listing_id, item_type, price_low, price_high, snippet in rows:
        amounts = extract_dollar_amounts(snippet)
        ok = price_is_supported(price_low, amounts) and price_is_supported(price_high, amounts)
        if ok and amounts:
            kept += 1
        else:
            removed.append((pid, listing_id, item_type, price_low, snippet))

    # Delete BEFORE printing — a print-loop crash (encoding, whatever) must
    # never be able to block the actual data-integrity fix, which is the one
    # part of this script that actually matters.
    if removed:
        conn.executemany("DELETE FROM listing_pricing WHERE id = ?", [(r[0],) for r in removed])
        conn.commit()

    print(f"Checked {len(rows)} pricing rows: {kept} verified, {len(removed)} unsupported by their own source_snippet.")
    for pid, listing_id, item_type, price_low, snippet in removed:
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
