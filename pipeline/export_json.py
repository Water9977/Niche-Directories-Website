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
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).parent / "directory.db"
EXPORT_DIR = Path(__file__).parent / "export"

NAME_EXCLUDE_KEYWORDS = ["glamping"]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    candidates = conn.execute(
        """
        SELECT l.*, rl.geo_status FROM listings l
        JOIN raw_listings rl ON l.raw_listing_id = rl.id
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
            "SELECT item_type, price_low, price_high, unit, source_snippet, extracted_by_model, last_checked FROM listing_pricing WHERE listing_id = ?",
            (row["id"],),
        ).fetchall()
        output.append({
            "name": row["name"],
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
            "delivery_available": row["delivery_available"],
            "setup_included": row["setup_included"],
            "weekend_surcharge": row["weekend_surcharge"],
            "pricing": [dict(p) for p in pricing],
        })

    out_path = EXPORT_DIR / "charlotte-metro-listings.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Candidates checked: {len(candidates)}")
    print(f"Excluded (off-niche): {len(excluded)}")
    for eid, name, reason in excluded:
        print(f"  - {name} ({reason})")
    print(f"Published: {len(published)} -> {out_path}")
    conn.close()


if __name__ == "__main__":
    main()
