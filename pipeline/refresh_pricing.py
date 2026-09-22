"""Freshness pass: re-verifies every published price against the business's own
live pages, so `last_checked` on the site means "we looked again", not "we
looked once in July".

Why this exists (2026-09-21): all pricing had last been checked 2026-07-12..27,
and the monthly re-enrich cadence (roadmap item 21) had never been built. A
third AdSense rejection asked for "ongoing curation and structural
maintenance"; the honest fix is to actually re-check the data, and to make that
repeatable.

The one rule this script exists to protect: **a row's last_checked only moves
when the row was verified against fresh content.** Nothing is re-dated on
trust. Rows that can't be verified stay on their old date and are reported.

How a row is judged (each row against ITS OWN source page):
  CONFIRMED   the snippet is still verbatim on the fresh page, or the same price
              still sits next to the item's own words.
  CHANGED     re-extraction found a different price for the same item, and that
              candidate passed the same anti-hallucination gate validate_pricing
              uses AND its snippet appears verbatim in the fresh page.
  MISSING     the source page loaded fine and has prices, but this item/price is
              gone. Reported; only removed with --allow-removals.
  UNVERIFIABLE  the source page couldn't be fetched (or rendered no prices at
              all). Left completely alone.
  UNLOCATED   the row's snippet is not on ANY stored page (39% of rows: their
              pages were fetched ad hoc and never stored), so the pricing pages
              are re-discovered and searched. If the price still isn't found, it
              is flagged for review. This is also how fabricated prices show up:
              RentMeUSA's four "prices" existed in no page, stored or fresh.
              Never treated as MISSING (we can't prove absence from a page we
              can't identify) and never removed without --remove-unlocated.

Fetching: Firecrawl (same settings as web_enrich.py, so results are comparable
to the original scrape) is the primary; Scrapling is the fallback when Firecrawl
fails, and a second opinion when Firecrawl returns a page with no dollar
figures at all (JS-rendered price widgets are the usual cause).

Default is a DRY RUN: nothing in the DB changes, a JSON report is written.
    python3 refresh_pricing.py --limit 5                  # dry run, 5 listings
    python3 refresh_pricing.py --all                      # dry run, everything
    python3 refresh_pricing.py --all --apply              # write safe updates
    python3 refresh_pricing.py --all --apply --allow-removals
After --apply, run validate_pricing.py then export_json.py (which also writes
the website's data file), then rebuild and deploy the site.

Run with python3 (3.13): that's the interpreter with Scrapling installed.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from ai_extract import build_content, extract  # noqa: E402  (LLM chain + page packing)
from export_json import NAME_EXCLUDE_KEYWORDS  # noqa: E402  (same publish exclusions)
from web_enrich import (  # noqa: E402  (same page-discovery rules the original enrichment used)
    COMMON_PATH_GUESSES,
    MAP_SEARCH_QUERY,
    find_pricing_links,
    firecrawl_map,
    is_excluded,
)
from validate_pricing import (  # noqa: E402  (the existing anti-hallucination gate)
    extract_dollar_amounts,
    item_type_matches_snippet_url,
    price_is_supported,
)

load_dotenv(Path(__file__).parent.parent / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY")
SCRAPE_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
DB_PATH = Path(__file__).parent / "directory.db"
REPORT_DIR = Path(__file__).parent / "refresh_reports"

# Identical to web_enrich.py so a refreshed page is comparable to the stored one.
WAIT_FOR_MS = 4000
MIN_USABLE_CHARS = 200

MONEY_RE = re.compile(r"\$\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)")
MONEY_RE_SUFFIX = re.compile(r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*\$")

STOPWORDS = {
    "the", "and", "for", "with", "per", "each", "from", "rental", "rentals", "rent", "price",
    "prices", "day", "event", "this", "that", "your", "our", "add", "cart", "more", "info",
    "details", "view", "item", "items", "only", "starting", "starts", "will", "can", "are",
    "you", "all", "new", "sale", "https", "http", "www", "com", "page", "product",
}

# Verdicts
CONFIRMED_VERBATIM = "confirmed_verbatim"
CONFIRMED_NEAR = "confirmed_near_item"
CONFIRMED_LLM = "confirmed_by_reextraction"
CHANGED = "changed"
MISSING = "missing"
UNVERIFIABLE = "unverifiable"
UNLOCATED = "unlocated"
CONFIRMED = {CONFIRMED_VERBATIM, CONFIRMED_NEAR, CONFIRMED_LLM}


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------
def norm(text):
    """Normalise page/snippet text so formatting differences don't hide a match.
    Applied identically to both sides of every comparison."""
    t = (text or "").lower()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\$\s+(?=\d)", "$", t)  # Webflow-style "$\n\n185.00"
    t = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", t)  # PDF-style "$3. 50"
    t = re.sub(r"[*_`|>#\\]", " ", t)  # markdown decoration
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def amounts_with_pos(text):
    out = []
    for rx in (MONEY_RE, MONEY_RE_SUFFIX):
        for m in rx.finditer(text):
            try:
                out.append((m.start(), float(m.group(1).replace(",", ""))))
            except ValueError:
                pass
    return sorted(out)


def dollar_count(text):
    return len(MONEY_RE.findall(text or "")) + len(MONEY_RE_SUFFIX.findall(text or ""))


def anchor_tokens(snippet, item_type):
    """The item's own words: what makes a price *this* item's price. Taken from the
    snippet with the money removed; if the snippet is a bare price ("$300.00"),
    falls back to the item_type's words."""
    s = MONEY_RE_SUFFIX.sub(" ", MONEY_RE.sub(" ", norm(snippet)))
    toks = [t for t in re.findall(r"[a-z0-9']{3,}", s) if t not in STOPWORDS and not t.isdigit()]
    seen, uniq = set(), []
    for t in toks:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    uniq = uniq[:10]
    if len(uniq) >= 2:
        return uniq, 0.6
    it = [t for t in re.split(r"[^a-z0-9]+", (item_type or "").lower())
          if len(t) >= 3 and t not in STOPWORDS and not t.isdigit()]
    return list(dict.fromkeys(it))[:6], 0.5


def window_ratio(window, tokens):
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in window) / len(tokens)


def type_key(item_type):
    return re.sub(r"[^a-z0-9]+", "_", (item_type or "").lower()).strip("_")


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------
FIRECRAWL_SLOTS = threading.BoundedSemaphore(5)  # never more than 5 calls in flight


def _firecrawl_post(payload):
    """POST to Firecrawl with backoff. Found 2026-09-21: two back-to-back runs with
    parallel fetches drew HTTP 429, and the first version of this gave up after one
    2-second retry, turning a rate limit into "page unreachable" verdicts for a
    whole listing. Honour Retry-After, back off up to ~40s, and cap concurrency."""
    note = "no attempt"
    for attempt in range(5):
        with FIRECRAWL_SLOTS:
            try:
                resp = requests.post(
                    SCRAPE_ENDPOINT, headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"}, json=payload, timeout=90
                )
            except requests.exceptions.RequestException as e:
                resp, note = None, f"firecrawl request error: {type(e).__name__}"
        if resp is not None:
            if resp.status_code == 200:
                return (resp.json().get("data") or {}), "ok"
            note = f"firecrawl HTTP {resp.status_code}"
            if resp.status_code not in (429, 500, 502, 503, 504):
                return None, note  # 4xx (blocked/not found) won't improve by retrying
            try:
                wait = float(resp.headers.get("Retry-After", 0))
            except ValueError:
                wait = 0
        else:
            wait = 0
        time.sleep(min(40, max(wait, 4 * 2 ** attempt)))
    return None, note


def fetch_firecrawl(url):
    data, note = _firecrawl_post(
        {"url": url, "formats": ["markdown"], "onlyMainContent": True, "waitFor": WAIT_FOR_MS}
    )
    if data is None:
        return "", note
    return data.get("markdown") or "", "ok"


def _html_to_text(raw_html):
    """Last-resort HTML -> text when Scrapling's own parser can't decode a page."""
    raw_html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw_html)
    raw_html = re.sub(r"(?s)<br\s*/?>|</(?:p|div|li|tr|h[1-6])>", "\n", raw_html)
    txt = re.sub(r"(?s)<[^>]+>", " ", raw_html)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#36;", "$"), ("&quot;", '"'), ("&#39;", "'")):
        txt = txt.replace(a, b)
    return re.sub(r"[ \t]+", " ", txt)


# Scrapling's browser engine drives Playwright, whose sync API is not safe to run
# from several threads at once; it is only needed for JS-rendered pages, so
# serialise it rather than risk it.
BROWSER_LOCK = threading.Lock()
BROWSER_BAD_HOSTS = set()  # hosts whose browser fetch already timed out this run


def _scrapling_text(page):
    """Page text from a Scrapling response. NOTE: `.markdown` is a METHOD in
    scrapling 0.4.x. The first version of this read `str(page.markdown)`, i.e. the
    repr of a bound method, always exactly 88 characters, and concluded that
    Scrapling "only ever gets a JS shell". It had been fetching the real page all
    along. Call it. Pages in legacy encodings raise UnicodeDecodeError from both
    parser routes, so fall back to decoding the raw body ourselves."""
    for getter in (
        lambda: str(page.markdown(main_content_only=False)),
        lambda: str(page.get_all_text(ignore_tags=("script", "style", "noscript"))),
    ):
        try:
            return getter(), "ok"
        except Exception:  # noqa: BLE001 — try the next route
            continue
    try:
        return _html_to_text(bytes(page.body).decode("utf-8", errors="replace")), "ok (raw decode)"
    except Exception as e:  # noqa: BLE001
        return "", f"decode error: {type(e).__name__}"


def fetch_scrapling(url, browser=False):
    """HTTP fetch (curl_cffi browser impersonation) or, with browser=True, a real
    headless-Chromium render for JS-built pages. Free, and not subject to
    Firecrawl's request-rate ceiling, which made a Firecrawl-only pass take ~2
    minutes per listing (about five hours for all 154).

    Fails FAST on purpose. A first full run stalled for 12 minutes because one site
    that never finished loading kept the (serialised) browser busy through three
    45-second retries, and every other listing queued behind it. So: short
    timeouts, one HTTP retry, a bounded wait for the browser lock, and a host that
    times out in the browser is not tried in the browser again this run."""
    label = "scrapling-browser" if browser else "scrapling"
    host = urlparse(url).netloc.lower()
    try:
        if browser:
            if host in BROWSER_BAD_HOSTS:
                return "", f"{label} skipped: host timed out earlier this run"
            from scrapling.fetchers import DynamicFetcher

            if not BROWSER_LOCK.acquire(timeout=90):
                return "", f"{label} skipped: browser busy"
            try:
                page = DynamicFetcher.fetch(url, headless=True, network_idle=True, timeout=20000)
            finally:
                BROWSER_LOCK.release()
        else:
            from scrapling.fetchers import Fetcher

            page = Fetcher.get(url, timeout=25, retries=1, stealthy_headers=True)
    except Exception as e:  # noqa: BLE001 — any fetch failure is just "no content"
        if browser:
            BROWSER_BAD_HOSTS.add(host)
        return "", f"{label} error: {type(e).__name__}"
    if page.status != 200:
        return "", f"{label} HTTP {page.status}"
    text, note = _scrapling_text(page)
    return text, note


def fetch_page(url, engine_mode, stored_dollars):
    """Returns dict(url, engine, text, ok, note).

    auto (default): Scrapling HTTP first. Escalate to Scrapling's browser, then to
    Firecrawl, only when the page is unusable OR shows no prices where the stored
    copy of this exact page had some (a JS-rendered price widget, or a block).
    Whichever attempt yields usable text with the most dollar figures wins.
    """
    tried = []
    best = {"url": url, "engine": None, "text": "", "ok": False, "note": "not fetched"}

    def consider(engine, text, note):
        nonlocal best
        tried.append(f"{engine}:{note}")
        ok = len(text.strip()) >= MIN_USABLE_CHARS
        cand = {"url": url, "engine": engine, "text": text, "ok": ok, "note": note}
        if ok and (not best["ok"] or dollar_count(text) > dollar_count(best["text"])):
            best = cand
        elif not best["ok"] and not best["engine"]:
            best = cand

    def needs_more():
        return not best["ok"] or (stored_dollars >= 1 and dollar_count(best["text"]) == 0)

    plans = {
        "auto": ["scrapling", "scrapling-browser", "firecrawl"],
        "scrapling": ["scrapling", "scrapling-browser"],
        "firecrawl": ["firecrawl"],
        "both": ["firecrawl", "scrapling"],
    }[engine_mode]
    for step in plans:
        if tried and not needs_more():
            break
        if step == "firecrawl":
            md, note = fetch_firecrawl(url)
        else:
            md, note = fetch_scrapling(url, browser=(step == "scrapling-browser"))
        consider(step, md, note)
    best["note"] = "; ".join(tried)
    return best


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def verify_row(row, haystack_norm):
    """row: dict(item_type, price_low, price_high, snippet). Returns (verdict, detail)."""
    snippet = row["snippet"] or ""
    sn = norm(snippet)
    price = row["price_low"]

    if len(sn) >= 6 and sn in haystack_norm:
        return CONFIRMED_VERBATIM, {}

    tokens, need = anchor_tokens(snippet, row["item_type"])
    occurrences = [(p, a) for p, a in amounts_with_pos(haystack_norm) if price is not None and abs(a - price) <= 0.01]
    for pos, _ in occurrences:
        window = haystack_norm[max(0, pos - 220): pos + 140]
        if window_ratio(window, tokens) >= need:
            high = row["price_high"]
            if high is not None and high != price:
                near = [a for _, a in amounts_with_pos(haystack_norm[max(0, pos - 300): pos + 300])]
                if not any(abs(a - high) <= 0.01 for a in near):
                    return MISSING, {"reason": "low price present but high price not found nearby"}
            return CONFIRMED_NEAR, {}

    # Item words present near *some* price, but not this row's price?
    nearby = set()
    if tokens:
        rarest = max(tokens, key=len)
        start = 0
        while True:
            i = haystack_norm.find(rarest, start)
            if i < 0:
                break
            window = haystack_norm[max(0, i - 220): i + 220]
            if window_ratio(window, tokens) >= need:
                nearby.update(a for _, a in amounts_with_pos(window))
            start = i + len(rarest)
            if start > len(haystack_norm) - 1 or len(nearby) > 12:
                break
    return MISSING, {"reason": "price not found next to this item", "nearby_amounts": sorted(nearby)[:8]}


def candidate_passes_gate(item, haystack_norm):
    """The anti-hallucination gate for a re-extracted price: same checks
    validate_pricing.py applies, plus the snippet must appear verbatim in the
    FRESH content (the model can't invent support that isn't on the page)."""
    price_low, price_high = item.get("price_low"), item.get("price_high")
    snippet = item.get("source_snippet") or ""
    if not isinstance(price_low, (int, float)):
        return False
    amounts = extract_dollar_amounts(snippet)
    if not amounts or not price_is_supported(price_low, amounts) or not price_is_supported(price_high, amounts):
        return False
    if not item_type_matches_snippet_url(item.get("item_type"), snippet):
        return False
    sn = norm(snippet)
    return len(sn) >= 6 and sn in haystack_norm


def match_candidate(row, cands, used):
    rk = type_key(row["item_type"])
    for i, c in enumerate(cands):
        if i not in used and type_key(c.get("item_type")) == rk:
            return i, "same item_type"
    r_tokens, _ = anchor_tokens(row["snippet"], row["item_type"])
    best, best_j = None, 0.0
    for i, c in enumerate(cands):
        if i in used:
            continue
        c_tokens, _ = anchor_tokens(c.get("source_snippet"), c.get("item_type"))
        if not r_tokens or not c_tokens:
            continue
        j = len(set(r_tokens) & set(c_tokens)) / len(set(r_tokens) | set(c_tokens))
        if j > best_j:
            best, best_j = i, j
    if best is not None and best_j >= 0.5:
        return best, f"snippet overlap {best_j:.2f}"
    return None, ""


# ---------------------------------------------------------------------------
# per-listing pass
# ---------------------------------------------------------------------------
def fetch_home_links(url):
    """All links on a business's homepage, INCLUDING the nav menu. Scrapling sees the
    whole DOM. (Firecrawl with onlyMainContent strips the nav, which is where the
    pricing/inventory links live; that is the gap web_enrich.py's own comments warn
    about and why discovery first missed Charlotte Party Rentals' /inventory/.)
    Firecrawl's full-page link list is the fallback."""
    try:
        from scrapling.fetchers import Fetcher

        page = Fetcher.get(url, timeout=30, stealthy_headers=True)
        hrefs = [str(h) for h in page.css("a::attr(href)").getall()]
        out = []
        for h in hrefs:
            h = h.strip()
            if not h or h.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            out.append(urljoin(url, h))
        if out:
            return out
    except Exception:  # noqa: BLE001 — fall through to Firecrawl
        pass
    data, _ = _firecrawl_post({"url": url, "formats": ["links"], "onlyMainContent": False, "waitFor": WAIT_FOR_MS})
    links = (data or {}).get("links") or []
    return [l.get("href", l) if isinstance(l, dict) else l for l in links]


def discover_pages(website, skip_urls, max_pages):
    """Re-find a business's pricing pages the way web_enrich.py originally did
    (nav-keyword links, then common paths, then Firecrawl's /map), but wider: the
    original stopped at 3 pages per business, which is why a catalog like Charlotte
    Party Rentals' /inventory/tents/ was never stored."""
    if not website or is_excluded(website):
        return []
    cands = find_pricing_links(website, fetch_home_links(website), max_pages * 2)
    if len(cands) < 3:
        cands += [urljoin(website, p) for p in COMMON_PATH_GUESSES[:6]]
    cands += firecrawl_map(website, MAP_SEARCH_QUERY, limit=8)
    out, seen = [], set(skip_urls) | {website, website.rstrip("/")}
    for u in cands:
        if u in seen or is_excluded(u) or "sitemap" in u.lower():
            continue
        seen.add(u)
        out.append(u)
    return out[:max_pages + 2]


def select_listings(conn):
    """Exactly the set export_json.py publishes (same SQL, same name exclusions)."""
    rows = conn.execute(
        """
        SELECT l.id, l.raw_listing_id, l.name FROM listings l
        JOIN raw_listings rl ON l.raw_listing_id = rl.id
        JOIN target_cities tc ON rl.target_city_id = tc.id
        WHERE l.address IS NOT NULL AND rl.geo_status = 'confirmed'
        AND EXISTS (SELECT 1 FROM listing_pricing lp WHERE lp.listing_id = l.id)
        ORDER BY l.id
        """
    ).fetchall()
    return [r for r in rows if not any(k in r[2].lower() for k in NAME_EXCLUDE_KEYWORDS)]


def refresh_listing(listing_id, raw_id, name, args):
    conn = sqlite3.connect(DB_PATH)  # own connection: listings are processed in threads
    try:
        return _refresh_listing(conn, listing_id, raw_id, name, args)
    finally:
        conn.close()


def _refresh_listing(conn, listing_id, raw_id, name, args):
    """Phase 1 for one listing: fetch, verify, discover. No LLM here (see
    llm_reextract): that step is slow and flaky, and used to be able to stall the
    whole pass. Returns a JSON-safe result; page texts needed later ride along in
    result["store_pages"] (persisted) and result["_llm_pending"] (memory only)."""
    pages = conn.execute(
        "SELECT id, url, page_type, markdown FROM scraped_pages WHERE raw_listing_id = ?", (raw_id,)
    ).fetchall()
    stored = {}  # url -> (page_type, stored_md, stored_norm)
    for _pid, url, ptype, md in pages:
        if url not in stored:
            stored[url] = (ptype, md or "", norm(md or ""))

    rows = [
        dict(id=r[0], item_type=r[1], price_low=r[2], price_high=r[3], unit=r[4], snippet=r[5])
        for r in conn.execute(
            "SELECT id, item_type, price_low, price_high, unit, source_snippet FROM listing_pricing WHERE listing_id = ?",
            (listing_id,),
        )
    ]

    # Which stored page did each row come from? (source_url in the DB is just the
    # homepage, so locate the snippet in the stored page text instead.)
    for r in rows:
        sn = norm(r["snippet"])
        r["source"] = None
        if len(sn) >= 6:
            for url, (_, _, snorm) in stored.items():
                if sn in snorm:
                    r["source"] = url
                    break

    def _fetch(url):
        return fetch_page(url, args.engine, dollar_count(stored[url][1]))

    fresh = {}
    if stored:
        with ThreadPoolExecutor(max_workers=min(args.workers, len(stored))) as ex:
            for res in ex.map(_fetch, list(stored)):
                fresh[res["url"]] = res
    ok_pages = {u: f for u, f in fresh.items() if f["ok"]}
    priced_ok = {u: f for u, f in ok_pages.items() if dollar_count(f["text"]) > 0}
    all_hay = norm("\n\n".join(f["text"] for f in ok_pages.values()))

    result = {
        "listing_id": listing_id, "name": name, "raw_id": raw_id,
        "pages": [
            {"url": u, "engine": f["engine"], "ok": f["ok"], "chars": len(f["text"]),
             "dollars": dollar_count(f["text"]), "note": f["note"][:160]}
            for u, f in fresh.items()
        ],
        "discovered": [], "rows": [], "new_items": [], "llm": None, "store_pages": [],
    }

    # First pass: deterministic verification against each row's own source page.
    pending = []
    for r in rows:
        src = r["source"]
        if src is not None:
            page = fresh.get(src)
            if not page or not page["ok"] or dollar_count(page["text"]) == 0:
                verdict, detail = UNVERIFIABLE, {"reason": "source page unreachable or rendered no prices"}
            else:
                verdict, detail = verify_row(r, norm(page["text"]))
        else:
            if not priced_ok:
                verdict, detail = UNLOCATED, {"reason": "no stored page with prices could be fetched"}
            else:
                verdict, detail = verify_row(r, all_hay)
                if verdict == MISSING:
                    # We don't know which page this row came from, so a failed
                    # search proves nothing yet: leave it for discovery.
                    verdict, detail = UNLOCATED, {"reason": "snippet not on any stored page; searched stored pages only"}
        r.update(verdict=verdict, detail=detail)
        if verdict == MISSING:
            pending.append(r)

    # Discovery: re-find the pricing pages for rows whose source we can't identify.
    unlocated = [r for r in rows if r["verdict"] == UNLOCATED]
    if unlocated and not args.no_discovery:
        website = conn.execute("SELECT website FROM listings WHERE id = ?", (listing_id,)).fetchone()[0]
        urls = discover_pages(website, set(fresh), args.max_discovery_pages)
        discovered = {}
        if urls:
            with ThreadPoolExecutor(max_workers=min(args.workers, len(urls))) as ex:
                for res in ex.map(lambda u: fetch_page(u, args.engine, 0), urls):
                    discovered[res["url"]] = res
        disc_ok = {u: f for u, f in discovered.items() if f["ok"]}
        # How much of the business's site did we actually read, and does it show
        # ANY dollar figure? Zero dollars across several substantial pages is the
        # strong signal that the business no longer publishes prices (Charlotte
        # Party Rentals went quote-only) or never did (RentMeUSA's extracted
        # "prices" were invented). A couple of near-empty pages proves nothing.
        read_pages = list(ok_pages.values()) + list(disc_ok.values())
        site_dollars = sum(dollar_count(f["text"]) for f in read_pages)
        substantial = sum(1 for f in read_pages if len(f["text"]) >= 1000)
        for r in unlocated:
            for u, f in disc_ok.items():
                v, _d = verify_row(r, norm(f["text"]))
                if v in CONFIRMED:
                    r.update(verdict=v, detail={"found_on": u}, source=u)
                    break
            else:
                r["detail"] = {
                    "reason": "not found on stored pages or on re-discovered pages",
                    "site_dollars": site_dollars,
                    "substantial_pages": substantial,
                    "pages_searched": len(ok_pages) + len(disc_ok),
                    "discovered_urls": list(disc_ok)[:8],
                }
        result["discovered"] = [
            {"url": u, "engine": f["engine"], "ok": f["ok"], "chars": len(f["text"]),
             "dollars": dollar_count(f["text"]), "note": f["note"][:120]}
            for u, f in discovered.items()
        ]
        # Keep the re-discovered pages that confirmed rows, so next month those rows
        # have a known source page instead of being UNLOCATED again.
        for u in {r["source"] for r in unlocated if r["verdict"] in CONFIRMED and r["source"]}:
            if u in disc_ok:
                result["store_pages"].append(
                    {"url": u, "page_type": "pricing_refresh", "text": disc_ok[u]["text"], "mode": "insert"}
                )

    if pending and priced_ok and not args.no_llm:
        result["_llm_pending"] = {
            "rows": pending,
            "pages": [(stored[u][0] or "page", f["text"], u) for u, f in priced_ok.items()],
            "all_hay": all_hay,
        }

    for r in rows:
        result["rows"].append(
            {"id": r["id"], "item_type": r["item_type"], "price_low": r["price_low"], "price_high": r["price_high"],
             "unit": r["unit"], "snippet": r["snippet"], "source": r["source"], "verdict": r["verdict"],
             "detail": r["detail"]}
        )
    return result


def llm_reextract(result, pend):
    """Phase 2 for one listing: ask the extractor what the fresh pages say about the
    rows we could not confirm deterministically, and accept only candidates that
    pass the anti-hallucination gate (same checks as validate_pricing.py, plus the
    snippet must appear verbatim in the FRESH content)."""
    rows_by_id = {r["id"]: r for r in result["rows"]}
    content = build_content([(pt, text) for pt, text, _u in pend["pages"]])
    extracted, model = extract(content)
    all_hay = pend["all_hay"]
    cands = [c for c in extracted.get("pricing_items", []) if candidate_passes_gate(c, all_hay)]
    result["llm"] = {"model": model, "extracted": len(extracted.get("pricing_items", [])), "passed_gate": len(cands)}
    used = set()
    for pr in pend["rows"]:
        r = rows_by_id[pr["id"]]
        idx, why = match_candidate(r, cands, used)
        if idx is None:
            continue
        used.add(idx)
        c = cands[idx]
        same = abs((c["price_low"] or 0) - (r["price_low"] or 0)) <= 0.01 and (
            (c.get("price_high") or None) == (r["price_high"] or None)
        )
        if same:
            r.update(verdict=CONFIRMED_LLM, detail={"match": why})
        else:
            r.update(
                verdict=CHANGED,
                detail={"match": why, "new": {
                    "price_low": c["price_low"], "price_high": c.get("price_high"),
                    "unit": c.get("unit") or r["unit"], "source_snippet": c["source_snippet"],
                    "item_type": c.get("item_type")}},
            )
            # Refresh the stored source page too, so the new snippet is locatable next time.
            src = r.get("source")
            for pt, text, u in pend["pages"]:
                if u == src and not any(sp["url"] == u for sp in result["store_pages"]):
                    result["store_pages"].append({"url": u, "page_type": pt, "text": text, "mode": "replace"})
    known = {type_key(r["item_type"]) for r in result["rows"]}
    for i, c in enumerate(cands):
        if i not in used and type_key(c.get("item_type")) not in known:
            result["new_items"].append({k: c.get(k) for k in ("item_type", "price_low", "price_high", "unit", "source_snippet")})


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------
def ensure_tables(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL, item_type TEXT NOT NULL,
            event TEXT NOT NULL, old_price_low REAL, old_price_high REAL,
            new_price_low REAL, new_price_high REAL, unit TEXT, reason TEXT, recorded_at TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS refresh_runs (
            id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, mode TEXT NOT NULL, summary_json TEXT)"""
    )


def unsupported_by_site(row):
    """True only when the evidence is strong: after re-discovery, the business's
    pages (2+ substantial ones) show no dollar figure at all. A price merely
    "not found" on a site that does show other prices stays for human review."""
    d = row.get("detail") or {}
    return d.get("site_dollars") == 0 and d.get("substantial_pages", 0) >= 2


def apply_result(conn, res, now, allow_removals, add_new, remove_unlocated=False):
    counts = {"redated": 0, "changed": 0, "removed": 0, "added": 0}
    lid = res["listing_id"]
    for r in res["rows"]:
        v = r["verdict"]
        if v in CONFIRMED:
            conn.execute(
                "UPDATE listing_pricing SET last_checked = ?, source_url = COALESCE(?, source_url) WHERE id = ?",
                (now, r["source"], r["id"]),
            )
            counts["redated"] += 1
        elif v == CHANGED:
            new = r["detail"]["new"]
            conn.execute(
                "INSERT INTO price_history (listing_id, item_type, event, old_price_low, old_price_high, new_price_low, new_price_high, unit, reason, recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (lid, r["item_type"], "changed", r["price_low"], r["price_high"], new["price_low"], new["price_high"],
                 new["unit"], f"refresh: {r['detail']['match']}", now),
            )
            conn.execute(
                "UPDATE listing_pricing SET price_low=?, price_high=?, unit=?, source_snippet=?, last_checked=?, extracted_by_model=? WHERE id=?",
                (new["price_low"], new["price_high"], new["unit"], new["source_snippet"], now,
                 f"refresh/{res['llm']['model']}", r["id"]),
            )
            counts["changed"] += 1
        elif v == UNLOCATED and remove_unlocated and unsupported_by_site(r):
            conn.execute(
                "INSERT INTO price_history (listing_id, item_type, event, old_price_low, old_price_high, unit, reason, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                (lid, r["item_type"], "removed", r["price_low"], r["price_high"], r["unit"],
                 "refresh: snippet is on no stored page and the business's pages (2+ substantial) show no dollar figure at all - unsupported by the business's own site", now),
            )
            conn.execute("DELETE FROM listing_pricing WHERE id = ?", (r["id"],))
            counts["removed"] += 1
        elif v == MISSING and allow_removals:
            conn.execute(
                "INSERT INTO price_history (listing_id, item_type, event, old_price_low, old_price_high, unit, reason, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                (lid, r["item_type"], "removed", r["price_low"], r["price_high"], r["unit"],
                 "refresh: source page loaded but item/price no longer present", now),
            )
            conn.execute("DELETE FROM listing_pricing WHERE id = ?", (r["id"],))
            counts["removed"] += 1
    if add_new:
        for it in res["new_items"]:
            conn.execute(
                "INSERT INTO listing_pricing (listing_id, item_type, price_low, price_high, unit, source_snippet, source_url, extracted_by_model, last_checked) VALUES (?,?,?,?,?,?,?,?,?)",
                (lid, it["item_type"], it["price_low"], it["price_high"], it.get("unit"), it["source_snippet"], None,
                 f"refresh/{res['llm']['model']}", now),
            )
            conn.execute(
                "INSERT INTO price_history (listing_id, item_type, event, new_price_low, new_price_high, unit, reason, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                (lid, it["item_type"], "added", it["price_low"], it["price_high"], it.get("unit"), "refresh: new item on source page", now),
            )
            counts["added"] += 1
    for sp in res.get("store_pages", []):
        if sp["mode"] == "insert":
            conn.execute(
                "INSERT INTO scraped_pages (raw_listing_id, url, page_type, markdown, scraped_at) VALUES (?,?,?,?,?)",
                (res["raw_id"], sp["url"], sp["page_type"], sp["text"], now),
            )
        else:
            conn.execute(
                "UPDATE scraped_pages SET markdown = ?, scraped_at = ? WHERE raw_listing_id = ? AND url = ?",
                (sp["text"], now, res["raw_id"], sp["url"]),
            )
    conn.commit()
    return counts


# ---------------------------------------------------------------------------
def load_run(path):
    out = {}
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                out[obj["listing_id"]] = obj  # later lines override earlier ones
    return out


def append_run(path, res):
    clean = {k: v for k, v in res.items() if not k.startswith("_")}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(clean) + "\n")


def row_summary(res):
    by = {}
    for r in res["rows"]:
        by[r["verdict"]] = by.get(r["verdict"], 0) + 1
    return by


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=5, help="listings to process (ignored with --all)")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--listing", help="only listings whose name contains this text")
    ap.add_argument("--apply", action="store_true", help="write verified updates to the DB (default: dry run)")
    ap.add_argument("--allow-removals", action="store_true", help="with --apply: delete rows whose source page loaded but no longer has the item")
    ap.add_argument("--add-new", action="store_true", help="with --apply: add newly found items that pass the gate")
    ap.add_argument("--remove-unlocated", action="store_true", help="with --apply: delete UNLOCATED rows only where the business's pages (2+ substantial) show no dollar figure at all")
    ap.add_argument("--no-discovery", action="store_true", help="skip re-discovering pricing pages for rows with an unknown source")
    ap.add_argument("--max-discovery-pages", type=int, default=8)
    ap.add_argument("--no-llm", action="store_true", help="deterministic verification only, no re-extraction")
    ap.add_argument("--llm-minutes", type=float, default=25, help="time budget for the (slow) re-extraction phase")
    ap.add_argument("--engine", choices=["auto", "both", "firecrawl", "scrapling"], default="auto")
    ap.add_argument("--parallel", type=int, default=4, help="listings processed at once")
    ap.add_argument("--workers", type=int, default=5, help="parallel page fetches per listing")
    ap.add_argument("--listing-timeout-min", type=float, default=12, help="give up waiting on the whole pass after this long")
    ap.add_argument("--resume", help="a run-*.jsonl file: skip listings already finished in it (and keep appending to it)")
    ap.add_argument("--apply-from-report", help="skip fetching entirely; apply exactly the verdicts already saved in this run-*.jsonl (still needs --apply)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)

    if args.apply_from_report:
        if not args.apply:
            print("--apply-from-report needs --apply too (it only ever writes what --apply allows).")
            return
        results = load_run(Path(args.apply_from_report))
        print(f"[APPLY FROM REPORT] {len(results)} listing(s) loaded from {args.apply_from_report}", flush=True)
        backup = DB_PATH.with_name(f"directory-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup)
        print(f"  DB backed up to {backup.name}", flush=True)
        ensure_tables(conn)
        now = datetime.now(timezone.utc).isoformat()
        totals = {}
        bump = lambda k, n=1: totals.__setitem__(k, totals.get(k, 0) + n)  # noqa: E731
        for res in results.values():
            c = apply_result(conn, res, now, args.allow_removals, args.add_new, args.remove_unlocated)
            for k, v in c.items():
                bump("applied_" + k, v)
            for r in res["rows"]:
                bump(r["verdict"])
            bump("rows", len(res["rows"]))
        conn.execute("INSERT INTO refresh_runs (started_at, mode, summary_json) VALUES (?,?,?)", (now, "APPLY-FROM-REPORT", json.dumps(totals)))
        conn.commit()
        print(f"applied: {{{', '.join(f'{k[8:]}={v}' for k, v in totals.items() if k.startswith('applied_'))}}}")
        print(f"rows by verdict: {{{', '.join(f'{k}={v}' for k, v in totals.items() if k in (CONFIRMED_VERBATIM, CONFIRMED_NEAR, CONFIRMED_LLM, CHANGED, MISSING, UNLOCATED, UNVERIFIABLE))}}}")
        conn.close()
        return

    listings = select_listings(conn)
    if args.listing:
        listings = [l for l in listings if args.listing.lower() in l[2].lower()]
    elif not args.all:
        listings = listings[args.offset: args.offset + args.limit]
    mode = "APPLY" if args.apply else "DRY RUN"

    REPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_path = Path(args.resume) if args.resume else REPORT_DIR / f"run-{stamp}.jsonl"
    done = load_run(run_path)
    print(f"[{mode}] {len(listings)} listing(s) | engine={args.engine} llm={'off' if args.no_llm else 'deferred'} | run file: {run_path.name} ({len(done)} already done)", flush=True)

    now = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    results = dict(done)
    todo = [l for l in listings if l[0] not in done]
    n_done = len(listings) - len(todo)
    llm_pending = {}

    # ---- phase 1: fetch + verify + discover, in parallel, saved as each listing finishes
    pool = ThreadPoolExecutor(max_workers=max(1, args.parallel))
    futs = {pool.submit(refresh_listing, lid, raw_id, name, args): (lid, name) for lid, raw_id, name in todo}
    try:
        for fut in as_completed(futs, timeout=args.listing_timeout_min * 60 * max(1, len(todo) // max(1, args.parallel) + 1)):
            lid, name = futs[fut]
            n_done += 1
            try:
                res = fut.result()
            except Exception as e:  # noqa: BLE001 — one bad listing must not abort the pass
                print(f"  [{n_done}/{len(listings)}] ERROR {name.encode('ascii', 'replace').decode()[:40]}: {type(e).__name__} {str(e)[:100]}", flush=True)
                continue
            if "_llm_pending" in res:
                llm_pending[lid] = res["_llm_pending"]
            results[lid] = res
            append_run(run_path, res)
            by = row_summary(res)
            unreachable = sum(1 for p in res["pages"] if not p["ok"])
            engines = sorted({p["engine"] for p in res["pages"] if p["ok"] and p["engine"]})
            nm = name.encode("ascii", "replace").decode()[:42]
            print(f"  [{n_done}/{len(listings)}] {nm:<42} pages {len(res['pages'])-unreachable}/{len(res['pages'])} via {'+'.join(engines) or '-'} | {', '.join(f'{k}={v}' for k, v in sorted(by.items())) or 'no rows'}", flush=True)
    except Exception as e:  # noqa: BLE001 — e.g. the overall timeout; keep what we have
        print(f"  !! phase 1 stopped early: {type(e).__name__} {e}", flush=True)
    pool.shutdown(wait=False, cancel_futures=True)

    # ---- phase 2: slow re-extraction, only for rows we couldn't confirm deterministically
    if llm_pending and not args.no_llm:
        deadline = time.time() + args.llm_minutes * 60
        fails = 0
        print(f"\n[LLM phase] {len(llm_pending)} listing(s) with unconfirmed rows, budget {args.llm_minutes:.0f} min", flush=True)
        for lid, pend in llm_pending.items():
            if time.time() > deadline or fails >= 4:
                print("  [LLM phase] stopping (budget used or repeated failures); remaining rows stay 'missing'", flush=True)
                break
            res = results[lid]
            try:
                llm_reextract(res, pend)
                fails = 0
            except Exception as e:  # noqa: BLE001
                fails += 1
                res["llm"] = {"error": str(e)[:160]}
                print(f"  [LLM] {res['name'].encode('ascii', 'replace').decode()[:40]}: failed ({str(e)[:70]})", flush=True)
            else:
                by = row_summary(res)
                print(f"  [LLM] {res['name'].encode('ascii', 'replace').decode()[:40]:<40} -> {', '.join(f'{k}={v}' for k, v in sorted(by.items()))}", flush=True)
            append_run(run_path, res)  # later line overrides the phase-1 line

    # ---- phase 3: apply (DB writes), only with --apply
    totals = {}
    bump = lambda k, n=1: totals.__setitem__(k, totals.get(k, 0) + n)  # noqa: E731
    if args.apply:
        backup = DB_PATH.with_name(f"directory-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
        shutil.copy2(DB_PATH, backup)
        print(f"\n  DB backed up to {backup.name}", flush=True)
        ensure_tables(conn)
        for res in results.values():
            for k, v in apply_result(conn, res, now, args.allow_removals, args.add_new, args.remove_unlocated).items():
                bump("applied_" + k, v)

    for res in results.values():
        for r in res["rows"]:
            bump(r["verdict"])
        bump("rows", len(res["rows"]))
        bump("new_items_found", len(res["new_items"]))
        bump("pages", len(res["pages"]))
        bump("pages_unreachable", sum(1 for p in res["pages"] if not p["ok"]))

    path = REPORT_DIR / f"refresh-{'apply' if args.apply else 'dry'}-{stamp}.json"
    slim = [{k: v for k, v in r.items() if k != "store_pages"} for r in results.values()]
    path.write_text(json.dumps({"mode": mode, "started": now, "totals": totals, "listings": slim}, indent=1), encoding="utf-8")
    if args.apply:
        conn.execute("INSERT INTO refresh_runs (started_at, mode, summary_json) VALUES (?,?,?)", (now, mode, json.dumps(totals)))
        conn.commit()

    rows = totals.get("rows", 0) or 1
    conf = sum(totals.get(k, 0) for k in CONFIRMED)
    print(f"\n=== {mode} done in {time.time() - t0:.0f}s ===")
    print(f"rows: {totals.get('rows', 0)} | confirmed {conf} ({100 * conf // rows}%) | changed {totals.get(CHANGED, 0)} | missing {totals.get(MISSING, 0)} | unlocated {totals.get(UNLOCATED, 0)} | unverifiable {totals.get(UNVERIFIABLE, 0)}")
    print(f"pages: {totals.get('pages', 0)} fetched-ok {totals.get('pages', 0) - totals.get('pages_unreachable', 0)} | new items found (not added unless --add-new): {totals.get('new_items_found', 0)}")
    if args.apply:
        print(f"applied: {{{', '.join(f'{k[8:]}={v}' for k, v in totals.items() if k.startswith('applied_'))}}}")
    print(f"report: {path}\nrun file (resumable): {run_path}", flush=True)
    conn.close()
    os._exit(0)  # don't wait on any straggler worker threads


if __name__ == "__main__":
    main()
