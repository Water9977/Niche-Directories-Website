# Niche Local Directory

A from-scratch, bootstrapped ($30 total budget) niche local directory website built to rank on Google and earn via lead-referral fees, featured listings, and display ads.

**Read [architecture.md](architecture.md) first.** It is the living source of truth for this project — every decision made, every decision pending, current build status, and the full plan. This README is just an entry point; architecture.md is authoritative and is updated every session.

## Current status

**Live in production at [eventrentalcosts.com](https://eventrentalcosts.com)** — 112 verified listings across 10 published metro pages (Charlotte, Raleigh–Durham, Indianapolis, Columbus, Greensboro–Winston-Salem, Richmond, Jacksonville, Greenville, Charleston, Knoxville), each with real per-item pricing scraped from the businesses' own websites and validated against source text. Google Search Console + Bing Webmaster Tools submitted, GA4 wired, lead-capture form live, backlink outreach sent. See architecture.md's changelog for the full session-by-session history.

## Niche

Party/event equipment rental directory (tents, tables, chairs) — US, city-by-city. Full validation scorecard, rejected alternatives, and reasoning are in architecture.md §5 and §5b.

## The moat

Real, verified per-day rental pricing collected directly from local rental companies — data Google Maps listings and quote-only marketplaces don't show. See architecture.md §1 for the full business thesis and honest risk assessment.

## Tech stack

Astro 5 (static output) + Python/SQLite data pipeline (build-time only, `pipeline/`) + Cloudflare Workers static assets hosting. Data: Apify Google Maps ingest → geo validation → Firecrawl website scraping → LLM pricing extraction (NVIDIA NIM/OpenRouter chain) → snippet-level price validation → JSON export straight into the site build. Full stack and rationale in architecture.md §4.

## Working rules

- `architecture.md` is updated at the end of every session — changelog, decision log, open questions.
- Real data only. No fabricated place IDs, no invented ratings, no unverified negative claims about real businesses.
- Hard budget cap: ~$30 total, tracked in architecture.md's budget ledger.
- Secrets live in `.env` only, never committed (see `.env.example` for the required keys).

## Setup

```
cp .env.example .env
# fill in real keys — see architecture.md §13 Security Notes for what's needed and why
```
