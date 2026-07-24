"""Scrapes each validated business's OWN website (never aggregators) for
pricing/catalog/shop pages, storing raw markdown in scraped_pages.

This only follows real business websites, never Yelp/Facebook/Angi/etc
profile pages that happen to be in the `website` field. Run small first
with --limit before committing to the full batch — Firecrawl credits
aren't unlimited either.

v2: widened the nav-label keyword net (session 6 only followed literal
"pricing"/"rates" links and missed sites that publish real prices under
"Shop"/"Catalog"/"Rentals"/"Products" nav labels instead), follows up to
3 candidate pages per business instead of 1, and probes a fixed list of
common paths directly when no nav link matches at all.

v3: found live 2026-07-24 debugging 3 businesses that showed as "fee-only"
(no real item pricing) despite genuinely having it. Two real gaps, both
fixed here: (1) every scrape now waits a few seconds for JS to render --
several sites (Booqable-powered checkout widgets especially) only put real
per-item prices in the DOM after client-side JS runs, so a plain static
fetch saw nothing. (2) when the nav-keyword crawl AND the common-path
guesses both find nothing, this now falls back to Firecrawl's /map
endpoint with a pricing-flavored search query -- some real catalogs
(Interactive Playgrounds' "/inventory/*" category pages, Magic Special
Events' tag-taxonomy product pages) simply aren't linked from the
homepage nav with a keyword this script's link-scan would ever match.
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
MAP_ENDPOINT = "https://api.firecrawl.dev/v2/map"
DB_PATH = Path(__file__).parent / "directory.db"

# Milliseconds to let client-side JS render before Firecrawl captures the
# page. Booqable-style checkout widgets and similar cart embeds render real
# prices only after this; a plain static fetch sees an empty/placeholder DOM.
WAIT_FOR_MS = 4000

MAP_SEARCH_QUERY = "pricing catalog rentals shop inventory products"

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

# Ordered roughly by how likely the label is to lead straight to real prices.
PRICING_KEYWORDS = [
    "pricing", "price", "prices", "rates", "rate", "cost", "costs",
    "catalog", "catalogue", "inventory", "menu",
    "shop", "store", "products", "product",
    "rentals", "rental", "rent",
    "book", "booking", "order", "reserve", "reservation",
    "browse", "collection", "items", "gallery",
]

# Tried directly when the homepage's own nav doesn't surface a matching link —
# some catalog pages sit outside <main> (header/footer nav) and Firecrawl's
# onlyMainContent extraction can miss them.
COMMON_PATH_GUESSES = [
    "/shop", "/store", "/catalog", "/rentals", "/products", "/pricing",
    "/price-list", "/rates", "/inventory", "/book-now",
]

MAX_PAGES_PER_BUSINESS = 3

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
    try:
        resp = requests.post(
            SCRAPE_ENDPOINT,
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"},
            json={
                "url": url,
                "formats": ["markdown", "links"],
                "onlyMainContent": True,
                "waitFor": WAIT_FOR_MS,
            },
            timeout=90,
        )
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json().get("data", {})


def firecrawl_map(url, search, limit=10):
    try:
        resp = requests.post(
            MAP_ENDPOINT,
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"},
            json={"url": url, "search": search, "limit": limit},
            timeout=30,
        )
    except requests.exceptions.RequestException:
        return []
    if resp.status_code != 200:
        return []
    return [l["url"] for l in resp.json().get("links", []) if l.get("url")]


def find_pricing_links(base_url, links, max_links):
    seen, found = set(), []
    for kw in PRICING_KEYWORDS:
        for link in links or []:
            low = link.lower()
            if kw in low and not is_excluded(link):
                full = urljoin(base_url, link)
                if full not in seen and full != base_url:
                    seen.add(full)
                    found.append(full)
                    if len(found) >= max_links:
                        return found
    return found


def store_page(conn, raw_listing_id, url, page_type, markdown):
    conn.execute(
        "INSERT INTO scraped_pages (raw_listing_id, url, page_type, markdown, scraped_at) VALUES (?, ?, ?, ?, ?)",
        (raw_listing_id, url, page_type, markdown, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def enrich_one(conn, raw_id, name, website):
    home = firecrawl_scrape(website)
    if not home or not home.get("markdown"):
        return "fail"

    store_page(conn, raw_id, website, "homepage", home["markdown"])
    pages_found = 1

    link_urls = [l.get("href", l) if isinstance(l, dict) else l for l in home.get("links", [])]
    candidates = find_pricing_links(website, link_urls, MAX_PAGES_PER_BUSINESS - 1)

    if not candidates:
        for path in COMMON_PATH_GUESSES:
            guess = urljoin(website, path)
            if is_excluded(guess):
                continue
            page = firecrawl_scrape(guess)
            if page and page.get("markdown") and len(page["markdown"]) > 200:
                store_page(conn, raw_id, guess, "pricing_guess", page["markdown"])
                pages_found += 1
                break
    else:
        for url in candidates:
            page = firecrawl_scrape(url)
            if page and page.get("markdown"):
                store_page(conn, raw_id, url, "pricing", page["markdown"])
                pages_found += 1

    if pages_found == 1:
        # Nothing found via nav links or common-path guesses. Some real
        # catalogs live outside the homepage nav entirely (category or
        # tag-taxonomy pages), so fall back to Firecrawl's own site index.
        for url in firecrawl_map(website, MAP_SEARCH_QUERY, limit=6):
            if is_excluded(url) or url == website or "sitemap" in url.lower():
                continue
            page = firecrawl_scrape(url)
            if page and page.get("markdown") and len(page["markdown"]) > 200:
                store_page(conn, raw_id, url, "pricing_mapped", page["markdown"])
                pages_found += 1
                if pages_found >= MAX_PAGES_PER_BUSINESS:
                    break

    return pages_found


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

    print(f"Enriching {len(candidates)} businesses (up to {MAX_PAGES_PER_BUSINESS} pages each)...")
    done, skipped_excluded, failed = 0, 0, 0

    for raw_id, name, website in candidates:
        if is_excluded(website):
            print(f"  SKIP (aggregator domain): {name} -> {website}")
            skipped_excluded += 1
            continue

        result = enrich_one(conn, raw_id, name, website)
        if result == "fail":
            print(f"  FAIL (no content): {name} -> {website}")
            failed += 1
        else:
            print(f"  OK: {name} -> {result} page(s) scraped")
            done += 1

    print(f"\nDone: {done}, skipped (excluded domain): {skipped_excluded}, failed: {failed}")
    conn.close()


if __name__ == "__main__":
    main()
