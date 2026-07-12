"""Pulls real Google Maps business data via Apify's compass/crawler-google-places
actor and inserts into raw_listings, deduped on the real Google place_id.

Run small first: `python maps_ingest.py --test` does one city, one search term,
5 places, so we can eyeball real output and actual Apify credit cost before
committing to the full Charlotte-metro run. No fabricated data, no synthetic
place_ids — if the actor returns nothing usable, that's a real result to act on,
not something to paper over.
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

APIFY_TOKEN = os.environ.get("MAPS_DATA_API_KEY")
ACTOR_ENDPOINT = "https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items"
DB_PATH = Path(__file__).parent / "directory.db"

SEARCH_TERMS = [
    "tent rental",
    "party rental",
    "table and chair rental",
]

# Added session 8 to widen supply for small towns where the original 3 broad
# terms were already returning fewer results than the max_places cap (i.e. we
# were hitting real supply limits, not our own capture ceiling) — distinct
# search terms surface distinct businesses Google Maps didn't return for the
# broader queries.
EXTRA_SEARCH_TERMS = [
    "bounce house rental",
    "linen rental",
    "wedding decor rental",
    "chair rental",
]


def run_actor(search_terms, city, state, max_places, scrape_details=True):
    if not APIFY_TOKEN:
        sys.exit("MAPS_DATA_API_KEY not set in .env")
    payload = {
        "searchStringsArray": search_terms,
        "city": city,
        "state": state,
        "countryCode": "us",
        "maxCrawledPlacesPerSearch": max_places,
        "language": "en",
        "scrapePlaceDetailPage": scrape_details,
        "skipClosedPlaces": True,
    }
    resp = requests.post(
        ACTOR_ENDPOINT,
        params={"token": APIFY_TOKEN},
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def upsert_listings(conn, items, search_term, target_city_id):
    now = datetime.now(timezone.utc).isoformat()
    inserted, skipped = 0, 0
    for item in items:
        place_id = item.get("placeId")
        name = item.get("title")
        if not place_id or not name:
            skipped += 1
            continue
        conn.execute(
            """
            INSERT INTO raw_listings (
                place_id, name, category, address, city, state, postal_code,
                lat, lng, phone, website, rating, review_count, hours_json,
                photo_url, search_term, target_city_id, source, raw_json, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(place_id) DO UPDATE SET
                rating=excluded.rating,
                review_count=excluded.review_count,
                hours_json=excluded.hours_json,
                phone=excluded.phone,
                website=excluded.website,
                scraped_at=excluded.scraped_at
            """,
            (
                place_id,
                name,
                item.get("categoryName"),
                item.get("address"),
                item.get("city"),
                item.get("state"),
                item.get("postalCode"),
                item.get("location", {}).get("lat"),
                item.get("location", {}).get("lng"),
                item.get("phone"),
                item.get("website"),
                item.get("totalScore"),
                item.get("reviewsCount"),
                json.dumps(item.get("openingHours")) if item.get("openingHours") else None,
                item.get("imageUrl"),
                search_term,
                target_city_id,
                "apify:compass/crawler-google-places",
                json.dumps(item),
                now,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="tiny single-city, single-term, 5-place run")
    parser.add_argument("--city", default="Charlotte")
    parser.add_argument("--state", default="NC")
    parser.add_argument("--max-places", type=int, default=None)
    parser.add_argument("--extra-terms", action="store_true", help="run only EXTRA_SEARCH_TERMS (supply-widening pass)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id FROM target_cities WHERE city=? AND state=?", (args.city, args.state)
    ).fetchone()
    if not row:
        sys.exit(f"{args.city}, {args.state} not in target_cities — run db_setup.py first or add it")
    target_city_id = row[0]

    if args.test:
        terms = [SEARCH_TERMS[0]]
        max_places = 5
    elif args.extra_terms:
        terms = EXTRA_SEARCH_TERMS
        max_places = args.max_places or 20
    else:
        terms = SEARCH_TERMS
        max_places = args.max_places or 30

    print(f"Running Apify actor: {terms} in {args.city}, {args.state} (max {max_places}/term)...")
    items = run_actor(terms, args.city, args.state, max_places)
    print(f"Actor returned {len(items)} raw items.")

    inserted, skipped = upsert_listings(conn, items, ",".join(terms), target_city_id)
    print(f"Inserted/updated {inserted} rows, skipped {skipped} (missing place_id or name).")
    conn.close()


if __name__ == "__main__":
    main()
