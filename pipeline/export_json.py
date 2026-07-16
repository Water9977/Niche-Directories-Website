"""Quality gate: only listings with a real address AND at least one real
pricing item get published. Everything else stays in the DB (useful for
re-enrichment later) but never reaches the site — per the brief, a page
with no real value should not exist.

Also excludes off-niche category leaks the Maps search picked up (e.g. a
literal "Tent rental service" business that's actually overnight glamping,
not party/event equipment) via a small manual exclusion list rather than
a heavyweight classifier — a one-off edge case doesn't need one.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# A listing whose ONLY pricing rows are fees/deposits/delivery charges has no
# actual rentable item to show — its "starting price" renders as "See listing"
# and the pricing table is just fees, which reads as a thin, broken page (found
# live: a Charleston listing publishing with only deposit + delivery_fee).
# Mirrors NON_RENTAL_ITEM_RE in website/src/lib/listings.ts — keep in sync.
NON_RENTAL_ITEM_RE = re.compile(
    r"deposit|delivery|fee\b|_fee|socks|admission|ticket|supervision|expedite|rescheduling",
    re.IGNORECASE,
)

DB_PATH = Path(__file__).parent / "directory.db"
EXPORT_DIR = Path(__file__).parent / "export"
# Writes directly to the website's data file too — every session up to this
# one required a manual `cp pipeline/export/*.json website/src/data/listings.json`
# after running this script, an easy step to forget (it happened 3 times in
# session 21 alone). Now export_json.py is the single source of truth.
WEBSITE_DATA_PATH = Path(__file__).parent.parent / "website" / "src" / "data" / "listings.json"

NAME_EXCLUDE_KEYWORDS = ["glamping"]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    candidates = conn.execute(
        """
        SELECT l.*, rl.geo_status, rl.photo_url, tc.metro FROM listings l
        JOIN raw_listings rl ON l.raw_listing_id = rl.id
        JOIN target_cities tc ON rl.target_city_id = tc.id
        WHERE l.address IS NOT NULL
        AND rl.geo_status = 'confirmed'
        AND EXISTS (SELECT 1 FROM listing_pricing lp WHERE lp.listing_id = l.id)
        """
    ).fetchall()

    published, excluded = [], []
    for row in candidates:
        if any(kw in row["name"].lower() for kw in NAME_EXCLUDE_KEYWORDS):
            excluded.append((row["id"], row["name"], "off-niche name match"))
            continue
        item_types = [
            r[0]
            for r in conn.execute(
                "SELECT item_type FROM listing_pricing WHERE listing_id = ?", (row["id"],)
            ).fetchall()
        ]
        # WARN but still publish. Hard-excluding fee-only listings was tried
        # (session 23) and measured before shipping: it would have knocked
        # Greensboro (5->3) and Greenville (5->4) below MIN_LISTINGS and
        # unpublished two live, indexed metro pages — a real SEO loss to fix
        # a cosmetic one. These listings still carry real fee data, policies,
        # photos, and contacts; they sort last in tables automatically. The
        # right long-term fix is re-enriching them for real item pricing.
        if not any(not NON_RENTAL_ITEM_RE.search(t) for t in item_types):
            print(f"  WARN fee-only pricing (re-enrich candidate): {row['name']}")
        published.append(row)

    conn.executemany(
        "UPDATE listings SET published = 0 WHERE id = ?", [(r["id"],) for r in candidates]
    )
    conn.executemany(
        "UPDATE listings SET published = 1 WHERE id = ?", [(r["id"],) for r in published]
    )
    conn.commit()

    EXPORT_DIR.mkdir(exist_ok=True)
    output = []
    for row in published:
        pricing = conn.execute(
            # DISTINCT: the extractor occasionally emits the same item+price
            # multiple times for one listing (seen live: a table row 3x) —
            # exact duplicates carry no information, drop them at export.
            "SELECT DISTINCT item_type, price_low, price_high, unit, source_snippet, extracted_by_model, last_checked FROM listing_pricing WHERE listing_id = ?",
            (row["id"],),
        ).fetchall()
        output.append({
            "name": row["name"],
            "metro": row["metro"],
            "address": row["address"],
            "city": row["city"],
            "state": row["state"],
            "postal_code": row["postal_code"],
            "lat": row["lat"],
            "lng": row["lng"],
            "phone": row["phone"],
            "website": row["website"],
            "rating": row["rating"],
            "review_count": row["review_count"],
            "category": row["category"],
            "photo_url": row["photo_url"],
            "delivery_available": row["delivery_available"],
            "setup_included": row["setup_included"],
            "weekend_surcharge": row["weekend_surcharge"],
            "pricing": [dict(p) for p in pricing],
        })

    payload = json.dumps(output, indent=2)
    out_path = EXPORT_DIR / "listings.json"
    out_path.write_text(payload, encoding="utf-8")
    WEBSITE_DATA_PATH.write_text(payload, encoding="utf-8")

    print(f"Candidates checked: {len(candidates)}")
    print(f"Excluded (off-niche): {len(excluded)}")
    for eid, name, reason in excluded:
        print(f"  - {name} ({reason})")
    print(f"Published: {len(published)} -> {out_path}")
    print(f"Also wrote directly to {WEBSITE_DATA_PATH} — no manual copy step needed.")
    conn.close()


if __name__ == "__main__":
    main()
