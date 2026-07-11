# Niche Local Directory — architecture.md
_Living source of truth. Update every session. Never let this drift from actual code._

---

## Changelog (newest first)

### 2026-07-12 — Session 3: domain purchased
- Human bought **eventrentalcosts.com** for $9. First real spend — budget now $9/$30 used, $21 left.
- Site identity now fixed: eventrentalcosts.com, flagship city Charlotte NC, niche party/event equipment rental (tents/tables/chairs).

### 2026-07-11 — Session 2: niche PIVOT — pickleball rejected, party/event rental locked in
- Deep multi-agent verification (WebSearch + Firecrawl, 2 rounds, 7 agents total) found pickleball court builders has a real incumbent: **PickleballCosts.com** already runs 50-state + city pricing, a cost calculator, and a contractor directory with a "3 free quotes" lead-gen funnel — likely templated/unverified data (same publisher family as sportsvenuecalculator.com), but a real live competitor, not empty space. Human chose to pivot rather than build against it.
- Human supplied 5 alternative candidates. Verified all 5 independently (parallel agents, Firecrawl + WebSearch, not taken on faith):
  - **Dog boarding/daycare pricing** — REJECT. Rover.com already runs live per-city, per-sitter transactional pricing pages + a parallel cost-guide blog for hundreds of cities. Same product, already at marketplace scale.
  - **RV park wifi/cell-signal ratings** — REJECT, hard fail. Campendium (70k+ campgrounds, owned by Roadtrippers) and RV LIFE have run crowdsourced per-carrier signal bars + speed tests for ~a decade. Independent of competition, the moat itself is unbootstrappable: it requires an existing user base to crowdsource readings, which a zero-audience $30 site cannot generate. This is the same "RV parks" the original brief already flagged as a prior candidate to not just default back to — confirmed correct to avoid.
  - **Specialty home inspectors (mold/sewer scope/thermal)** — REJECT. InterNACHI runs a fully programmatic certified-inspector directory with full city coverage (confirmed 47 inspectors returned for one metro). Angi/HomeAdvisor own the cost-guide layer. Also YMYL-adjacent (major property-purchase decision + mold health exposure) — three fronts at once.
  - **Plasma donation payout rates** — REJECT. discoverplasma.com already crowdsources real per-center pay rates (1,256 centers, 46 states) and runs a $100/month donor incentive to keep data fresh — exactly the infrastructure this moat needs, unreplicable at this budget. Real per-visit rate data isn't scrapable from company sites (only vague "up to $X" marketing figures); it only exists via community crowdsourcing.
  - **Tool & party equipment rental** — SPLIT. Heavy equipment (bobcat/excavator) REJECT — BigRentz and DOZR are national marketplaces already aggregating real city-level daily pricing; Home Depot/Sunbelt/United Rentals/Herc own the branded SERP. **Party/event rental (tents/tables/chairs) SURVIVES** — fragmented local operators (Century Party Rental, e-Tent Rent, Avalon Event Rentals, etc.), no dominant incumbent for pricing-intent queries, real itemized per-day pricing confirmed directly scrapable off individual company sites, decent ticket ($1,500-6,000/wedding).
- **Niche locked: party/event equipment rental (tents, tables, chairs — NOT heavy construction equipment).** Scope is intentionally narrower than the original "Tool & Party Equipment" pitch; heavy equipment sub-vertical is dropped.
- Maps data source also resolved this session: **Apify `compass/crawler-google-places`** approved (Outscraper backup declined by human to keep it simple) — $1.50/1k, all required fields (real place_id, address, phone, geo, rating, reviews, category, hours), $5/mo free credit likely covers the full ingest at ~$0 net cost.
- Not yet started: DB schema, data pipeline, Astro scaffold. Still pure research/setup phase.

### 2026-07-11 — Session 1 (cont.): keys added
- Human provided EXA_API_KEY, FIRECRAWL_API_KEY, GEMINI_API_KEY (all free-tier). Written to `.env` (gitignored, verified via `git check-ignore` — not tracked).
- **LLM enrichment locked to Gemini** (free-tier key provided) — record actual model string per-row when ai_extract is built, don't hardcode.
- Remaining blocker: Maps data source pick + spend approval (§8).

### 2026-07-11 — Session 1 (cont.): niche confirmed
- Human approved **pickleball court construction/builder directory** as the niche. No longer PROPOSED.
- Next blocking item: Exa API key (optional, ask human) + Maps data source selection/approval before any spend.

### 2026-07-11 — Session 1: workspace init + niche research
- Created this file, `.gitignore`, `.env.example`. `git init` done. No remote yet (not pushed — will confirm before any push).
- Ran niche validation research (Firecrawl search) across 10 candidates. See §5 scorecard.
- **Recommendation: Pickleball court construction/builder directory.** Awaiting human sign-off (see Open Questions).
- Nothing built yet — no Astro project, no DB, no data pipeline. Pure research phase.

---

## Open Questions / Decisions Needed From Human

1. ~~Niche sign-off~~ — **DONE 2026-07-11, then PIVOTED same day.** Final: party/event equipment rental (tents/tables/chairs). See changelog for full reasoning.
2. ~~Exa API key~~ — **DONE 2026-07-11.** In `.env`, gitignored.
3. **Playwright MCP not installed.** Not needed yet (no JS-heavy scraping until data pipeline phase). Install instructions in §4 when needed.
4. ~~Maps data source~~ — **DONE 2026-07-11.** Apify `compass/crawler-google-places` approved, ~$0-5 expected spend. Not yet signed up / actually purchased — that's still a next step.
5. ~~Domain name~~ — **DONE 2026-07-12.** Purchased `eventrentalcosts.com` for $9.
6. ~~Target flagship city~~ — **DONE 2026-07-12.** Charlotte, NC confirmed. Full multi-city rollout list still to be built once flagship is validated.
7. **Reventals.com competitive risk — needs ongoing awareness, not a blocker.** It's a funded 34-metro marketplace but hides real pricing behind a quote flow — our verified-pricing moat still applies even in cities where it operates. Noted so future sessions don't re-discover this from scratch.

---

## 1. Business Thesis (see full brief for complete context)

Hyper-focused local directory in an underserved niche. Static Astro site, SEO-only distribution, monetized via lead-referral/featured listings/ads. Moat = real data Google Maps doesn't show (verified pricing, structured comparison, freshness) — not AI-summarized homepage content.

**Honest risk assessment:** ~50% of directories like this earn $0 ever. Google's 2025-2026 updates specifically target thin aggregator/directory content. 6-12 months to rank, if it ranks at all. Budget assumes total loss is the base case; treat any revenue as upside.

**Hard budget: ~$30 total.** Ledger in §13. Nothing spent yet.

---

## 2. Chosen Niche

**CONFIRMED 2026-07-11 (final, after pivot): Party/event equipment rental directory — tents, tables, chairs.**

Scope explicitly EXCLUDES heavy construction equipment (skid steers, excavators, bobcats) — that sub-vertical is already owned by BigRentz/DOZR (national rental marketplaces) and Home Depot/Sunbelt/United Rentals/Herc (major chains). Only the event-rental side (weddings, parties, corporate events) survived verification.

Search intent to target: "tent rental cost near me", "party rental price comparison [city]", "wedding tent rental cost [city]", "tables and chairs rental price [city]".

Moat: real itemized per-day pricing (tent sizes, table/chair unit prices, delivery fees, deposit policies, inventory counts) collected directly from individual local rental companies' own sites — confirmed scrapable (e.g. Century Party Rental: 10x10 tent $150, chairs $1.25-$8.50/unit). No dominant aggregator found for the pricing-intent queries; WeddingWire/TheKnot rank for broad vendor-directory queries but not itemized pricing comparison.

Pickleball court construction (previous pick, see §5 history) was rejected after finding a real incumbent (PickleballCosts.com) — full reasoning preserved in the scorecard below and in the changelog.

---

## 3. Decision Log

| Date | Decision | Options considered | Why | Reversible? |
|---|---|---|---|---|
| 2026-07-11 | Reject restroom trailer rental (prior candidate) | Was a top prior candidate | `restroomtrailerlist.com` already exists as a direct incumbent — 160 cities, "no pay-to-play" positioning, ranking on page 1 for the exact target query. Cloning an existing player with zero head start is a losing bet. | N/A (research finding) |
| 2026-07-11 | Reject fence/generator/pool/turf/dumpster/epoxy niches | 6 candidates researched | All are mature Angi/Thumbtack/HomeDepot/manufacturer-owned SERP verticals. National lead-gen giants and manufacturer sites occupy top results; a new zero-authority site cannot displace them in any realistic timeframe. | N/A |
| 2026-07-11 | Propose pickleball court construction as niche | vs. all above | High ticket ($8k-50k), fragmented regional builders, no dominant aggregator (only a generic Homeguide page + thin official USA Pickleball list), sport is in a genuine growth phase (more demand signal, less saturated content). Real Maps data (builders are local businesses) obtainable. Non-YMYL. | Reversible — no spend committed yet |
| 2026-07-11 | git init locally, no remote | — | Brief requires secrets-clean verification before any public push; too early to push. | Reversible |
| 2026-07-11 | Reject pickleball court construction (was confirmed niche) | Keep building anyway w/ differentiation vs. pivot vs. narrow scope | Deep-dive competitor agent found PickleballCosts.com already live: 50-state+city pricing, calculator, contractor directory, lead-gen funnel. Human chose to pivot rather than compete against an existing structural clone, even though its data looks templated/unverified. | Reversible — no spend committed |
| 2026-07-11 | Approve Apify `compass/crawler-google-places` as Maps data source | Apify, Outscraper, SerpAPI, official Places API, DataForSEO | Apify: $1.50/1k, all required fields incl. real place_id, $5/mo free credit likely covers full ~1,500-business ingest at ~$0 net. Cheapest option meeting full field requirement; official Places API lost its $200/mo credit in 2025 and needs 2 paid calls/business; DataForSEO has a $50 minimum deposit alone exceeding the whole project budget. Outscraper backup declined by human for simplicity. | Reversible — not yet signed up |
| 2026-07-11 | Reject dog boarding, RV park wifi, home inspectors, plasma donation, heavy-equipment rental; accept party/event rental | 5 human-supplied candidates, verified via 5 parallel research agents | Dog boarding: Rover.com already live at marketplace scale with real per-city/per-sitter pricing. RV park wifi: Campendium/RV LIFE own it at 70k+ sites for ~a decade AND the moat needs an audience we don't have — fatal regardless of competition (this was the brief's already-flagged prior candidate, confirmed correct to avoid). Home inspectors: NACHI owns the certified-directory layer city-by-city, Angi/HomeAdvisor own cost-guides, plus YMYL-adjacent risk (property purchase + mold health). Plasma donation: discoverplasma.com already crowdsources real pay data across 1,256 centers with a paid incentive program — infrastructure we can't replicate. Heavy equipment rental: BigRentz/DOZR are national marketplaces already aggregating this exact pricing; Home Depot/Sunbelt/United/Herc own the branded SERP. Party/event rental (tents/tables/chairs) was the only one with no dominant incumbent found and confirmed-scrapable real per-day pricing. | Reversible — no spend committed |
| 2026-07-11 | **FINAL niche: party/event equipment rental (tents/tables/chairs)** | vs. pickleball, vs. the 4 other rejected candidates | Only candidate across 15 total niches researched (10 in session 1 + 5 in session 2) with no dominant incumbent, real scrapable pricing data, and a bootstrappable moat at $30 budget. Smaller ticket ($1,500-6,000) than pickleball ($8k-50k) but meaningfully lower competitive risk. | Reversible until Maps data spend actually executed |
| 2026-07-12 | Reject scrape.do, keep Apify as Maps data source | Apify (already chosen) vs. scrape.do (human-flagged via a Google ad targeting Outscraper searchers) | scrape.do does have a dedicated Maps Ready-API (not just raw HTML — corrected an initial assumption) with a workable free tier, but the "20 results/call" math breaks down for a sparse niche like ours and full photo parity needs a 2nd paid call per business, likely pushing into a $29+/mo plan. Apify's actor is purpose-built for this exact city×category workflow and stays free at our volume. | Reversible, no spend either way |
| 2026-07-12 | Flag Reventals.com as a real national competitor, but confirm moat still holds | Continue with party/event rental vs. reconsider | Reventals is a funded marketplace (cart/checkout, AI chat assistant "Evie," blog content network) already live in 34 major US metros. Critically, it does NOT publish real per-item pricing — checkout shows "$0.00 estimated, final quote after request," same quote-gated pattern as Angi/WeddingWire. Our moat (real, verified, published prices) is still a genuine gap even where Reventals operates. Decision: pick an initial city Reventals does NOT cover, to avoid a direct authority fight while still proving the model, rather than abandon the niche. | Reversible |
| 2026-07-12 | Recommend Charlotte, NC (Charlotte-Concord-Gastonia metro) as flagship launch city | Checked against Reventals' 34-city footprint (Charlotte not on it) | Confirmed real market: $508M annual wedding market, 13,931 weddings/year (wedding.report, 2025 data). Multiple real local rental companies with their own sites found (Thomas Rental, Party Reflections, Charlotte Party Rentals, Curated Events) — fragmented, no dominant local aggregator found. Not in Reventals' city list. | Reversible — pending human confirmation |

---

## 4. Tech Stack [PLANNED — not yet implemented]

Per brief §4, locked pending niche confirmation:
- Astro (latest stable) — static output, best CWV, content-collections
- `@astrojs/sitemap`, `site` set in config from commit #1
- Vanilla CSS, design tokens, no Tailwind
- Python 3.12 + SQLite (build-time only, no live DB in prod)
- Maps data source: TBD after niche confirmed (§8)
- LLM enrichment: latest cost-effective model, model name stored per-row (not hardcoded)
- Firecrawl MCP (installed, live) + Playwright MCP (not installed — see below)
- Hosting: Cloudflare Pages (free)
- Forms: Web3Forms/Formspark/CF Worker → human's email (real endpoint, not `action="#"`)
- Analytics: Plausible free tier or Umami
- Domain: Cloudflare Registrar, .com preferred over .directory

**Playwright MCP install (for the human to run, or ask Claude to run once needed):**
```
claude mcp add playwright npx '@playwright/mcp@latest'
```
Not run yet — not needed until JS-heavy scraping phase (§8).

---

## 5. Niche Validation Scorecard

**Note: this section is historical (session 1). Pickleball was the round-1 recommendation but was rejected in session 2 after a deep competitor check found a live incumbent (PickleballCosts.com). See §5b for the round-2 candidates and the final pick. Kept here for the audit trail — do not treat the "RECOMMEND" verdict below as current.**

Researched via Firecrawl web search (real SERP snapshots, 2026-07-11). Scored 1-5 per criterion (5 = best for us) except YMYL Risk and Competition Authority, which are inverted (5 = safest/most beatable).

| Niche | Demand | Commercial Value | SERP Gap | Moat Feasibility | YMYL Risk (5=safe) | Competition Beatable (5=easy) | Verdict |
|---|---|---|---|---|---|---|---|
| **Pickleball court construction/builders** | 4 | 5 ($8k-50k ticket) | 4 | 4 | 5 | 4 | **RECOMMEND** |
| Restroom trailer rental (event) | 4 | 4 ($500-4.5k/event) | 1 — `restroomtrailerlist.com` already owns this exact niche, 160 cities | 3 | 5 | 2 | REJECT — direct incumbent exists |
| RV/boat storage | 4 | 2 (low monthly commission) | 1 — Neighbor.com, Extraspace, PublicStorage, StorageArea marketplaces dominate w/ live inventory | 2 | 5 | 1 | REJECT |
| Fence installation | 5 | 4 | 1 — Angi/HomeDepot/Homewyse/Thumbtack own SERP | 3 | 5 | 1 | REJECT — mature lead-gen vertical |
| Home generator installation | 4 | 5 | 1 — Generac/Cummins (manufacturers) + HomeDepot/Lowes | 2 | 5 | 1 | REJECT |
| Inground pool builders | 5 | 5 | 1 — Angi/Thumbtack/Buildzoom + big builder brands | 3 | 5 | 1 | REJECT — mature vertical |
| Artificial turf installation | 4 | 3 | 1 — Angi/Thumbtack/HomeDepot | 3 | 5 | 1 | REJECT |
| Epoxy garage floor coating | 3 | 2 | 1 — Thumbtack dominant | 2 | 5 | 1 | REJECT — low ticket + saturated |
| Dumpster rental | 5 | 3 | 1 — WM.com (Fortune 500) + Angi + Homeguide/dumpsters.com | 2 | 5 | 1 | REJECT |
| Batting cage rental | 2 | 1 (hourly direct-booking, no lead-referral model) | 3 | 1 | 5 | 3 | REJECT — wrong business model, no lead value |

### Why pickleball court construction wins
- **Demand:** pickleball is the fastest-growing sport in the US; 8+ independent cost-guide articles already rank organically, confirming real search volume for "[x] cost near me" queries.
- **Commercial value:** $8,000–$50,000 per project. A single converted lead is worth real referral-fee money.
- **SERP gap:** top results are a mix of small builder-company blogs (versacourt, sportmaster, dominatorhoop) and ONE generic multi-vertical Homeguide page. No dedicated, deep, comparison-first directory exists (unlike restroom trailers, where `restroomtrailerlist.com` already does exactly this). `usapickleball.org`'s "preferred builder" list is a thin, sponsor-style directory, not a real comparison — a specific gap.
- **Moat feasibility:** builders are real local businesses — full Google Maps data available (name, address, phone, geo, rating, reviews). Real per-sq-ft pricing by region is collectable via scraping builder sites + outreach, and stays volatile enough (material costs, seasonal lead times, contractor capacity) to justify re-crawling on a cadence competitors won't match.
- **YMYL:** none — sports facility construction, not health/finance/legal.
- **Competition authority:** regional/small builder companies, not national lead-gen conglomerates. Realistic to outrank on long-tail city+niche pages.

### Trade-off to flag honestly
Total addressable search volume is smaller than fence/pool/dumpster (those are bigger categories) — the whole bet is that a smaller, less-contested pond beats a bigger, unwinnable one. If pickleball's growth curve flattens, TAM could stay thin. Kill-switch at month 6 (§7 of brief) applies as always.

**SUPERSEDED 2026-07-11 (later same day): rejected.** `PickleballCosts.com` was found live — 50-state + city pricing, cost calculator, contractor directory with reviews, "3 free quotes" lead-gen funnel. Structurally near-identical to the plan above. Likely templated/unverified data (same publisher family as sportsvenuecalculator.com) so the gap for *genuinely verified* data may still be real, but human chose not to compete against a live structural clone from zero authority. See §5b and Decision Log.

---

## 5b. Round 2 Niche Validation (session 2, human-supplied candidates)

Verified via 5 parallel research agents (WebSearch + Firecrawl, live scrapes of competitor sites), 2026-07-11. These candidates were supplied by the human explicitly to avoid re-treading round-1 ground; none were taken on faith.

| Niche | Verdict | Key finding |
|---|---|---|
| Dog boarding/daycare pricing | REJECT | Rover.com runs live, transaction-backed per-city/per-sitter pricing pages (updated monthly) + a parallel cost-guide blog for hundreds of cities. Same product, already at marketplace scale with 30k+ reviews. |
| RV parks — verified wifi/cell-signal ratings | REJECT (hard fail) | Campendium (70k+ campgrounds) and RV LIFE have run crowdsourced per-carrier signal bars + speed tests for ~a decade. Independent of competition: the moat requires an existing user base to crowdsource readings — unbootstrappable cold with $30 and zero audience. This is the exact niche the original brief flagged as a prior candidate not to just default to; confirmed correct. |
| Specialty home inspectors (mold/sewer scope/thermal) | REJECT | InterNACHI runs a fully programmatic certified-inspector directory with full city coverage (47 inspectors returned for one test metro alone). Angi/HomeAdvisor own the cost-guide layer. Also YMYL-adjacent (major property-purchase decision + mold health exposure). |
| Plasma donation payout rates/coupons | REJECT | discoverplasma.com already crowdsources real per-center pay data (1,256 centers, 46 states) with a $100/month donor incentive to keep it current — the exact infrastructure this moat needs, infeasible at this budget. Company sites only publish vague "up to $X" marketing figures, not real scrapable rates. |
| Heavy equipment rental (bobcat/excavator/skid steer) | REJECT | BigRentz and DOZR are national marketplaces already aggregating real city-level daily pricing; Home Depot/Sunbelt/United Rentals/Herc dominate the branded SERP with gated (call-for-quote) pricing. |
| **Party/event equipment rental (tents/tables/chairs)** | **ACCEPT — final pick** | No dominant incumbent for pricing-intent queries (WeddingWire/TheKnot rank for broad vendor-directory intent, not itemized pricing). Real itemized per-day pricing confirmed directly scrapable off individual local operators (e.g. Century Party Rental: 10x10 tent $150, chairs $1.25-$8.50/unit). Fragmented — dozens of metro-only operators, no single dominant player. Ticket size $1,500-6,000/wedding. |

### Why party/event rental wins
- **SERP gap:** genuinely the cleanest of all 15 niches checked across both sessions (10 in round 1, 5 in round 2). No marketplace, no certification body, no national aggregator owns the pricing-comparison intent.
- **Moat feasibility:** individual rental companies publish real per-day pricing directly on their own sites — confirmed via live scrape, not assumed.
- **YMYL:** none.
- **Honest trade-off:** smaller ticket than pickleball ($1.5-6k vs $8-50k) and than fence/pool (even bigger but unwinnable). Betting on a smaller, genuinely open niche over a bigger contested one — consistent with the lesson learned from pickleball this same session.

---

## 6. Database Schema [PLANNED — not yet built]
Will follow brief §5 spec: `raw_listings`, `scraped_pages`, `listings`, `target_cities`. DDL to be added once niche confirmed and `db_setup` script is written.

## 7. Data Pipeline [PLANNED]
Scripts per brief §5 (`maps_ingest`, `geo_validate`, `web_enrich`, `ai_extract`, `export_json`) — not started.

## 8. Maps Data Source

**DECIDED 2026-07-11: Apify — `compass/crawler-google-places` (Google Maps Scraper).** Not yet signed up/purchased — decision made, execution pending.

Comparison researched live (pricing pages scraped 2026-07-11):

| Provider | Price/1k | Fields | Free tier | Verdict |
|---|---|---|---|---|
| **Apify `compass/crawler-google-places`** | $1.50 | ALL: place_id, name, address, phone, lat/lng, rating, review_count, category, hours, photos | $5/mo free credit (no card) ≈ 3,300 places/mo | **Chosen.** ~1,500-business ingest ≈ $2.25, fully covered by free credit → ~$0 net. |
| Outscraper | $3 (500/mo free) | Same full field set | 500 free/mo | Close 2nd, declined as backup by human for simplicity. |
| SerpApi (Maps engine) | $25/mo or free | Same, incl. reviews/thumbnails | 250 free searches/mo forever | Viable, more complex free-tier math (searches vs listings). |
| SearchApi.io | $4/1k | Same | 100 free (one-time) | No small PAYG plan below $40/mo — likely exceeds budget. |
| Official Google Places API | ~$32/1k search + ~$17+/1k Place Details (2 paid calls needed for full fields) | Full fields only at Pro tier | Small per-SKU caps only; $200/mo blanket credit removed March 2025 | Most "official"/ToS-clean but most expensive here — rejected on cost. |
| DataForSEO | Cheapest raw unit cost | Full fields via Business Data API | None useful — **$50 minimum account top-up** | Rejected — minimum deposit alone exceeds the entire $30 project budget. |

All scraper-based options (Apify/Outscraper/SerpApi/SearchApi) operate in the same standard gray-area relative to Google's Maps ToS that essentially all directory-site data pipelines of this kind use; not flagged as a blocker.

**Next action:** sign up for Apify, wire `MAPS_DATA_API_KEY` into `.env`, write `maps_ingest.py` targeting the party/event rental niche once target city list is set (§Open Questions item 6).

## 9. Website Architecture [PLANNED]
Routes/SEO/schema.org per brief §6 — not started.

## 10. SEO Checklist [PLANNED]
All items from brief §6 — none yet applicable, nothing built.

## 11. Monetization Plan
Lead-referral to local party/event rental companies (tent/table/chair quote requests) + featured listing slots for rental businesses wanting visibility for their off-season/weekday capacity + reserved (empty) ad space until traffic justifies Mediavine (~month 6+). Honest expectation: plan for $0-300/mo outcome per brief's realistic distribution; treat anything above as upside. Ticket size ($1,500-6,000/wedding) is smaller than the rejected pickleball niche ($8k-50k) — referral fee per lead will be proportionally smaller; volume of weddings/events searched is the offsetting factor.

## 12. Budget Ledger

| Date | Item | Cost | Running Total |
|---|---|---|---|
| 2026-07-12 | Domain: eventrentalcosts.com | $9 | **$9 / $30** |

## 13. Security Notes
- `.env` created with EXA_API_KEY, FIRECRAWL_API_KEY, GEMINI_API_KEY (free-tier, human-provided 2026-07-11). Confirmed gitignored via `git check-ignore -v .env` — not tracked, not staged.
- `.gitignore` covers `.env*`, `node_modules/`, `dist/`, `.astro/`, `*.db` from commit #1.
- No secrets in any tracked file (repo tracks only: this doc, `.gitignore`, `.env.example`, `README.md`).
- Public GitHub remote live (see §14) — pushed only after confirming `.env` excluded via `git check-ignore`; re-verify before every future push.

## 14. Deployment State
Website: not deployed. **Domain purchased: eventrentalcosts.com** ($9, 2026-07-12). No Cloudflare Pages project yet. No Search Console.
GitHub: **public repo live** — https://github.com/Water9977/Niche-Directories-Website. Commits pushed 2026-07-12 (`.env` confirmed excluded, only `.env.example` tracked).

## 15. Roadmap / Next Steps (ordered)
1. ~~Get human sign-off on niche~~ — DONE (party/event rental, after pivot from pickleball).
2. ~~Get Exa API key~~ — DONE.
3. ~~Evaluate + approve Maps data source~~ — DONE (Apify).
4. ~~Pick flagship city~~ — DONE (Charlotte, NC).
5. ~~Pick + buy domain~~ — DONE (eventrentalcosts.com, $9).
6. Sign up for Apify, get API key into `.env` as `MAPS_DATA_API_KEY`.
7. Install Playwright MCP if/when JS-heavy scraping is needed (most rental-company sites are likely simple enough for Firecrawl alone — assess during web_enrich).
8. Scaffold Astro project, config (`site`, sitemap, robots.txt) from the first commit.
9. Design DB schema, write `db_setup`.
10. Build data pipeline scripts in order (maps_ingest → geo_validate → web_enrich → ai_extract → export_json).
11. Build website routes + SEO scaffolding.
12. Deploy to Cloudflare Pages, submit sitemap to Search Console.
13. Month-6 kill-switch check.
