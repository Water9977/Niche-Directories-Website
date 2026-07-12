"""Scrapes each validated business's OWN website (never aggregators) for
pricing/rates/about pages, storing raw markdown in scraped_pages.

This only follows real business websites, never Yelp/Facebook/Angi/etc
profile pages that happen to be in the `website` field. Run small first
with --limit before committing to the full batch — Firecrawl credits
aren't unlimited either.
"""
import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import os
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY")
SCRAPE_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
DB_PATH = Path(__file__).parent / "directory.db"

EXCLUDED_HOSTS = {
    "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com",
    "yelp.com", "www.yelp.com",
    "angi.com", "www.angi.com",
    "thumbtack.com", "www.thumbtack.com",
    "homeadvisor.com", "www.homeadvisor.com",
    "weddingwire.com", "www.weddingwire.com",
    "theknot.com", "www.theknot.com",
    "reventals.com", "www.reventals.com",
    "linktr.ee", "google.com", "www.google.com",
    "maps.google.com", "business.google.com",
}

PRICING_KEYWORDS = ["pricing", "price", "rates", "rate", "cost", "catalog", "inventory", "menu"]

# Google Maps' category matching is loose — generic search terms like "party rental"
# and "table and chair rental" pull in venues, DJs, bridal shops, furniture stores,
# even Costco and Camping World. Only actual equipment-rental businesses match our
# niche; everything else is noise regardless of rating/review count.
ALLOWED_CATEGORIES = {
    "Party equipment rental service",
    "Tent rental service",
    "Equipment rental agency",
    "Furniture rental service",
    "Audiovisual equipment rental service",
}


def is_excluded(url):
    host = urlparse(url).netloc.lower()
    return host in EXCLUDED_HOSTS


def firecrawl_scrape(url):
    resp = requests.post(
        SCRAPE_ENDPOINT,
        headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"},
        json={"url": url, "formats": ["markdown", "links"], "onlyMainContent": True},
        timeout=60,
    )
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", {})
    return data


def find_pricing_link(base_url, links):
    for link in links or []:
        low = link.lower()
        if any(kw in low for kw in PRICING_KEYWORDS) and not is_excluded(link):
            return urljoin(base_url, link)
    return None


def store_page(conn, raw_listing_id, url, page_type, markdown):
    conn.execute(
        "INSERT INTO scraped_pages (raw_listing_id, url, page_type, markdown, scraped_at) VALUES (?, ?, ?, ?, ?)",
        (raw_listing_id, url, page_type, markdown, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(ALLOWED_CATEGORIES))
    candidates = conn.execute(
        f"""
        SELECT id, name, website FROM raw_listings
        WHERE geo_status = 'confirmed' AND website IS NOT NULL
        AND category IN ({placeholders})
        AND id NOT IN (SELECT DISTINCT raw_listing_id FROM scraped_pages)
        ORDER BY review_count DESC
        LIMIT ?
        """,
        (*ALLOWED_CATEGORIES, args.limit),
    ).fetchall()

    print(f"Enriching {len(candidates)} businesses...")
    done, skipped_excluded, failed = 0, 0, 0

    for raw_id, name, website in candidates:
        if is_excluded(website):
            print(f"  SKIP (aggregator domain): {name} -> {website}")
            skipped_excluded += 1
            continue

        home = firecrawl_scrape(website)
        if not home or not home.get("markdown"):
            print(f"  FAIL (no content): {name} -> {website}")
            failed += 1
            continue

        store_page(conn, raw_id, website, "homepage", home["markdown"])

        link_urls = [l.get("href", l) if isinstance(l, dict) else l for l in home.get("links", [])]
        pricing_url = find_pricing_link(website, link_urls)
        if pricing_url and pricing_url != website:
            pricing_page = firecrawl_scrape(pricing_url)
            if pricing_page and pricing_page.get("markdown"):
                store_page(conn, raw_id, pricing_url, "pricing", pricing_page["markdown"])
                print(f"  OK: {name} -> homepage + pricing page found")
            else:
                print(f"  OK: {name} -> homepage only (pricing link found but scrape failed)")
        else:
            print(f"  OK: {name} -> homepage only (no pricing link found)")
        done += 1

    print(f"\nDone: {done}, skipped (excluded domain): {skipped_excluded}, failed: {failed}")
    conn.close()


if __name__ == "__main__":
    main()
