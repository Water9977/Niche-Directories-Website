"""Creates the build-time SQLite schema for the party/event rental directory.

Three-state fields (yes/no/unknown) are stored as TEXT, never coerced to a
boolean — an absent field must stay distinguishable from a confirmed "no".
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "directory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS target_cities (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    metro TEXT,
    lat REAL,
    lng REAL,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(city, state)
);

CREATE TABLE IF NOT EXISTS raw_listings (
    id INTEGER PRIMARY KEY,
    place_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    lat REAL,
    lng REAL,
    phone TEXT,
    website TEXT,
    rating REAL,
    review_count INTEGER,
    hours_json TEXT,
    photo_url TEXT,
    search_term TEXT,
    target_city_id INTEGER REFERENCES target_cities(id),
    source TEXT NOT NULL,
    raw_json TEXT,
    scraped_at TEXT NOT NULL,
    geo_status TEXT NOT NULL DEFAULT 'unchecked'
);
CREATE INDEX IF NOT EXISTS idx_raw_listings_target_city ON raw_listings(target_city_id);
CREATE INDEX IF NOT EXISTS idx_raw_listings_geo_status ON raw_listings(geo_status);

CREATE TABLE IF NOT EXISTS scraped_pages (
    id INTEGER PRIMARY KEY,
    raw_listing_id INTEGER NOT NULL REFERENCES raw_listings(id),
    url TEXT NOT NULL,
    page_type TEXT,
    markdown TEXT,
    scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scraped_pages_listing ON scraped_pages(raw_listing_id);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY,
    raw_listing_id INTEGER NOT NULL UNIQUE REFERENCES raw_listings(id),
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    lat REAL,
    lng REAL,
    phone TEXT,
    website TEXT,
    rating REAL,
    review_count INTEGER,
    category TEXT,
    hours_json TEXT,
    delivery_available TEXT NOT NULL DEFAULT 'unknown',
    setup_included TEXT NOT NULL DEFAULT 'unknown',
    weekend_surcharge TEXT NOT NULL DEFAULT 'unknown',
    published INTEGER NOT NULL DEFAULT 0,
    last_enriched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_listings_city ON listings(city, state);
CREATE INDEX IF NOT EXISTS idx_listings_published ON listings(published);

CREATE TABLE IF NOT EXISTS listing_pricing (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    item_type TEXT NOT NULL,
    price_low REAL,
    price_high REAL,
    unit TEXT,
    source_snippet TEXT,
    source_url TEXT,
    extracted_by_model TEXT,
    last_checked TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_listing_pricing_listing ON listing_pricing(listing_id);
"""

CHARLOTTE_METRO_SEED = [
    ("Charlotte", "NC", "Charlotte-Concord-Gastonia"),
    ("Concord", "NC", "Charlotte-Concord-Gastonia"),
    ("Gastonia", "NC", "Charlotte-Concord-Gastonia"),
    ("Huntersville", "NC", "Charlotte-Concord-Gastonia"),
    ("Matthews", "NC", "Charlotte-Concord-Gastonia"),
    ("Mooresville", "NC", "Charlotte-Concord-Gastonia"),
    ("Indian Trail", "NC", "Charlotte-Concord-Gastonia"),
    ("Monroe", "NC", "Charlotte-Concord-Gastonia"),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT OR IGNORE INTO target_cities (city, state, metro) VALUES (?, ?, ?)",
        CHARLOTTE_METRO_SEED,
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM target_cities").fetchone()[0]
    print(f"Schema ready at {DB_PATH}. target_cities rows: {count}")
    conn.close()


if __name__ == "__main__":
    main()
