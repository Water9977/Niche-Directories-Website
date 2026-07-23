"""Extracts real structured pricing + three-state fields from scraped_pages
into listings and listing_pricing, via OpenRouter's free-tier models.

Hard rule: never infer. If the text doesn't explicitly state a price or a
yes/no fact, the field stays empty/'unknown' — an absent claim is not the
same as a negative claim about a real business.

Provider note: Google's Gemini free tier caps at a hard 20 requests/day
PER MODEL (confirmed via AI Studio dashboard 2026-07-12) — burned through
that on gemini-2.5-flash and gemini-2.5-flash-lite mid-session. Switched to
OpenRouter's free models (20 RPM / 50 RPD account-wide, not per-model),
which comfortably covers our ~200-business volume. Tries a short list of
free models in order since individual free-tier upstream providers on
OpenRouter sometimes return transient 429s independent of our own quota.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

# (provider, model) in priority order. NVIDIA NIM tested fast/reliable (<1s) on the
# 8B model; OpenRouter's free tier is shared/congested (upstream providers return
# transient 429s independent of our own account quota) so it's the fallback.
# The two OpenRouter free slugs below were replaced 2026-07-23: the originals
# (meta-llama/llama-3.3-70b-instruct:free, qwen/qwen3-next-80b-a3b-instruct:free)
# 404'd on every single call this whole session -- confirmed via OpenRouter's own
# free-models catalog that both were deprecated/removed, not a transient outage.
PROVIDER_CHAIN = [
    ("nvidia", "meta/llama-3.1-8b-instruct"),
    ("nvidia", "meta/llama-3.3-70b-instruct"),
    ("openrouter", "openai/gpt-oss-20b:free"),
    ("openrouter", "nvidia/nemotron-3-nano-30b-a3b:free"),
]
DB_PATH = Path(__file__).parent / "directory.db"

JSON_SHAPE_INSTRUCTIONS = """Respond with ONLY a single JSON object, no markdown fences, \
no commentary, matching exactly this shape:
{
  "pricing_items": [
    {"item_type": "string, e.g. tent_10x10 / chair_folding / table_round_60in / delivery_fee / deposit",
     "price_low": number, "price_high": number or null, "unit": "string, e.g. 'per day'/'per event'/'flat'/'each'",
     "source_snippet": "exact quoted text the price came from"}
  ],
  "delivery_available": "yes" | "no" | "unknown",
  "setup_included": "yes" | "no" | "unknown",
  "weekend_surcharge": "yes" | "no" | "unknown"
}"""

PROMPT = """You are extracting REAL pricing data for a party/event equipment rental \
business (tents, tables, chairs) from its own website content below. This data will \
be published on a comparison directory, so accuracy matters more than completeness.

STRICT RULES:
- Only extract a price if a real dollar figure is explicitly stated in the text. Never \
estimate, infer, or guess a price from context.
- Every pricing_items entry MUST include the exact source_snippet text it came from.
- For delivery_available / setup_included / weekend_surcharge: only say "yes" or "no" \
if the text explicitly states it. If the page doesn't mention it at all, you MUST \
answer "unknown" — do not default to "no". An absent claim is not a negative claim.
- If there is no real pricing anywhere in the text, return an empty pricing_items array. \
Do not fabricate a plausible-sounding price to fill the field.

{shape}

WEBSITE CONTENT:
{content}
"""


def call_model(provider, model, content):
    prompt_text = PROMPT.format(shape=JSON_SHAPE_INSTRUCTIONS, content=content[:40000])
    if provider == "nvidia":
        endpoint, key = NVIDIA_ENDPOINT, NVIDIA_KEY
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0,
            "max_tokens": 6000,
        }
    else:
        endpoint, key = OPENROUTER_ENDPOINT, OPENROUTER_KEY
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

    resp = requests.post(endpoint, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
    if resp.status_code == 429:
        try:
            retry_after = resp.json().get("error", {}).get("metadata", {}).get("retry_after_seconds", 5)
        except Exception:
            retry_after = 5
        return None, retry_after
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    if choice.get("finish_reason") == "error":
        raise RuntimeError(f"provider error: {choice.get('error')}")
    text = choice["message"]["content"].strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text), None


def extract(content):
    for provider, model in PROVIDER_CHAIN:
        for attempt in range(2):
            try:
                result, retry_after = call_model(provider, model, content)
            except json.JSONDecodeError as e:
                # A malformed JSON generation is a one-off sampling glitch, not a
                # broken model/endpoint (found live 2026-07-23: the exact same
                # ACC Rental content parsed fine on a fresh call). Worth a real
                # retry on the SAME model before giving up on it -- the previous
                # code treated this identically to a dead endpoint and jumped
                # straight to the fallback chain, most of which is unreliable
                # (70B times out, the free OpenRouter model IDs below 404).
                print(f"    {provider}/{model} produced malformed JSON ({e}), retrying...")
                continue
            except (RuntimeError, KeyError, requests.exceptions.RequestException) as e:
                print(f"    {provider}/{model} failed ({e}), trying next...")
                break
            if result is not None:
                return result, f"{provider}/{model}"
            print(f"    {provider}/{model} rate-limited, waiting {retry_after}s...")
            time.sleep(retry_after + 1)
        # exhausted retries for this provider/model, move to next
    raise RuntimeError("all providers failed or rate-limited")


def upsert_listing(conn, raw_id, result, model_used):
    row = conn.execute("SELECT * FROM raw_listings WHERE id=?", (raw_id,)).fetchone()
    cols = [d[0] for d in conn.execute("SELECT * FROM raw_listings WHERE id=?", (raw_id,)).description]
    r = dict(zip(cols, row))
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO listings (
            raw_listing_id, name, address, city, state, postal_code, lat, lng,
            phone, website, rating, review_count, category, hours_json,
            delivery_available, setup_included, weekend_surcharge, last_enriched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(raw_listing_id) DO UPDATE SET
            delivery_available=excluded.delivery_available,
            setup_included=excluded.setup_included,
            weekend_surcharge=excluded.weekend_surcharge,
            last_enriched_at=excluded.last_enriched_at
        """,
        (
            raw_id, r["name"], r["address"], r["city"], r["state"], r["postal_code"],
            r["lat"], r["lng"], r["phone"], r["website"], r["rating"], r["review_count"],
            r["category"], r["hours_json"],
            result["delivery_available"], result["setup_included"], result["weekend_surcharge"],
            now,
        ),
    )
    listing_id = conn.execute("SELECT id FROM listings WHERE raw_listing_id=?", (raw_id,)).fetchone()[0]

    conn.execute("DELETE FROM listing_pricing WHERE listing_id=?", (listing_id,))
    for item in result.get("pricing_items", []):
        conn.execute(
            """
            INSERT INTO listing_pricing (
                listing_id, item_type, price_low, price_high, unit,
                source_snippet, source_url, extracted_by_model, last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing_id, item["item_type"], item.get("price_low"), item.get("price_high"),
                item.get("unit"), item.get("source_snippet"), r["website"], model_used, now,
            ),
        )
    conn.commit()
    return listing_id, len(result.get("pricing_items", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    raw_ids = conn.execute(
        """
        SELECT DISTINCT raw_listing_id FROM scraped_pages
        WHERE raw_listing_id NOT IN (SELECT raw_listing_id FROM listings)
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    print(f"Extracting {len(raw_ids)} businesses via {PROVIDER_CHAIN[0][0]}/{PROVIDER_CHAIN[0][1]} (+ fallbacks)...")
    with_pricing, without_pricing, failed = 0, 0, 0

    for (raw_id,) in raw_ids:
        name = conn.execute("SELECT name FROM raw_listings WHERE id=?", (raw_id,)).fetchone()[0]
        pages = conn.execute(
            "SELECT page_type, markdown FROM scraped_pages WHERE raw_listing_id=?", (raw_id,)
        ).fetchall()
        content = "\n\n---\n\n".join(f"[{ptype}]\n{md}" for ptype, md in pages)

        try:
            result, model_used = extract(content)
        except Exception as e:
            print(f"  FAIL: {name} -> {e}")
            failed += 1
            continue

        listing_id, n_items = upsert_listing(conn, raw_id, result, model_used)
        if n_items > 0:
            print(f"  OK: {name} ({model_used}) -> {n_items} real pricing item(s) extracted")
            with_pricing += 1
        else:
            print(f"  OK: {name} ({model_used}) -> no real pricing found (listing created, no moat data)")
            without_pricing += 1
        time.sleep(3)

    print(f"\nDone: {with_pricing} with real pricing, {without_pricing} without, {failed} failed.")
    conn.close()


if __name__ == "__main__":
    main()
