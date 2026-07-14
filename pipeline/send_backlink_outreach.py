"""Sends backlink-outreach emails to businesses we've published — but ONLY to
a real email address extracted from their own scraped website content, never
a guessed one (no info@/contact@ guessing). We already scraped each listed
business's site for pricing (see `scraped_pages.markdown`); this reuses that
same real content to pull a real contact email, so no new scraping/cost.

Real per-listing pricing pages often carry noise that looks like an email
(image filenames, tracking-pixel domains, Wix/Sentry boilerplate) — filtered
out via JUNK_DOMAINS/JUNK_LOCALPARTS below, built from what was actually
observed in a dry run, not guessed in advance.

Dry run (default): writes a preview CSV, sends nothing.
Real send: `python send_backlink_outreach.py --send` — requires
RESEND_API_KEY in .env and the sending domain verified in Resend.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(__file__).parent / "directory.db"
LISTINGS_JSON = Path(__file__).parent.parent / "website" / "src" / "data" / "listings.json"
PREVIEW_PATH = Path(__file__).parent / "export" / "backlink-outreach-real-emails.csv"

SITE = "https://eventrentalcosts.com"
FROM_ADDRESS = "EventRentalCosts.com <outreach@eventrentalcosts.com>"

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,24}\b")
JUNK_DOMAINS = (
    "sentry.io", "wixpress.com", "example.com", "godaddy.com", "schema.org",
    "w3.org", "domain.com", "yourdomain.com", "email.com", "yoursite.com",
    "sentry.wixpress.com", "sentry-next.wixpress.com",
)
JUNK_LOCALPARTS = ("noreply", "no-reply", "donotreply")
IMAGE_EXT_RE = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp)$")

TEMPLATE = """Hi {name} team,

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


def clean_emails(markdown: str) -> set[str]:
    found = set()
    for m in EMAIL_RE.findall(markdown or ""):
        m = m.strip(".,;:()[]<>\"'`").lower()
        if any(j in m for j in JUNK_DOMAINS):
            continue
        local = m.split("@")[0]
        if any(j in local for j in JUNK_LOCALPARTS):
            continue
        if IMAGE_EXT_RE.search(m):
            continue
        if len(m) > 60:
            continue
        found.add(m)
    return found


def slugify(text: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))


def compute_slugs(published: list[dict]) -> dict[tuple, str]:
    """Mirrors website/src/lib/listings.ts's makeUniqueSlugs exactly — the
    JSON export has no `slug` field, Astro computes it at build time, so we
    have to reproduce the same algorithm to get real, correct listing URLs."""
    base_slugs = [slugify(f"{p['name']}-{p['city']}") for p in published]
    counts: dict[str, int] = {}
    for s in base_slugs:
        counts[s] = counts.get(s, 0) + 1

    seen: dict[str, int] = {}
    slugs = {}
    for p, base in zip(published, base_slugs):
        key = (p["name"], p["city"])
        if counts[base] <= 1:
            slugs[key] = base
            continue
        with_postal = slugify(f"{p['name']}-{p['city']}-{p.get('postal_code') or ''}")
        n = seen.get(with_postal, 0) + 1
        seen[with_postal] = n
        slugs[key] = f"{with_postal}-{n}" if n > 1 else with_postal
    return slugs


def build_targets():
    published = json.loads(LISTINGS_JSON.read_text(encoding="utf-8"))
    by_name_city = {(p["name"], p["city"]): p for p in published}
    slugs = compute_slugs(published)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    db_rows = conn.execute(
        "SELECT id, raw_listing_id, name, city FROM listings WHERE published = 1"
    ).fetchall()

    targets = []
    for r in db_rows:
        p = by_name_city.get((r["name"], r["city"]))
        if not p:
            continue
        pages = conn.execute(
            "SELECT markdown FROM scraped_pages WHERE raw_listing_id = ?", (r["raw_listing_id"],)
        ).fetchall()
        emails = set()
        for pg in pages:
            emails |= clean_emails(pg["markdown"])
        if not emails:
            continue
        email = sorted(emails)[0]  # deterministic pick when a page has >1
        listing_url = f"{SITE}/listing/{slugs[(r['name'], r['city'])]}/"
        subject = f"You're listed on EventRentalCosts.com — real pricing, free"
        body = TEMPLATE.format(name=r["name"], city=r["city"], listing_url=listing_url)
        targets.append({
            "name": r["name"], "city": r["city"], "email": email,
            "listing_url": listing_url, "subject": subject, "body": body,
        })
    conn.close()
    return targets


def write_preview(targets):
    PREVIEW_PATH.parent.mkdir(exist_ok=True)
    with open(PREVIEW_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "city", "email", "listing_url", "subject", "body"])
        for t in targets:
            w.writerow([t["name"], t["city"], t["email"], t["listing_url"], t["subject"], t["body"]])
    print(f"Wrote {len(targets)} real-email targets to {PREVIEW_PATH}")


def send(targets):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("RESEND_API_KEY not set in .env — aborting.", file=sys.stderr)
        sys.exit(1)

    sent, failed = 0, []
    for t in targets:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": FROM_ADDRESS,
                "to": [t["email"]],
                "subject": t["subject"],
                "text": t["body"],
                "reply_to": "outreach@eventrentalcosts.com",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            sent += 1
            print(f"sent -> {t['name']} <{t['email']}>")
        else:
            failed.append((t["name"], t["email"], resp.status_code, resp.text))
            print(f"FAILED -> {t['name']} <{t['email']}>: {resp.status_code} {resp.text}")
        time.sleep(0.5)  # stay well under Resend's 2 req/s default limit

    print(f"\nDone: {sent} sent, {len(failed)} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Actually send via Resend (default is dry-run preview only)")
    args = parser.parse_args()

    targets = build_targets()
    write_preview(targets)

    if args.send:
        send(targets)
    else:
        print("Dry run only — nothing sent. Re-run with --send to actually send.")
