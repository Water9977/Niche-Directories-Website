"""Generates a backlink outreach list from our own published listings.

Every video researched on directory-site SEO independently stressed the same
thing: on-page SEO alone hits a traffic ceiling without backlinks. The
cheapest, most natural backlink source we have is the businesses we're
already giving free exposure to — we listed their real pricing, so asking
for a link back is a fair, low-friction, zero-cost ask (not cold spam).

Outputs a CSV: business name, city, contact page guess, our listing URL,
and a draft outreach message. Does NOT send anything — sending real emails
requires explicit human action per the project's safety rules.
"""
import csv
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path(__file__).parent / "directory.db"
OUT_PATH = Path(__file__).parent / "export" / "backlink-outreach.csv"

SITE = "https://eventrentalcosts.com"


def slugify(text):
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))


TEMPLATE = """Subject: You're listed on EventRentalCosts.com — real pricing, free

Hi {name} team,

I run EventRentalCosts.com, a comparison site for real, published rental \
pricing in {city}. I recently added your business with the pricing you \
publish on your own site — no cost to you, no login required:

{listing_url}

If you're able to, a link back to that page from your site (or just \
eventrentalcosts.com) would help other {city} customers find you through \
search, and helps us keep growing the directory. Totally understand if not \
— either way, wanted you to know you're listed and to flag if anything \
looks wrong so we can fix it.

Thanks,
EventRentalCosts.com
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, city, state, website FROM listings WHERE published = 1 ORDER BY city, name"
    ).fetchall()

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "city", "state", "website", "listing_url", "draft_message"])
        for r in rows:
            slug = slugify(f"{r['name']}-{r['city']}")
            listing_url = f"{SITE}/listing/{slug}/"
            contact_guess = ""
            if r["website"]:
                host = urlparse(r["website"]).netloc or r["website"]
                contact_guess = f"{r['website'].rstrip('/')}/contact"
            message = TEMPLATE.format(name=r["name"], city=r["city"], listing_url=listing_url)
            writer.writerow([r["name"], r["city"], r["state"], r["website"] or "", listing_url, message])

    print(f"Wrote {len(rows)} outreach targets to {OUT_PATH}")
    with_website = sum(1 for r in rows if r["website"])
    print(f"{with_website} have a website (contact page guess included), {len(rows) - with_website} don't")


if __name__ == "__main__":
    main()
