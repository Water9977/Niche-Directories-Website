# Niche Local Directory — architecture.md
_Living source of truth. Update every session. Never let this drift from actual code._

---

## Changelog (newest first)

### 2026-07-14 — Session 21: full-project deep audit (Fable-5-analysis.md) + week-1 fixes shipped
- Human asked for a complete deep analysis of everything (code, live site, SEO, UX, keywords, competitors) written to `Fable-5-analysis.md` — done, 10 bugs + 6 SEO opportunities + prioritized plan, all findings verified against the live site/real data, not assumed. Key research (2026): FAQPage schema no longer shows visual rich results but lifts AI-citation rates (~22% median); Bing WMT/IndexNow feeds ChatGPT/Copilot — unclaimed by this site.
- **Fixed and deployed the week-1 items in the same session:**
  - **B1 (the "$1+" trust-killer)**: rewrote `lowestPrice()` around a new `cheapestRentalItem()` — excludes fees/deposits/consumables/linens (real vocabulary-based regex), and the listing table now shows *what* the price is for ("$1.88+ folding chair"), because most sub-$10 prices turned out to be REAL chair prices that only looked broken without context. Metro intro's misleading "$1 to $1000" range replaced with labeled real examples (chairs from $X, tents from $Y).
  - **B2**: FAQPage JSON-LD on every metro page — FAQ content moved to a single `faqs` array so HTML and schema render from one source. Added a data-gated wedding-tent FAQ (only renders where 20x40+ tents exist in real data: Indianapolis + Jacksonville currently) targeting "wedding tent rental cost" (Easy KD).
  - **B3**: homepage now has WebSite + Organization JSON-LD (was the only page with zero schema).
  - **B4**: About page rewritten — 7 metros (was still saying "Charlotte metro area"), and the broken stat ("of 96 checked, 96 publish pricing" — a tautology since the export gate requires pricing) replaced with the real funnel: ~1,057 raw businesses checked → 96 publish verifiable pricing. That pass-rate IS the trust story.
  - **B5**: llms.txt updated with Richmond + Jacksonville (was missing 2 of 7 live metros).
  - **B6**: killed visible "Ad space reserved" boxes — in-content slot reserves height invisibly, mobile anchor bar removed entirely (was permanently eating ~50px of every mobile viewport for zero revenue).
  - **B7**: CSS-only scroll shadows on listing tables (mobile cut columns with no cue), immutable cache headers for hashed assets via `public/_headers` (B9).
- **IndexNow**: key generated, key file in `public/` (built, NOT yet deployed — production deploy of the key file blocked by permission mode mid-session; needs one more `wrangler deploy` + a ping to `api.indexnow.org`). Bing Webmaster Tools signup itself is a human task (Microsoft login; can one-click import the verified GSC property).
- **Needs the human**: (1) one more deploy for the IndexNow key file, then ping; (2) Bing WMT signup/import; (3) Cloudflare Email Routing (dashboard, 2 min: Email → create `contact@eventrentalcosts.com` → forward to own inbox — API token lacks the permission) so the About page's "found an error?" has a real contact route; (4) Web3Forms key (unchanged); (5) backlink outreach go/no-go (46 real scraped emails ready, Resend domain verification was still pending).
- Remaining from the analysis (this-month tier): national `/tent-rental-cost/` guide page from real cross-metro data (biggest content gap — no page targets the national head terms, all Easy KD), homepage grid redesign + real-price card teasers, monthly re-enrich freshness cadence, `minimum_order` item-type relabel + re-enrich Charlotte Party Rentals (its real tent inventory page has real prices; current listing only shows a $1,000 order minimum mislabeled as "tent frame").

### 2026-07-14 — Session 20: executed master plan items 2-9 (of the original 13); items 10-13 blocked/decided
Human said "GO" on the master plan, one item at a time, executed in order:
- **Item 1 (addressRegion → 2-letter state)**: added `stateAbbr()` in `website/src/lib/listings.ts` (data has mixed full-name/abbreviated states from Apify — normalized at read time). Applied to `seo.ts` schema, `ListingTable.astro`, and the listing-page title/description. **Bonus bug found+fixed in the same file**: the listing-page title hardcoded `, NC` for every listing regardless of actual state — wrong for Jacksonville FL, Indianapolis IN, etc. Fixed alongside.
- **Item 2 (titles 50-60 chars)**: homepage 65→43 chars, metro pages 66-84→40-59 chars (verified against real per-metro listing counts and names, worst case Greensboro at 58). Listing-page titles vary with real business name length (10-75 chars) — 13/96 still exceed 60 chars because the business's real name is long; not fixable without truncating/faking a name, so left as-is.
- **Item 3 (meta descriptions 150-160 chars)**: metro descriptions rewritten, 144-151 chars across all 7 live metros. Listing-page descriptions similarly vary with real business name length (21/96 exceed 160 for the same reason as above).
- **Items 4-7 (FAQ phrasing, tent-size content, bounce-house prominence, table/chair de-prioritize)**: built together on the metro page since they're all the same content surface. Added `tentSizeBreakdown()` and `bounceHousePriceRange()` to `listings.ts` — real aggregations from `listing_pricing.item_type` (regex-matched WxH tent sizes, `bounce.?house` pattern), not fabricated. New metro-page sections: "Tent rental cost by size", "Bounce house rental cost". FAQ expanded with the exact "how much does X cost" phrasing from the Ahrefs data, one entry each for tent/bounce-house/table&chair (table&chair kept to one short answer, no dedicated section — the de-prioritization).
- **Data-quality catch**: the existing `lowestPrice()` helper (used for the metro intro's price range and, initially, my tent FAQ answer) picks up non-rental line items like a $1 sock rental as the "lowest price" — made the new tent FAQ answer say "starts around $1", which is misleading. Fixed the FAQ to use the size-filtered tent minimum instead. The underlying `lowestPrice()` noise still affects the metro-page intro paragraph and homepage — **flagged as a follow-up task, not fixed this session** (out of scope of the 13 items, needs its own exclusion-list decision).
- **Item 8 (real images)**: found `raw_listings.photo_url` already existed in the pipeline DB (real Google-hosted business photos, 1034/1057 raw rows) but was never carried into `export_json.py`'s output or `listings.json` — added it to both. 95/96 published listings now have a real photo. Rendered on listing pages with `aspect-ratio` CSS (photo dimensions vary per business, avoided hardcoding width/height to prevent distortion/CLS).
- **Item 10 (lead-capture form)**: built `LeadForm.astro` — plain HTML POST to Web3Forms (no JS, works on the static Cloudflare Workers deploy), gated behind `PUBLIC_WEB3FORMS_KEY` so nothing broken ships if unset. Added `website/.env` (gitignored, Astro/Vite needs its own — the repo-root `.env` only feeds the Python pipeline). **Caught and fixed a fabrication risk in my own first draft**: the copy originally said "we'll pass your request along to real local companies" — untrue, there's no forwarding automation, it's a plain contact form to the site owner's inbox. Reworded to "we'll reply directly." **Blocked**: needs a real Web3Forms key from the human (free, no account — just an email to receive the key at) before the form actually renders.
- **Item 9 (backlink outreach)**: NOT sent. Sending real email to 92 real businesses is an irreversible, external action explicitly marked "human's call" in this same plan — did not send, asked instead.
- **Items 11-12 (Greenville/Pittsburgh push, more metros/suburbs)**: decided **accept as-is**, did not spend more Apify credit. Reasoning: (a) all suburb cities defined in `pipeline/metros.py` for the 3 weak metros were already ingested last session; (b) the changelog already documents hitting a genuine data ceiling for these small towns twice (sessions logged at lines ~124/132 of this file — businesses with no scrapable web pricing, not a pipeline gap); (c) remaining Apify free credit is only ~$1.94; (d) adding a genuinely new 10th metro is a research decision (verify it's outside the funded competitor's footprint, etc.), not a quick top-up — out of scope for "execute the list."
- **Item 13 (ads)**: still correctly deferred, no change.

### 2026-07-14 — Session 19: real SEO audit run, master plan compiled (not executed)
- Human manually pulled real Ahrefs keyword-volume data (bypassing the bot-check from last session by searching themselves) across ~15 query clusters: core niche terms, "near me" intent, adjacent items (bounce house, linen), and our actual metro cities.
- Pulled the full `seo-audit` skill (coreyhaines31/marketingskills, v2.0.0) via `gh api` after Firecrawl scrapes of the skills.sh preview page and a wrong raw-GitHub path both came back incomplete/404 — found the real path via search first.
- **Ran the skill's checklist against the live site for real** (not from memory): titles run 69-72 chars (recommended 50-60, real SERP-truncation risk), meta descriptions 160-164 chars (borderline over 150-160), H1 count correct (1/page), schema is server-rendered not JS-injected (no false-negative risk), page weight excellent (8.5KB homepage). **Found two real, concrete bugs**: (1) `LocalBusiness` schema's `streetAddress` field contains the full formatted address (street+city+state+zip) instead of just the street portion — redundant with the separate `addressLocality`/`addressRegion`/`postalCode` fields already in the same object; (2) NAP inconsistency — `addressRegion` stores the full state name ("North Carolina") while the site's own URLs/metro config use the standard abbreviation ("NC").
- Compiled a full master plan (below) combining: the real audit findings, the two keyword-research batches, and the standing open items (lead form, more metros, ads). **Not executed — human said don't start until "GO."**

**MASTER PLAN STATUS** (as of Session 20 — see that changelog entry for full detail on each)

- [x] 1. `streetAddress` schema bug — DONE (Session 20/streetAddress entry)
- [x] 2. `addressRegion` → 2-letter state abbreviation — DONE
- [x] 3. Title tags 50-60 chars — DONE (homepage/metro fully; listing pages vary with real business-name length, not fixable without truncating real data)
- [x] 4. Meta descriptions 150-160 chars — DONE (same caveat as above for listing pages)
- [x] 5. FAQ phrasing matched to real "how much does X cost" queries — DONE
- [x] 6. Tent-SIZE-specific content — DONE (new "Tent rental cost by size" section per metro)
- [x] 7. Bounce house prominence — DONE (new "Bounce house rental cost" section per metro)
- [x] 8. De-prioritize table/chair content — DONE (one FAQ line, no dedicated section)
- [x] 9. Real images on listing pages — DONE (95/96 listings, real Apify-captured Google photos)
- [~] 10. Real lead-capture form — component built (`LeadForm.astro`), gated behind `PUBLIC_WEB3FORMS_KEY` which is unset. **Needs human to get a free key from web3forms.com and set it in `website/.env`** before the form goes live.
- [ ] 11. Send the 92-target backlink outreach batch — NOT sent, human's call (irreversible external action).
- [x] 12. Push Greenville/Pittsburgh further — **decided: accept as-is.** Genuine data ceiling confirmed twice already (see lines ~124/132), all defined suburbs exhausted.
- [x] 13. More metros/suburb top-ups — **decided: accept as-is** for now. Only ~$1.94 free Apify credit left; a genuinely new metro is a research decision, not a quick top-up.
- [ ] 14. Ads — still deferred per the brief's month-6+ guidance.

**Still open, needs the human:** provide a Web3Forms key (item 10) and say go/no-go on sending the backlink outreach batch (item 11).

### 2026-07-14 — Session 18: suburb top-ups — Richmond crosses publish threshold, 7 metros live; Ahrefs blocked by bot-check
- Ingested all 11 remaining suburb cities from `metros.py` for the 3 weak/zero metros: Richmond (Henrico, Chesterfield, Midlothian, Glen Allen VA), Greenville (Greer, Simpsonville, Anderson, Spartanburg SC), Pittsburgh (Cranberry Township, Bethel Park, Monroeville PA). Apify cost: $1.37 → $3.06/$5 free credit for all 11. 1,057 total raw businesses now.
- Ran full downstream pipeline (geo_validate: 841 confirmed → web_enrich: 26 new candidates → ai_extract → validate_pricing: 1159 of 1193 rows verified) and export.
- **Result: 96 total published (91 live after excluding one already-flagged off-niche entry), 7 metros now clear the publish threshold** (up from 6): Jacksonville 25, Charlotte 22, Indianapolis 15, Raleigh-Durham 12, Columbus 7, Greensboro 5, **Richmond 5 (crossed the floor)**. Greenville reached 4 (still short), Pittsburgh stayed at 1 — confirmed via its own enriched businesses that it's a genuinely quote-gated market, not a pipeline gap.
- Rebuilt and deployed — Richmond's page went live automatically since its `metros.ts` config already existed from session 11 (`MIN_LISTINGS` gate auto-activates metros as they cross the floor, no code change needed). Verified live: homepage shows "91 verified tent... 7 US metro", `/richmond-va/` returns 200.
- **Tried to pull real keyword-volume data from Ahrefs' free keyword generator** (human's suggestion) via both the Browser pane and Firecrawl's action-scraping. Confirmed the tool sits behind a **Cloudflare Turnstile bot-check** ("Verify you are human") that blocks automated submission — did not attempt to bypass it (prohibited). Left it to the human to check manually and share numbers if wanted; the site's demand validation up to now has relied on real SERP-density signals instead, which remains the fallback.

### 2026-07-13 — Session 17: researched 3 directory-SEO YouTube videos, applied the findings
- Human asked to scrape 3 YouTube videos (Create a Pro Website's niche-directory tutorial; Frey Chu's "10 Easy Directory Niches" and "5 Profitable Directory Websites") via Firecrawl and apply what's useful. Firecrawl's YouTube postprocessor returned full transcripts, not just metadata — genuinely useful, not just titles/descriptions.
- **Key finding, repeated across all 3 videos independently: on-page SEO alone hits a traffic ceiling without backlinks.** This project has had zero backlink strategy up to this point — a real gap, not a nice-to-have. Built `pipeline/backlink_outreach.py`: generates a CSV of every published listing (92 businesses) with their real website, a guessed contact-page URL, and a drafted outreach message asking for a link back to their own listing page (real, low-friction ask — we're already giving them free exposure with real pricing, not cold spam). Does not send anything; sending real outreach emails is the human's call per the project's safety rules on messaging on someone's behalf.
- **Independent validation of two prior decisions**: (1) the ~$80-300/month revenue range cited across multiple real case studies (soakorgan.com, swimmingholes.org, concretedisciples.com — all 2-15k monthly visitors) matches the brief's own honest revenue distribution almost exactly. (2) rockhounding.org's decline was attributed to "completely empty" listing pages likely getting de-indexed — direct real-world validation of why `validate_pricing.py`'s strict real-data-only gate (session 9) was the right call, not overcaution.
- **Closest real-world analog to our monetization model found**: roaminghunger.com (food truck directory) sells qualified corporate-catering leads to vendors, now ~$14M/year — structurally identical to our own plan (real leads sold to real rental companies), not just an ad-revenue play. Reassuring validation of the thesis, not a new idea to chase.
- Applied one concrete UX pattern from the research: roaminghunger.com organizes many location pages by state with a toggle. We're not yet at the scale that needs a JS toggle (6 metros), so added static state-grouping to the homepage instead (`byState` grouping in `index.astro`) — same organizing principle, right-sized for current scale, and ready to become a real toggle later if the metro count grows enough to need one.
- Deployed and verified live: homepage groups metros under NC (3)/FL (1)/IN (1)/OH (1) headings, sorted by state total listings.

### 2026-07-13 — Session 16: www redirect done; declined to set up ads yet
- Added `www.eventrentalcosts.com` → apex domain, done in two parts: CNAME DNS record created via the Cloudflare API (that token has DNS edit), but the actual redirect rule needed the Rules/Single-Redirects product which the token wasn't scoped for — read Cloudflare's own docs (`/rules/url-forwarding/`) to get the exact dashboard flow right rather than guess, then guided the human through it: Wildcard pattern match `https://www.eventrentalcosts.com/*` → dynamic target `https://eventrentalcosts.com/${1}`, 301, preserve query string. **Verified live**: `curl -D-` on both `www.../` and `www.../charlotte-nc/` confirmed correct 301s with paths preserved, not just root.
- Human asked to also set up ads. **Pushed back rather than just doing it** — the brief's own plan explicitly marks ads as a month-6+ concern: the site launched today with zero traffic/history, Mediavine/Ezoic need ~50k sessions/month (nowhere close), and applying to AdSense with zero traffic risks a low-quality rejection for effectively $0 realistic revenue right now (no visitors = no impressions either way). Ad slots are already reserved and ready to flip on later — no rework needed when the time comes. Awaiting human's decision on whether to proceed anyway or wait for real traffic.

### 2026-07-13 — Session 15: real OG image, last SEO checklist gap closed
- Human asked to get the OG image "from Chrome." The Browser pane's `computer` screenshot/zoom actions hung (30s timeout, repeated) in this session, so used a local Playwright instance instead: installed the `playwright` npm package + Chromium, wrote a small script to screenshot a branded 1200x630 HTML card (wordmark, real headline, real stats pulled from the actual listing count) to PNG.
- Wired into `BaseLayout.astro`: `og:image`, `og:image:width/height`, `twitter:image`, upgraded `twitter:card` from `summary` to `summary_large_image`.
- Deployed (asset upload succeeded; the `wrangler deploy` routes-reconciliation step still errors on the same Workers-Routes permission gap from session 12 — harmless, asset/worker code updates regardless. Left `wrangler.jsonc`'s `routes` block alone rather than risk it detaching the working custom domain on a config-reconcile). Verified live: `/og-image.png` returns 200 at the correct 1200x630 dimensions, `og:image` tag points at it correctly.
- **This closes the last open item in the §10 SEO checklist** — everything in it is now done except the "not formally audited" accessibility note.

### 2026-07-13 — Session 14: Google Search Console verified, sitemap submitted — ranking clock started
- Human independently verified the domain in Google Search Console and submitted `https://eventrentalcosts.com/sitemap-index.xml` — status **Success**. "Discovered pages: 0" as of submission is expected (Google hasn't crawled yet; populates over the next hours-to-days).
- **This is the real milestone per the brief's §7**: the 6-12 month ranking clock now officially starts from 2026-07-13. Month-6 kill-switch check date: **~2027-01-13** — check Search Console impressions then, decide invest-more vs. the niche is dead per the brief's explicit framework.
- Honest expectation to hold onto: even with 85 real listings across 6 metros and correct technical SEO, brand-new zero-authority sites typically take months to show meaningful impressions, and the realistic outcome distribution from the brief still applies (~50% earn $0 ever). Nothing about today's launch changes those odds — it just means the clock is now running instead of not-yet-started.

### 2026-07-13 — Session 13: real domain live, found and fixed a robots.txt conflict
- Human's domain was registered at Spaceship (spaceship.com), not Cloudflare — kept registration there, moved DNS management to Cloudflare (standard, free, no domain transfer needed). Human added `eventrentalcosts.com` in the Cloudflare dashboard, got 2 nameservers, updated them at Spaceship. Verified propagation via `nslookup -type=NS` (near-instant — Google's public DNS already showed the new Cloudflare nameservers) and confirmed the zone showed `"status": "active"` via the Cloudflare API.
- Custom domain attachment to the Worker required broader token permissions than the original one had. Human created a second, properly-scoped Cloudflare API token (Account: Workers Scripts Edit; Zone: DNS/SSL/Zone Edit, scoped to just this zone — explicitly steered away from the legacy "Global API Key" which grants full account access, unnecessary and riskier). Even that token hit a permissions gap on the Workers Routes API specifically. Rather than keep chasing token scopes, finished the custom domain attach directly in the Cloudflare dashboard (one-click, uses the human's full session auth) — first attempt blocked by 2 leftover Spaceship parking-page A records, deleted those, retried, succeeded.
- **`eventrentalcosts.com` is now the live production URL**, verified: homepage 200 with correct real content, `/robots.txt`/`/sitemap-index.xml`/`/llms.txt` all 200, fake URL correctly 404s, canonical tags self-reference correctly (checked `/charlotte-nc/` → `rel="canonical" href="https://eventrentalcosts.com/charlotte-nc/"`).
- **Found and fixed a real SEO conflict**: `robots.txt` was serving Cloudflare's own auto-injected "Managed robots.txt" block (part of their AI Crawl Control product, on by default for new zones) **above** our custom content — it explicitly `Disallow: /` for `ClaudeBot`, `GPTBot`, and `Google-Extended`, directly contradicting the AI-crawler allowlist we deliberately built into `robots.txt` and `llms.txt` for AI-answer-engine citability. Found by literally reading the live `robots.txt` output rather than assuming a 200 status meant it was correct. Fixed: Cloudflare dashboard → AI Crawl Control → toggled off "Managed robots.txt". Re-verified live — clean, matches our intended file exactly.
- **Known minor gap, not blocking**: `www.eventrentalcosts.com` has no DNS record (only the apex domain was added as a custom domain). Nothing on the site links to `www` and all canonicals use the bare apex, so this doesn't affect SEO correctness — but a visitor typing `www.` manually would hit a dead end. Worth adding a redirect rule (apex already correct) next session.

### 2026-07-13 — Session 12: DEPLOYED — site is live on the real internet
- Human decided to ship now (85 listings/6 metros is a real directory) and asked Vercel vs Cloudflare Pages. Recommended staying with Cloudflare per the brief's original decision: Vercel's free Hobby tier explicitly disallows commercial use in its ToS, and this site carries ads/lead-gen intent — a real disqualifier, not a style preference.
- `wrangler login` (OAuth browser flow) timed out twice — browser likely wasn't reachable/visible in this session's environment. Switched to a Cloudflare API token instead (human created one via the dashboard, `CLOUDFLARE_API_TOKEN` added to `.env`, verified via `wrangler whoami` before using).
- `wrangler pages deploy` auto-delegated to Cloudflare's newer Workers-based static-assets deploy path (Cloudflare's current recommended architecture — Pages and Workers have merged), installing `@astrojs/cloudflare` and generating `wrangler.jsonc`. Output remains 100% prerendered static HTML (`prerendering static routes` for all pages) — no live compute, still matches the brief's static-only architecture, just a newer delivery mechanism.
- First deploy attempt failed needing a `workers.dev` subdomain registered; the interactive confirmation prompt silently defaults to "no" in a non-TTY session (piping "y" via stdin didn't work either — the prompt library ignores piped input). Registered the subdomain directly via Cloudflare's REST API (`PUT /accounts/{id}/workers/subdomain`) to unblock, then `wrangler deploy` succeeded.
- **Site is live**: https://eventrentalcosts.eventrentalcosts.workers.dev — verified via live navigation: correct homepage content (85 listings, 6 metros), zero console errors.
- **Not yet done: the real domain isn't pointed here yet.** `eventrentalcosts.com` needs to either move its DNS to Cloudflare (standard flow: add site to Cloudflare, update nameservers at the registrar) or get a custom domain route added to the Worker — need to know where the domain is currently registered before proceeding. Also still open: Search Console submission, real OG image, lead-capture form.

### 2026-07-12 — Session 11: 3 more metros — 59 → 85 published listings across 6 metros
- Human's original $5/mo Apify credit hit exactly $4.9996 mid-Indianapolis last session. Human created a fresh free Apify account (`apify_api_QtjFlZAq...`), wired into `.env`, confirmed fresh $5 credit via usage API before proceeding.
- Ingested the remaining 3 metros from `metros.py`: Jacksonville FL (90 raw items), Pittsburgh PA (65), Greenville SC (40). Fresh key at $1.37/$5 after all 3 — cheap, plenty of headroom left for suburb top-ups next session.
- Ran the downstream pipeline: geo_validate (687 confirmed) → web_enrich (56 new category-matched candidates). **Hit a real crash**: `web_enrich.py` had no exception handling around the Firecrawl HTTP call — a single 60s read-timeout on one business's site crashed the whole batch script (unhandled `requests.exceptions.ReadTimeout`). Per-record commits meant no data was lost, but the script had to be manually resumed. Fixed by wrapping the request in `try/except requests.exceptions.RequestException: return None` so one bad site no longer takes down the whole run — this bug will otherwise recur on any future metro since it's inherent to scraping real, sometimes-flaky small-business websites.
- ai_extract (37 with real pricing, 8 without, 2 failed) → validate_pricing (1065 of 1177 rows verified — hallucination rate holding steady around 10% this batch, lower than earlier ~20% batches) → export_json.
- **Result: 88 total published listings, 8 metros with data.** Jacksonville came in the biggest single metro yet at 24 listings. **Pittsburgh: 0 published** — all 8 enriched businesses were genuinely quote-gated (zero real pricing found anywhere), a real market finding, not a bug — Pittsburgh's rental scene apparently doesn't publish prices online. Greenville: 1 (below threshold, correctly held back).
- Added Jacksonville, Pittsburgh, and Greenville to `website/src/lib/metros.ts` (Pittsburgh/Greenville configs added even though not yet published — they'll auto-activate once they clear `MIN_LISTINGS`). **Site now shows 85 verified listings across 6 published metro pages** (Richmond 2 and Greenville 1 still below the floor). Rebuilt (99 pages, zero errors) and verified live via dev server — Jacksonville correctly appears on the homepage with its real count.

### 2026-07-12 — Session 10: multi-metro expansion — 22 → 59 published listings across 5 metros
- Human flagged (correctly) that one metro / 22 listings is too thin for a real directory. Diagnosis: a directory is meant to be many metros; one metro is one small directory. The pipeline is proven and cheap to run, so the fix is scaling metros, NOT squeezing Charlotte harder (already at its real ceiling). Explicitly rejected the tempting shortcut of publishing listings without pricing — that's the thin scraped-directory content the 2026 Google updates penalize, and it would gut the moat.
- Target: uncovered mid-size wedding markets outside Reventals.com's 34-metro footprint (same "find the gap" logic that made Charlotte viable). Added `pipeline/metros.py` (8 metros: Raleigh-Durham, Greensboro-Winston-Salem, Richmond, Columbus, Indianapolis, Jacksonville, Pittsburgh, Greenville — core city + key suburbs each) and `pipeline/seed_metros.py`.
- Ingest strategy: CORE city only per metro (~$0.36-0.62 each vs ~$2.33 for a full 8-city sweep) — Google Maps' core-city search already surfaces nearby suburb businesses. Ran 5 metros before the Apify $5/mo free credit hit exactly $4.9996/$5: Raleigh 88, Greensboro 67, Richmond 53, Columbus 89, Indianapolis 85 raw items. **Human is creating fresh free Apify accounts to continue — the remaining 3 metros (Jacksonville, Pittsburgh, Greenville) are pending a new API key.** (Tracked real per-metro cost live via Apify's usage API to know exactly when to swap.)
- Ran the full downstream pipeline on the 5 new metros (all free-tier, no Apify): geo_validate (532 confirmed) → web_enrich (72 of 78 new category-matched businesses enriched, wider-keyword v2 from session 7) → ai_extract (NVIDIA NIM primary + fallbacks; a few huge-catalog businesses failed on token-truncation, accepted as minor losses) → validate_pricing (removed ~20% hallucinated rows again — consistent rate — 633 verified of 717) → export_json.
- **Result: 61 total published listings** (up from 22): Charlotte 22, Indianapolis 14, Raleigh-Durham 12, Columbus 6, Greensboro 5, Richmond 2. Added `metro` to the export JSON so the site can group by metro.
- **Rebuilt the website from Charlotte-hardcoded to fully multi-metro:**
  - New `website/src/lib/metros.ts` — metro key → {slug, name, state, blurb} config + a `MIN_LISTINGS = 5` thin-content floor. A metro only gets a page + homepage card once it clears the floor; metros auto-graduate as data grows, no code change needed. **Richmond (2 listings) is correctly held back** — so the site publishes 59 listings across 5 metros, not the raw 61.
  - Rewrote `lib/listings.ts` around metros (group-by-metro, group-by-city within a metro, threshold filtering).
  - Replaced the two hardcoded Charlotte pages with one dynamic `src/pages/[metro].astro` (getStaticPaths from published metros; sections by city when a metro has multiple, single table otherwise). Homepage now lists all published metros. Header nav, 404, listing-page breadcrumbs, and llms.txt all regenerated from the metro config.
- Builds clean (71 pages: 61 listings + 5 metro pages + homepage + about/privacy/terms + 404), verified live via dev server — homepage shows all 5 metros with real counts, Raleigh/Indianapolis metro pages render real companies with real pricing, zero console errors.

### 2026-07-12 — Session 9: Astro site built and launched (Charlotte + Metro Suburbs), found and fixed a real hallucination bug
- Confirmed launch structure: Charlotte as a deep flagship city page, the other 5 towns combined into one honest "Charlotte Metro Suburbs" page rather than 5 thin URLs — matches the research from session 8.
- Scaffolded the Astro site at `website/` (Astro 5, `@astrojs/sitemap`, vanilla CSS design tokens, no Tailwind, `site` set to `https://eventrentalcosts.com` from the first commit). Structure: `BaseLayout` (canonical/OG/JSON-LD per page), `Header`/`Footer`, `AdSlot` (CSS `min-height`-reserved, anchor + in-content variants per session 8's ad research, absent on listing detail pages), `Breadcrumbs`, `ListingTable`, `ThreeStateBadge` (yes/no/"Not published" — never coerces unknown to a negative claim).
- Routes built: homepage (real area selector generated from data, not hardcoded), `/charlotte-nc/` (flagship), `/charlotte-metro-nc/` (combined suburbs, sectioned by town), `/listing/[slug]/` (one per business, `getStaticPaths` from real data), `/about/` (honest methodology disclosure — states the real pass/fail count of businesses with real pricing), `/privacy/`, `/terms/`, custom `/404` (noindex).
- SEO baked in per the `seo-s` skill checklist + brief §6: per-page self-referencing canonicals, sitemap via `@astrojs/sitemap`, `robots.txt` with explicit AI-crawler allow blocks (GPTBot/ClaudeBot/PerplexityBot/OAI-SearchBot/Google-Extended) + sitemap reference, `llms.txt`, `BreadcrumbList`/`ItemList`/`LocalBusiness` JSON-LD (aggregateRating only emitted when a listing has real rating+review_count, never fabricated), unique title/description per page. **Open gap: no real OG image** — no image-generation tooling available in this session (ffmpeg can't rasterize SVG, no ImageMagick/canvas lib); omitted the `og:image` tag entirely rather than ship a broken or unreliable one. Needs a real designed 1200x630 PNG before this checklist item is actually done.
- **Found and fixed a real data-integrity bug while spot-checking the built site**, not before: several listings showed "$0+" or "$1+" as their starting price. Investigated the raw `listing_pricing` rows and found the 8B extraction model had hallucinated ~20% of them (72 of 353) — inventing prices for generic marketing copy with no real number, misreading a shopping-cart "0 items" counter as a price, and in one case assigning 5 different fabricated prices (\$1000/\$2500/\$5000) to 5 different "features" all sourced from one unrelated "Minimum project size: \$1,000" sentence. One business (`Thomas Equipment & Party Rentals`) had literally "Contact us for price." as its source text for 15 line items, all still fabricated with numbers by the model.
- Built `pipeline/validate_pricing.py`: verifies every `price_low`/`price_high` actually appears as a real dollar figure in its own `source_snippet` before it's allowed to stay; also rejects any `$0` price outright (real rental items are never free — a `$0.00` that's technically quoted verbatim in a snippet is virtually always a broken JS price-widget placeholder on the business's own site, not a real price). Removed 73 of 353 rows total. 4 listings lost their only real pricing and dropped out of the published set entirely as a result (`Thomas Equipment & Party Rentals`, `RentmeUSA Party Rentals`, `Country Roads Party Rentals LLC`, `Tent Guys`) — correct behavior, not a bug: a listing with no verified real pricing shouldn't be published.
- **Final published count after validation: 22 real, verified listings** (down from the pre-validation 26 — the 4 fewer are the honest number), 261 verified pricing rows, across Charlotte (13) + 5 metro suburb towns (9 combined: Concord 2, Huntersville 1, Mooresville 2, Indian Trail 2, Monroe 2).
- Site builds cleanly (`npm run build` in `website/`, 29 pages, zero errors) and was spot-checked live via the dev server — homepage, Charlotte page, Metro Suburbs page, and a listing detail page all read correctly with real data, correct three-state badges, and no console errors.
- Also fixed a real slug-collision bug caught during the first build: two genuinely different real businesses (`RentMeUSA Party Rentals` and `RentmeUSA Party Rentals`, different addresses/place_ids) produced the same URL slug from name+city alone. Fixed by disambiguating with postal code on collision rather than silently dropping either listing.
- **Not yet done:** real OG image, AdSense/analytics not wired up (slots are empty placeholders only, correctly so per the brief — applying to ad networks is a month-6+ concern), no deploy yet (still local `dist/`), Search Console not set up, no quote-request lead-capture form yet (individual listings currently link directly to the business's own real phone/website — honest and functional, but doesn't capture leads for the site's own referral-fee model; needs a Web3Forms or similar key before building a real form).



### 2026-07-12 — Session 8: SEO/ads research, confirmed real data ceiling, launch-structure decision pending
- Loaded local skill `E:\Claude\Claude Skills\seo-s` (Next.js/Vercel-specific audit skill, not directly runnable here, but its technical checklist transfers: canonical tags, sitemap gotchas, robots.txt + explicit AI-crawler allowlist, `llms.txt`, structured data validity, meta completeness, soft-404 handling). Will bake this checklist into the Astro build.
- Ran 2 parallel research agents (Reddit/Twitter/YouTube via Firecrawl + WebSearch) on (a) local-directory SEO tactics for the 2025/2026 "anti-thin-directory" Google updates, and (b) ad-placement best practices for lead-gen sites.
  - **Key finding: city pages need ~5-10 real listings minimum before they stop reading as thin content.** Real directory operators report pages below that threshold don't just underperform individually — the 2026 enforcement pattern is a domain-wide "weakest link" effect (Digital Applied's March 2026 analysis: sites mixing strong and weak programmatic pages got hit broadly, not just on the weak pages). Sources: directoryfa.st, Digital Applied's programmatic-SEO-after-March-2026 post, Search Engine Journal's aggregator-visibility analysis (TripAdvisor -45, Yelp -33 in that update).
  - **Reassuring counter-finding:** genuinely unique per-item pricing data (our core moat) is explicitly named as a *surviving* signal pattern in the same analysis — "local directories with unique business data, reviews, and hours" were low-impact/maintained. The site's thesis holds; the risk is specifically about publishing pages that don't yet have enough real data.
  - Ad research: anchor/sticky-footer + one in-content slot (between every ~4-6 listings) is the real-world pattern for lead-gen sites — deliberately lower ad density than a pure content blog since a clicked ad is a lost lead. CSS `min-height` reservation only (JS-based sizing still causes CLS). Keep the quote-request flow itself completely ad-free.
- Checked current per-city counts against the 5-10 threshold: Charlotte 16 (passes), **Concord 3, Huntersville 1, Mooresville 2, Indian Trail 2, Monroe 2 — all 5 below the bar.**
- Human chose to widen the Maps search before deciding launch structure, rather than assume the shortfall was permanent. Added `EXTRA_SEARCH_TERMS` to `maps_ingest.py` (bounce house rental, linen rental, wedding decor rental, chair rental) and re-pulled all 5 weak cities (`--extra-terms` flag, $2.33/$5 free credit total, still $0 net). Raw supply grew meaningfully (Concord 38→50, Huntersville 19→27, Mooresville 22→33, Indian Trail 20→25, Monroe 17→21).
- **Result: no change to publishable count.** Re-ran geo_validate (224 confirmed) → web_enrich (only 4 new category-matched candidates had a website at all, all 4 were already-known dead domains/Instagram-only) → export_json. **Still exactly 26 published listings, same 5 weak cities.** Confirmed via direct query: the remaining category-matched-but-unenriched businesses in these towns have no website field in Google Maps at all. This is a genuine real-world data ceiling — these small towns don't have enough party/event rental businesses with real published web pricing — not a search-term or pipeline gap.
- **Open decision (asked, awaiting answer):** Charlotte as a deep flagship city page (16 real listings) is solid. For the other 5 towns (10 listings combined, each individually below the thin-content threshold), the recommended approach is one honest combined "Charlotte Metro Area" page covering all 5 towns as sections, rather than 5 separate thin URLs — avoids the domain-wide weakest-link risk the research flagged while still using 100% of the real data gathered.

### 2026-07-12 — Session 7: widened pricing detection, gathered full data — 26 listings
- Human asked to maximize data gathering rather than launch thin with 11 listings. Rewrote `web_enrich.py` (v2): widened `PRICING_KEYWORDS` from 8 terms to 26 (added shop/store/products/rentals/book/order/reserve/browse/collection/etc — session 6's list only caught literal "pricing"/"rates" links and missed sites publishing real prices under other nav labels), follows up to 3 candidate pages per business instead of 1, and probes a fixed list of common paths (`/shop`, `/catalog`, `/rentals`, etc.) directly when no nav link matches.
- Cleared and re-ran the full enrichment + extraction cycle from scratch on all 43 category-matched businesses. Dollar-sign hit rate roughly doubled: 24/43 pages now contain real pricing signal, up from 14/43 last session.
- Hit a second real bug during re-extraction: 5 businesses failed with "unterminated string" JSON errors — traced to `max_tokens=2048` truncating mid-output on businesses with lots of real pricing items (the ones with the *most* data were the ones failing). Bumped to 6000, all 5 recovered cleanly (Rogue Motions SFX alone had 49 real pricing items once it could finish).
- Investigated a further oddity: 3 previously-successful businesses (Abuelita's Touch, Sunbelt Rentals, "Now It's A Party!") came back with "no real pricing found" after the re-enrichment added more pages to their context. Suspected content truncation (20k char limit) for the one that grew past it, bumped to 40k and retried — same result. Concluded this is the model being appropriately conservative on ambiguous content, not a bug: the earlier "\$ sign present" heuristic can false-positive on incidental dollar amounts (deposits mentioned in policy text, unrelated numbers) that aren't real per-item rental prices. Not every "\$" is real pricing data.
- Checked for remaining untried candidates: found 15 more category-matched businesses across the metro that had never been enriched. Ran them — 11 of 15 have no `website` field in Google Maps at all (informal operators, Facebook/Instagram-only), and the remaining 4 either had dead domains or were Instagram-only "websites." **This is a genuine data ceiling, not a pipeline gap** — you cannot verify pricing from a business with no scrapable web presence.
- **Final result: 26 published listings** (up from 11), **333 real pricing items** (up from 151), across **6 of 8 target cities** (Charlotte 16, Concord 3, Huntersville 1, Mooresville 2, Indian Trail 2, Monroe 2). Gastonia and Matthews remain at zero — their category-matched candidates are either website-less or have no real published pricing, confirmed exhaustively rather than assumed.

### 2026-07-12 — Session 6: ai_extract built, LLM provider saga, first published listings
- Built `ai_extract.py` and ran it across all 43 enriched businesses. Hit a real wall: **Gemini's free tier caps at a hard 20 requests/day PER MODEL** (confirmed via the AI Studio dashboard — `gemini-2.5-flash` showed 21/20, `gemini-2.5-flash-lite` also capped at 20/day). This isn't a per-minute throttle, it's a daily quota tied to the Google Cloud project; retrying doesn't help until midnight Pacific reset. Burned through both models' daily allowances mid-run.
- Human provided two more free-tier keys (OpenRouter, NVIDIA NIM) and asked for real doc research before picking, not another guess. Read OpenRouter's and Google's actual rate-limit docs via Firecrawl, and NVIDIA NIM's via forum threads (no clean official page found, but consistent 40 RPM reports with no daily cap mentioned).
  - **OpenRouter free (`:free`) models**: 20 RPM / 50 RPD account-wide (not per-model) if <10 lifetime credits purchased, 1000 RPD if ≥10 purchased. Tested `openai/gpt-oss-120b:free` (garbled output, flaky provider) and `meta-llama/llama-3.3-70b-instruct:free` (real requests, but hit consistent ~28s upstream-provider rate limits — confirmed via `GET /api/v1/key` that our own account usage was 0, so this was shared free-tier congestion on OpenRouter's third-party inference hosts, not our own cap).
  - **NVIDIA NIM**: tested `meta/llama-3.3-70b-instruct` first — timed out repeatedly (60s+, likely cold-start or capacity on that specific model). Switched to `meta/llama-3.1-8b-instruct` — responded in <1s, reliable. Good enough for a structured-JSON extraction task (not complex reasoning).
- **Final provider chain in `ai_extract.py`**: NVIDIA `meta/llama-3.1-8b-instruct` (primary) → NVIDIA `meta/llama-3.3-70b-instruct` → OpenRouter `llama-3.3-70b-instruct:free` → OpenRouter `qwen3-next-80b-a3b-instruct:free`, each with short retry-then-fallback. `extracted_by_model` is recorded per-row (not hardcoded) exactly as the brief requires, since which provider actually served a given extraction now varies row to row.
- **Result: 42/43 businesses processed** (1 failure — `K's Bounce n Play` — repeatedly produced malformed/truncated JSON across all 4 providers, likely a scraped-content quirk; accepted as an acceptable single-row loss rather than over-engineering a fix). **12 businesses had real extractable pricing** (~29%, matching the ~1/3 rate predicted from the dollar-sign spot-check last session), 172 total pricing line items.
- Built `export_json.py` — the actual publish quality gate. Requires: real address, `geo_status='confirmed'`, at least one real `listing_pricing` row. Also excludes off-niche category leaks by name keyword (`glamping` — catches the "Sweet Dreams Glamping" edge case found last session; Google itself categorizes it as "Tent rental service" so the category filter alone couldn't catch it). **Result: 11 real, publishable listings** across 5 of the 8 target cities (Charlotte, Gastonia, Matthews, Indian Trail, Monroe — Concord, Huntersville, Mooresville had zero businesses clear the bar), 151 pricing items, written to `pipeline/export/charlotte-metro-listings.json`.
- Honest read on this number: 11 listings from 209 raw Maps businesses is a real, defensible dataset — not padded, not fabricated — but it's thin for a full 8-city launch. Concord/Huntersville/Mooresville currently have zero publishable listings. Next session should decide whether to re-run enrichment with a wider pricing-link detection net (many businesses likely publish real prices under nav labels our `PRICING_KEYWORDS` list didn't catch — "Shop", "Rentals", "Catalog", "Products") before declaring the pilot city "done," rather than launching with visible city-page gaps.

### 2026-07-12 — Session 5: geo_validate + web_enrich, and a real quality-gate finding
- Built `geo_validate.py`: labels each raw_listing's `geo_status` (`confirmed`/`mismatch`/`unknown`) against its target city — never drops silently. Result on the 209 rows: 191 confirmed, 3 real mismatches (e.g. a Kannapolis business surfaced under a Concord search — real business, just outside that city's polygon), 15 unknown (missing city field). Per the brief, mismatches stay in the data with a label; export_json's quality gate decides what publishes.
- **Found a category-relevance problem the hard way:** initial `web_enrich.py` test ordered candidates by review_count and hit Costco, Camping World, a bowling alley, and a furniture outlet — Google Maps' matching on generic terms like "party rental" and "table and chair rental" pulls in venues, DJs, bridal shops, retail stores, not just actual rental businesses. Checked the full category breakdown (209 rows spanned 60+ distinct categories) and added an `ALLOWED_CATEGORIES` filter (Party equipment rental service, Tent rental service, Equipment rental agency, Furniture rental service, Audiovisual equipment rental service) — cut the enrichment pool to the ~63 rows that are actually rental businesses.
- Built `web_enrich.py`: scrapes each business's own site directly via Firecrawl's REST API (not the MCP tool — the pipeline is a standalone script, same pattern as maps_ingest calling Apify directly), skips a hardcoded aggregator-domain list (Facebook, Yelp, Angi, Thumbtack, WeddingWire, TheKnot, Reventals, Instagram, Google), follows one auto-detected pricing-keyword link per homepage. Hit the same Windows console emoji-encoding crash as the geo_validate spot-check earlier — data was safe (commits are per-record) but fixed with `sys.stdout.reconfigure(encoding="utf-8")` so it doesn't happen again.
- **Result: 43 businesses enriched** (homepage + pricing page where found), 6 with a dedicated pricing page auto-detected, 2 failed (no scrapable content), 1 skipped (Instagram-only "website"). **Real finding: only 14/43 scraped homepages actually contain a dollar amount.** Spot-checked "Party Reflections" — a 31KB product catalog page, zero real prices — likely a request-quote/login-to-see-pricing model, same pattern as Reventals and WeddingWire found in earlier competitor research. This is not a pipeline bug — it's the moat's quality gate doing its job: most local rental businesses simply don't publish real prices publicly, and the site should only ever list ones that do. Expect the eventual `published=1` set to be a real minority of the 209 raw businesses, not all of them.
- Not yet done: ai_extract (pull structured pricing from the ~14-20 businesses with real dollar signals into `listing_pricing`), export_json, Astro scaffold.

### 2026-07-12 — Session 4: real Maps data ingested for Charlotte metro
- Signed up for Apify, wired `MAPS_DATA_API_KEY` into `.env`. Confirmed actor ID `nwua9Gu5YrADL7ZDj` = `compass/crawler-google-places`.
- Built `pipeline/` — `db_setup.py` (schema: target_cities, raw_listings, scraped_pages, listings, listing_pricing) and `maps_ingest.py` (calls the Apify actor, upserts into raw_listings deduped on real `place_id`, `ON CONFLICT` refreshes rating/reviews/hours on re-run). Isolated venv at `pipeline/.venv` (gitignored) since the system Python lacked pip.
- **Corrected a cost assumption from session 2:** full detail scraping (needed for phone/rating/review_count/hours — all required fields) costs ~$7-8/1,000 places, not the base $1.50/1k quoted on Apify's pricing page (that rate excludes the detail-page add-on). Verified via real account usage API after a 5-place test run, before committing to the full pull — this is why the test-first approach mattered.
- Ran ingest across all 8 Charlotte-metro target cities (search terms: "tent rental", "party rental", "table and chair rental"). **Result: 209 unique real businesses**, each with a genuine Google `place_id`, address, phone, rating, review count, category, lat/lng. Total Apify spend: $1.65 of the $5/month free credit — $0 actual out-of-pocket. Per-city counts: Charlotte 45, Concord 38, Gastonia 27, Mooresville 22, Matthews 21, Indian Trail 20, Huntersville 19, Monroe 17.
- Spot-checked output quality: real addresses, real phone numbers, real websites (e.g. Charlotte Party Rentals, Thomas Equipment & Party Rentals, RentMeUSA). One loosely-related result ("Sweet Dreams Glamping") surfaced under the "tent rental" search term — expected noise, to be filtered in geo_validate/category-cleanup, not a data-integrity problem.
- Not yet done: geo_validate (confirm each listing's real city matches its target city), web_enrich (scrape each business's own site for real pricing), ai_extract, export_json, Astro scaffold.

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

## 6. Database Schema

**BUILT 2026-07-12** — `pipeline/db_setup.py`. Live DDL (SQLite, build-time only, matches brief §5 spec plus a `listing_pricing` table for the moat data):

- `target_cities` — city, state, metro, lat/lng, active flag. Seeded with the 8 Charlotte-metro cities.
- `raw_listings` — one row per real Maps business, unique on `place_id`. Includes `geo_status` (default `'unchecked'`) for the geo_validate step.
- `scraped_pages` — one row per business-website page scraped in web_enrich (not yet populated).
- `listings` — the enriched/published table. Three-state fields (`delivery_available`, `setup_included`, `weekend_surcharge`) stored as TEXT `'yes'/'no'/'unknown'`, never coerced to boolean. Has a `published` gate flag.
- `listing_pricing` — the actual moat: per-item real pricing (`item_type`, `price_low/high`, `unit`, `source_snippet`, `source_url`, `extracted_by_model`, `last_checked`). Not yet populated (needs web_enrich + ai_extract).

Run `python pipeline/db_setup.py` to (re)create. DB file (`pipeline/directory.db`) is gitignored — build artifact, not source.

## 7. Data Pipeline

Scripts per brief §5 (`maps_ingest`, `geo_validate`, `web_enrich`, `ai_extract`, `export_json`).

- **`maps_ingest.py` — BUILT and RUN 2026-07-12.** Calls Apify's `compass/crawler-google-places` actor, upserts into `raw_listings` deduped on real `place_id` (`ON CONFLICT` refreshes rating/reviews/hours so re-running stays current — this is the freshness-cadence mechanism). Has a `--test` mode (1 city, 1 term, 5 places) used before the full run to verify real data and real cost before committing spend. **Result: 209 unique real Charlotte-metro businesses ingested, $1.65 of Apify's $5/mo free credit used, $0 out-of-pocket.** See changelog for per-city counts and spot-check notes.
- `geo_validate.py`, `web_enrich.py`, `ai_extract.py`, `export_json.py` — not built yet, next up.

## 8. Maps Data Source

**DECIDED 2026-07-11, EXECUTED 2026-07-12: Apify — `compass/crawler-google-places` (Google Maps Scraper).**

Comparison researched live (pricing pages scraped 2026-07-11):

| Provider | Price/1k | Fields | Free tier | Verdict |
|---|---|---|---|---|
| **Apify `compass/crawler-google-places`** | $1.50 base, **~$7-8/1k with full detail scraping actually enabled** (corrected 2026-07-12 — see below) | ALL: place_id, name, address, phone, lat/lng, rating, review_count, category, hours, photos | $5/mo free credit (no card) | **Chosen.** Real run: 209 places, $1.65 spent — well inside free credit, $0 net. |
| Outscraper | $3 (500/mo free) | Same full field set | 500 free/mo | Close 2nd, declined as backup by human for simplicity. |
| SerpApi (Maps engine) | $25/mo or free | Same, incl. reviews/thumbnails | 250 free searches/mo forever | Viable, more complex free-tier math (searches vs listings). |
| SearchApi.io | $4/1k | Same | 100 free (one-time) | No small PAYG plan below $40/mo — likely exceeds budget. |
| Official Google Places API | ~$32/1k search + ~$17+/1k Place Details (2 paid calls needed for full fields) | Full fields only at Pro tier | Small per-SKU caps only; $200/mo blanket credit removed March 2025 | Most "official"/ToS-clean but most expensive here — rejected on cost. |
| DataForSEO | Cheapest raw unit cost | Full fields via Business Data API | None useful — **$50 minimum account top-up** | Rejected — minimum deposit alone exceeds the entire $30 project budget. |

All scraper-based options (Apify/Outscraper/SerpApi/SearchApi) operate in the same standard gray-area relative to Google's Maps ToS that essentially all directory-site data pipelines of this kind use; not flagged as a blocker.

**Cost correction (2026-07-12):** the $1.50/1k figure on Apify's pricing page is the base search rate; it does not include `scrapePlaceDetailPage`, which is required to reliably get `review_count`/`hours`/full `phone` (confirmed via Apify's own input-schema docs: "Enabling this also ensures that reviewsCount will be scraped"). With detail scraping on, real measured cost was ~$7-8/1,000 places (verified via Apify's account usage API after a small test run, before committing to the full pull). Still cheap in absolute terms — 209 real places cost $1.65 — but future volume estimates should use ~$8/1k, not $1.50/1k.

**Executed:** signed up for Apify 2026-07-12, `MAPS_DATA_API_KEY` in `.env`, `maps_ingest.py` built and run across all 8 Charlotte-metro cities. See §7 and changelog for results.

## 9. Website Architecture

**BUILT 2026-07-12** — Astro 5 static site at `website/`. Routes:

| Route | Purpose |
|---|---|
| `/` | Homepage — area selector generated from real data (2 areas: Charlotte, Metro Suburbs), no hardcoded links to non-existent pages |
| `/charlotte-nc/` | Flagship city page — 13 real listings, comparison table, real local context, FAQ |
| `/charlotte-metro-nc/` | Combined suburbs page — 9 listings across 5 towns, sectioned, avoids 5 separate thin pages |
| `/listing/[slug]/` | One per business (22 total) — full pricing table, policies, real phone/website CTA, no ads |
| `/about/` | Honest methodology — states the real pass/fail count of businesses checked vs. published |
| `/privacy/`, `/terms/` | Required for lead-gen/ads |
| `/404` | Custom, `noindex` |

Data flow: `pipeline/export/charlotte-metro-listings.json` → manually copied to `website/src/data/listings.json` (no automated sync yet — a build script to do this automatically is a good next-session addition once the pipeline is re-run regularly).

## 10. SEO Checklist

- [x] Per-page correct canonical (self-referencing, computed from `Astro.site` + path — never all-homepage)
- [x] `@astrojs/sitemap` generating; `site` set in `astro.config.mjs`; `robots.txt` references `sitemap-index.xml`
- [x] Unique title + meta description per page
- [x] Valid structured data: `BreadcrumbList` (all pages), `ItemList` (city pages), `LocalBusiness` (listing pages) — `aggregateRating` only emitted when a listing has a real `rating` + `review_count`, never fabricated
- [x] **Real OpenGraph image — DONE 2026-07-13.** Rendered via a local Playwright instance (browser screenshot tool was hanging in-session): a branded 1200x630 HTML card screenshotted to PNG, real site stats (85+ companies, 6 metros). Live at `/og-image.png`, wired into `og:image`/`twitter:image` (upgraded twitter:card to `summary_large_image`).
- [x] No AI-slop copy — reviewed page content for invented stats/unverifiable "we verify" claims; About page states real counts, not marketing fluff
- [x] Three-state rendering (yes/no/"Not published") — never coerces missing data to a negative claim
- [x] Ad slots reserved as empty CSS-`min-height` space (anchor + in-content), no ad network applied yet (correct per brief — month-6+ concern)
- [x] Mobile-first, responsive (`clamp()` typography, anchor ad slot mobile-only)
- [x] `robots.txt` with explicit AI-crawler allow blocks (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Google-Extended)
- [x] `llms.txt` present with honest, factual site summary
- [ ] Accessibility — basic (`aria-label`s present) but not formally audited
- [x] **Deployed and verified live** at https://eventrentalcosts.com (2026-07-13) — all items above checked against the real production URL, not just local dev
- [x] Google Search Console: domain verified, sitemap submitted, status Success (2026-07-13) — ranking clock started

## 11. Monetization Plan
Lead-referral to local party/event rental companies (tent/table/chair quote requests) + featured listing slots for rental businesses wanting visibility for their off-season/weekday capacity + reserved (empty) ad space until traffic justifies Mediavine (~month 6+). Honest expectation: plan for $0-300/mo outcome per brief's realistic distribution; treat anything above as upside. Ticket size ($1,500-6,000/wedding) is smaller than the rejected pickleball niche ($8k-50k) — referral fee per lead will be proportionally smaller; volume of weddings/events searched is the offsetting factor.

## 12. Budget Ledger

| Date | Item | Cost | Running Total |
|---|---|---|---|
| 2026-07-12 | Domain: eventrentalcosts.com | $9 | **$9 / $30** |

Apify usage ($1.65 of the $5/mo free credit, 209 places ingested) is tracked separately — it's inside the free tier, not a real charge against the $30 cash cap. Will move into this ledger for real if/when usage ever exceeds $5/mo.

## 13. Security Notes
- `.env` created with EXA_API_KEY, FIRECRAWL_API_KEY, GEMINI_API_KEY, MAPS_DATA_API_KEY (Apify), OPENROUTER_API_KEY, NVIDIA_API_KEY (all free-tier, human-provided across sessions). Confirmed gitignored via `git check-ignore -v .env` — not tracked, not staged.
- `.gitignore` covers `.env*`, `node_modules/`, `dist/`, `.astro/`, `*.db`, `pipeline/.venv/`, `__pycache__/` from commit #1.
- No secrets in any tracked file (repo tracks only: this doc, `.gitignore`, `.env.example`, `README.md`, `pipeline/*.py`, `pipeline/requirements.txt`).
- Public GitHub remote live (see §14) — pushed only after confirming `.env` excluded via `git check-ignore`; re-verify before every future push.

## 14. Deployment State
**Website is LIVE at https://eventrentalcosts.com** (real production domain, not just the workers.dev URL). Cloudflare Workers static assets. Verified: correct content, zero console errors, robots.txt/sitemap/llms.txt all 200, 404 handling correct, canonicals self-reference correctly.
- Domain registrar: Spaceship (spaceship.com) — registration stays there, DNS management moved to Cloudflare (nameservers updated at Spaceship to Cloudflare's, zone active).
- `www.eventrentalcosts.com` not yet set up (minor, not SEO-blocking — see changelog).
- No Search Console submission yet — next step.
GitHub: **public repo live** — https://github.com/Water9977/Niche-Directories-Website. Commits pushed through 2026-07-13.
Cloudflare account: dedicated account created for this project (credentials in `.env`, not tracked — never put personal/account email or account ID in this doc, it's public). Worker name `eventrentalcosts`, `workers.dev` subdomain registered, custom domain attached, AI Crawl Control's "Managed robots.txt" turned off (was overriding our intentional AI-crawler allowlist).

## 15. Roadmap / Next Steps (ordered)
1. ~~Get human sign-off on niche~~ — DONE (party/event rental, after pivot from pickleball).
2. ~~Get Exa API key~~ — DONE.
3. ~~Evaluate + approve Maps data source~~ — DONE (Apify).
4. ~~Pick flagship city~~ — DONE (Charlotte, NC).
5. ~~Pick + buy domain~~ — DONE (eventrentalcosts.com, $9).
6. ~~Sign up for Apify, wire key, build + run maps_ingest~~ — DONE (209 real Charlotte-metro businesses, $1.65/$5 free credit).
7. ~~Build `geo_validate.py`~~ — DONE (191 confirmed / 3 mismatch / 15 unknown of 209).
8. ~~Build `web_enrich.py`~~ — DONE (43 businesses enriched after category filtering).
9. ~~Build `ai_extract.py`~~ — DONE (NVIDIA NIM primary, OpenRouter fallback, after Gemini's 20/day/model cap forced a provider switch — see changelog). 42/43 processed, 12 with real pricing.
10. ~~Build `export_json.py`~~ — DONE. **11 publishable listings live in `pipeline/export/charlotte-metro-listings.json`.**
11. ~~Widen pricing detection, gather full data~~ — DONE. 26 published listings before the session 9 validation-bug fix; see below for the corrected honest number.
12. ~~Scaffold Astro project, config (`site`, sitemap, robots.txt)~~ — DONE.
13. ~~Build website routes + SEO scaffolding~~ — DONE. See §9/§10.
14. ~~Build `validate_pricing.py`, fix hallucinated pricing~~ — DONE. **22 published listings, 261 verified pricing rows** — the honest, spot-checked-clean number. See changelog for the bug found and how it was caught.
15. ~~Deploy, point real domain, submit sitemap to Search Console~~ — DONE (2026-07-13). **Live at eventrentalcosts.com, sitemap Success, ranking clock started.** See changelog session 12-14 for the Vercel-vs-Cloudflare decision, the domain/DNS migration from Spaceship, and the Cloudflare AI-crawler robots.txt bug found and fixed.
16. **Get a real OG image** (1200x630 PNG) — no tooling available in any session so far, needs either a design tool or an image-generation MCP.
17. **Get a Web3Forms (or similar) key** so listing pages can carry a real multi-quote lead-capture form instead of just linking to each business's own contact info directly.
18. ~~Set up `www.eventrentalcosts.com` redirect~~ — DONE 2026-07-13. Verified 301, paths preserved.
19. Build a proper sync step from `pipeline/export/*.json` into `website/src/data/` (currently a manual copy) — matters more once more metros get added.
20. Consider more metros / suburb top-ups for the metros still below the 5-listing floor (Richmond, Greenville, Pittsburgh) — Apify key has ~$3.63/$5 free credit left.
21. **Month-6 kill-switch check: ~2027-01-13.** Check Search Console impressions; invest more / build site 2 if climbing, stop if flat, per the brief's framework.
