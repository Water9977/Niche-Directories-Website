import rawListings from '../data/listings.json';
import { METROS, MIN_LISTINGS, metroByKey, nearbyMetroKeys, type MetroMeta } from './metros';

export interface PricingItem {
  item_type: string;
  price_low: number | null;
  price_high: number | null;
  unit: string | null;
  source_snippet: string | null;
  extracted_by_model: string | null;
  last_checked: string | null;
}

export interface Listing {
  name: string;
  metro: string;
  address: string;
  city: string;
  state: string;
  postal_code: string | null;
  lat: number | null;
  lng: number | null;
  phone: string | null;
  website: string | null;
  rating: number | null;
  review_count: number | null;
  category: string | null;
  photo_url: string | null;
  delivery_available: 'yes' | 'no' | 'unknown';
  setup_included: 'yes' | 'no' | 'unknown';
  weekend_surcharge: 'yes' | 'no' | 'unknown';
  pricing: PricingItem[];
  slug: string;
}

/** Apify's Google Maps extraction returns full state names for some records
 * and USPS abbreviations for others (spot-checked: FL came through abbreviated,
 * everything else full-name) — normalize at read time rather than re-running
 * the scrape, since schema/display need the 2-letter form consistently. */
const STATE_ABBR: Record<string, string> = {
  'North Carolina': 'NC',
  Virginia: 'VA',
  Ohio: 'OH',
  Indiana: 'IN',
  Florida: 'FL',
  'South Carolina': 'SC',
  Pennsylvania: 'PA',
  // Added 2026-09-12: both came through as full names, so listing titles read
  // "Pooler, Georgia" while the breadcrumb above them said "Savannah, GA".
  Georgia: 'GA',
  Tennessee: 'TN',
};

export function stateAbbr(state: string): string {
  return STATE_ABBR[state] ?? state;
}

export function slugify(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function makeUniqueSlugs(items: Omit<Listing, 'slug'>[]): Listing[] {
  const baseSlugs = items.map((l) => slugify(`${l.name}-${l.city}`));
  const counts = new Map<string, number>();
  for (const s of baseSlugs) counts.set(s, (counts.get(s) ?? 0) + 1);

  const seen = new Map<string, number>();
  return items.map((l, i) => {
    const base = baseSlugs[i];
    if ((counts.get(base) ?? 0) <= 1) return { ...l, slug: base };
    // Collision (two near-identically-named but genuinely different real
    // businesses at different addresses) — disambiguate with postal code
    // rather than silently dropping either one.
    const withPostal = slugify(`${l.name}-${l.city}-${l.postal_code ?? ''}`);
    const n = (seen.get(withPostal) ?? 0) + 1;
    seen.set(withPostal, n);
    return { ...l, slug: n > 1 ? `${withPostal}-${n}` : withPostal };
  });
}

const listings: Listing[] = makeUniqueSlugs(rawListings as Omit<Listing, 'slug'>[]);

export function getAllListings(): Listing[] {
  return listings;
}

export function getListingBySlug(slug: string): Listing | undefined {
  return listings.find((l) => l.slug === slug);
}

export function getListingsByMetroKey(metroKey: string): Listing[] {
  return listings.filter((l) => l.metro === metroKey);
}

/** Metros that actually have listings AND clear the thin-content floor,
 * in METROS declaration order. These are the only ones that get a page. */
export function getPublishedMetros(): { meta: MetroMeta; listings: Listing[] }[] {
  return METROS.map((meta) => ({ meta, listings: getListingsByMetroKey(meta.key) })).filter(
    (m) => m.listings.length >= MIN_LISTINGS,
  );
}

/** Published listings whose metro hasn't cleared MIN_LISTINGS, so no metro page
 * exists to link them. Without surfacing these somewhere they're orphans: live
 * and in the sitemap, but reachable by zero internal links. Found live
 * 2026-07-26 — Pittsburgh's single listing had been in that state since the
 * metro was added, joined by Myrtle Beach's two. Covers both cases: a metro
 * declared in METROS but under the floor, and one not declared there at all. */
export function getUnpagedListings(): Listing[] {
  const paged = new Set(getPublishedMetros().map((m) => m.meta.key));
  return listings
    .filter((l) => !paged.has(l.metro))
    .sort((a, b) => a.city.localeCompare(b.city) || a.name.localeCompare(b.name));
}

export function getMetroForListing(listing: Listing): MetroMeta | undefined {
  return metroByKey(listing.metro);
}

/** Published metros geographically near the given one, for cross-metro
 * internal linking on metro pages (SEO audit 2026-07-31). Filters the real
 * adjacency list down to metros that actually have a page right now, so a
 * neighbor below MIN_LISTINGS (or removed) never produces a dead link. */
export function getNearbyPublishedMetros(key: string): MetroMeta[] {
  const publishedKeys = new Set(getPublishedMetros().map((m) => m.meta.key));
  return nearbyMetroKeys(key)
    .filter((k) => publishedKeys.has(k))
    .map((k) => metroByKey(k))
    .filter((m): m is MetroMeta => m != null);
}

/** Group a metro's listings by city, so a metro page can section them. */
export function groupByCity(items: Listing[]): { city: string; listings: Listing[] }[] {
  const byCity = new Map<string, Listing[]>();
  for (const l of items) {
    if (!byCity.has(l.city)) byCity.set(l.city, []);
    byCity.get(l.city)!.push(l);
  }
  // Largest city section first.
  return [...byCity.entries()]
    .map(([city, ls]) => ({ city, listings: ls }))
    .sort((a, b) => b.listings.length - a.listings.length);
}

/** Item types that are real rows in the data but aren't rentable equipment —
 * fees, deposits, admissions, and consumable add-ons (built from the actual
 * item_type vocabulary in listings.json, e.g. a real "$2 socks" add-on at a
 * bounce venue and a "$1 chair cover" that were surfacing as a company's
 * headline "starting price" and reading as broken data). */
const NON_RENTAL_ITEM_RE =
  /deposit|delivery|fee\b|_fee|socks|admission|ticket|supervision|syrup|popcorn$|popcorn_supplies|cover|cushion|tablecloth|linen|candleholder|candlestick|goblet|pillow|tabletop_|napkin/i;

export interface CheapestItem {
  price: number;
  label: string;
}

/** Human-readable label for an item_type slug, truncated so long catalog
 * slugs don't blow up table cells. */
function itemLabel(itemType: string): string {
  const text = itemType.replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  return text.length > 26 ? `${text.slice(0, 25)}…` : text;
}

/** Cheapest real *rentable equipment* price for a listing, with what it's
 * for. Showing "$1+" alone read as broken data (a $1 folding chair is real,
 * but nobody knows it's a chair); showing "$1+ (folding chair)" reads as the
 * verified fact it is. */
export function cheapestRentalItem(listing: Listing): CheapestItem | null {
  let best: CheapestItem | null = null;
  for (const p of listing.pricing) {
    if (p.price_low == null || p.price_low <= 0) continue;
    if (NON_RENTAL_ITEM_RE.test(p.item_type)) continue;
    if (!best || p.price_low < best.price) {
      best = { price: p.price_low, label: itemLabel(p.item_type) };
    }
  }
  return best;
}

/** Lowest real rentable-equipment price for a listing, for sorting/display. */
export function lowestPrice(listing: Listing): number | null {
  return cheapestRentalItem(listing)?.price ?? null;
}

/** Cheapest real chair price across a set of listings — chairs are the most
 * common lowest-priced real item, so metro intros anchor on them explicitly
 * instead of an unlabeled (and misleading-looking) bare minimum. */
export function chairPriceMin(items: Listing[]): number | null {
  let min: number | null = null;
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null || p.price_low <= 0) continue;
      if (!/chair/i.test(p.item_type)) continue;
      if (NON_RENTAL_ITEM_RE.test(p.item_type)) continue;
      if (min == null || p.price_low < min) min = p.price_low;
    }
  }
  return min;
}

export interface TentSizeStat {
  size: string;
  low: number;
  high: number;
  count: number;
}

/** Real per-size tent pricing, aggregated from `item_type` values that name an
 * actual WxH tent (e.g. `tent_40x60`, `pole_tent_30x30`) — keyword research
 * confirmed size-specific searches (40x60, 20x40, 20x30, 20x20) carry real
 * volume, but this data is otherwise buried in the flat per-listing pricing
 * table. Only counts item_types containing "tent" AND a WxH pattern, so
 * unrelated catalog entries that happen to share a `tent_` prefix (a few
 * furniture-rental listings use it oddly, e.g. `tent_kingston_farm_table`)
 * are excluded automatically. */
export function tentSizeBreakdown(items: Listing[], minCount = 1): TentSizeStat[] {
  const bySize = new Map<string, number[]>();
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null) continue;
      if (!/tent/i.test(p.item_type)) continue;
      const m = p.item_type.match(/(\d+)\s*x\s*(\d+)/);
      if (!m) continue;
      const size = `${m[1]}x${m[2]}`;
      if (!bySize.has(size)) bySize.set(size, []);
      bySize.get(size)!.push(p.price_low);
    }
  }
  return [...bySize.entries()]
    .map(([size, prices]) => ({
      size,
      low: Math.min(...prices),
      high: Math.max(...prices),
      count: prices.length,
    }))
    .filter((s) => s.count >= minCount)
    .sort((a, b) => {
      const [aw, ah] = a.size.split('x').map(Number);
      const [bw, bh] = b.size.split('x').map(Number);
      return aw * ah - bw * bh;
    });
}

export interface PriceRange {
  low: number;
  high: number;
  count: number;
}

/** Renders a price range, collapsing to a single figure when low === high.
 * Metro pages aggregate small per-metro samples, so a category with one real
 * price (or several identical ones) otherwise renders as "$10–$10", which
 * reads like a formatting bug rather than real data. Found live 2026-07-26
 * across 6 collapsed ranges on metro pages spanning several categories. */
export function formatPriceRange(range: PriceRange, fmt: (n: number) => string): string {
  return range.low === range.high
    ? `$${fmt(range.low)}`
    : `$${fmt(range.low)}–$${fmt(range.high)}`;
}

/** Real bounce-house price range from `item_type` values matching "bounce
 * house" in any form — keyword research showed real head-term volume + Easy
 * KD on "bounce house rental cost", better than table/chair terms, so this
 * gets its own stat rather than staying buried in the generic pricing table. */
export function bounceHousePriceRange(items: Listing[]): PriceRange | null {
  const prices: number[] = [];
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null) continue;
      if (/bounce.?house/i.test(p.item_type)) prices.push(p.price_low);
    }
  }
  if (!prices.length) return null;
  return { low: Math.min(...prices), high: Math.max(...prices), count: prices.length };
}

// Matches "table"/"tables" as a real word, not a substring — a naive /table/i
// would also match every single bounce-house/inflatable item_type, since
// "inflatable" itself contains "table" (in-fla-TABLE). Verified against the
// live DB before shipping: 0 of 117 real matches were contaminated by
// "inflatable" once boundaries were required on both sides. The separate
// /cloth/i guard below catches tablecloth item_types the NON_RENTAL_ITEM_RE
// tablecloth check misses when the words are space- or underscore-separated
// ("COCKTAIL TABLE CLOTH", "table_cloth_60x120") rather than one word.
const TABLE_WORD_RE = /(^|[^a-zA-Z])tables?([^a-zA-Z]|$)/i;

// Real contamination found live 2026-07-26 while shipping tablePriceRange,
// both from a single business's garbled extraction, not the regex above:
// (1) item_types like "tents_tables_chairs_and_more_tent_20x20" are a
//     category breadcrumb the model captured as the item_type instead of the
//     actual item -- the $679.90 behind it is a TENT price, not a table's.
// (2) one "table_round_60in" row's source_snippet is literally for a sofa
//     ($400 "cream boucle sherpa sofa") -- a real item_type hallucination
//     validate_pricing.py can't catch, since it only checks that the price
//     appears in the snippet, never that the snippet is actually about the
//     claimed item. Guarding against recognizable furniture words here
//     rather than hand-excluding one row, so a future re-extraction with the
//     same failure mode doesn't quietly slip back in.
const GARBLED_CATEGORY_RE = /tent.*chair|chair.*tent/i;
const WRONG_ITEM_SNIPPET_RE = /sofa|couch|loveseat|sectional/i;

// Found 2026-09-12 while putting real category ranges on the homepage, where a
// contaminated figure would have been the first thing anyone saw:
// (1) "tables_and_chairs" ($200) is a category bundle, not an item — it could
//     be a table, a chair, or a package covering both, so it can't honestly
//     anchor either category's range.
// (2) the "tents_tables_chairs_and_more_" breadcrumb prefix one real business's
//     extraction produced is followed by the ACTUAL item, so the tail decides
//     the category: "..._tent_20x30" is a $679.90 TENT and must never count as
//     a chair, while "..._white_resin_chair" ($4.50) is a genuine chair price
//     worth keeping. GARBLED_CATEGORY_RE already drops the whole family from
//     tables; chairs need the narrower tent-with-a-size test instead.
// (3) "table_leg_extension" ($1) and "table_tree_decoration" ($3) are parts and
//     decor, not tables — they were making "tables from $1" technically true
//     and practically misleading.
const AMBIGUOUS_BUNDLE_RE = /tables?[_\s]+and[_\s]+chairs?|chairs?[_\s]+and[_\s]+tables?/i;
const TENT_WITH_SIZE_RE = /tent[_\s]*\d+\s*x\s*\d+/i;
const TABLE_PART_RE = /leg[_\s]?extension|decoration/i;

/** Real table price range (any table type — banquet, cocktail, round, etc) —
 * "table rental cost" is an Easy-KD real-volume keyword (keyword-research.md
 * batch 1) that only ever surfaced as a single chair-price line, never its
 * own number, despite real table pricing existing across the data. */
export function tablePriceRange(items: Listing[]): PriceRange | null {
  const prices: number[] = [];
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null || p.price_low <= 0) continue;
      if (/cloth/i.test(p.item_type)) continue;
      if (GARBLED_CATEGORY_RE.test(p.item_type)) continue;
      if (AMBIGUOUS_BUNDLE_RE.test(p.item_type)) continue;
      if (TABLE_PART_RE.test(p.item_type)) continue;
      if (p.source_snippet && WRONG_ITEM_SNIPPET_RE.test(p.source_snippet)) continue;
      if (TABLE_WORD_RE.test(p.item_type)) prices.push(p.price_low);
    }
  }
  if (!prices.length) return null;
  return { low: Math.min(...prices), high: Math.max(...prices), count: prices.length };
}

function priceRangeForPattern(items: Listing[], pattern: RegExp): PriceRange | null {
  const prices: number[] = [];
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null || p.price_low <= 0) continue;
      if (pattern.test(p.item_type)) prices.push(p.price_low);
    }
  }
  if (!prices.length) return null;
  return { low: Math.min(...prices), high: Math.max(...prices), count: prices.length };
}

/** Real published delivery-fee range — for the national cost guide's "does
 * delivery cost extra" question, answered with real numbers instead of a
 * generic "it varies." */
export function deliveryFeeRange(items: Listing[]): PriceRange | null {
  return priceRangeForPattern(items, /delivery/i);
}

/** Real published deposit range, same reasoning as deliveryFeeRange. */
export function depositRange(items: Listing[]): PriceRange | null {
  return priceRangeForPattern(items, /deposit/i);
}

/** "photo booth rental cost" showed >100 volume + Easy KD in the July 2026
 * Ahrefs pull (wedding + 360 variants too) and we hold real published photo
 * booth pricing across several metros — same promote-on-real-demand logic
 * as bounce houses. */
export function photoBoothPriceRange(items: Listing[]): PriceRange | null {
  return priceRangeForPattern(items, /photo.?booth|photobooth/i);
}

/** "water slide rental cost" = Easy KD, and the dataset holds dozens of real
 * water-slide price points (Jacksonville especially). */
export function waterSlidePriceRange(items: Listing[]): PriceRange | null {
  return priceRangeForPattern(items, /water.?slide|water_unit/i);
}

/** Real chair price range, same guards as chairPriceMin (which only ever
 * returned a floor). Needed so chairs can take part in the per-listing peer
 * comparison below like every other category. */
export function chairPriceRange(items: Listing[]): PriceRange | null {
  const prices: number[] = [];
  for (const l of items) {
    for (const p of l.pricing) {
      if (p.price_low == null || p.price_low <= 0) continue;
      if (!/chair/i.test(p.item_type)) continue;
      if (NON_RENTAL_ITEM_RE.test(p.item_type)) continue;
      // See the notes on AMBIGUOUS_BUNDLE_RE / TENT_WITH_SIZE_RE above: a
      // "tents_tables_chairs_and_more_tent_20x30" row is a tent price, and a
      // "tables_and_chairs" row is a bundle — neither is a real chair rate.
      if (AMBIGUOUS_BUNDLE_RE.test(p.item_type)) continue;
      if (TENT_WITH_SIZE_RE.test(p.item_type)) continue;
      prices.push(p.price_low);
    }
  }
  if (!prices.length) return null;
  return { low: Math.min(...prices), high: Math.max(...prices), count: prices.length };
}

export interface PeerComparison {
  label: string;
  self: PriceRange;
  peers: PriceRange;
  /** How many *other* companies in the compared pool publish a price here. */
  peerCompanies: number;
  /** Whether the comparison pool was this company's own metro or the whole
   * directory. Some companies are the only one locally publishing a given
   * category (a photo-booth specialist in a tent-heavy metro, say) — falling
   * back to the national pool keeps the comparison real, as long as the page
   * says plainly which pool it used. */
  scope: 'local' | 'national';
}

type RangeFn = (items: Listing[]) => PriceRange | null;

function comparisonFor(
  label: string,
  fn: RangeFn,
  listing: Listing,
  localPeers: Listing[],
  nationalPeers: Listing[],
): PeerComparison | null {
  const self = fn([listing]);
  if (!self) return null;
  const pools = [
    ['local', localPeers],
    ['national', nationalPeers],
  ] as const;
  for (const [scope, pool] of pools) {
    if (!pool.length) continue;
    const peers = fn(pool);
    if (!peers) continue;
    const peerCompanies = pool.filter((p) => fn([p]) != null).length;
    if (!peerCompanies) continue;
    return { label, self, peers, peerCompanies, scope };
  }
  return null;
}

/** How many peer comparisons a single listing page will show. Tent sizes are
 * capped separately because a big catalog can publish a dozen of them and the
 * section stops being readable. */
const MAX_TENT_SIZE_COMPARISONS = 5;
const MAX_COMPARISONS = 9;

/** Compare one company's real published prices against the other companies we
 * track in the same metro, category by category.
 *
 * This is the one genuinely original thing this site can say that no single
 * rental company's own website can: not just "here is their price" but "here
 * is their price next to everyone else's in the same market." Added 2026-09-12
 * after AdSense's "low value content" rejection — per-listing pages were a
 * scraped price table and little else, which is exactly the thin/templated
 * pattern their policy calls out. Every number here is real published pricing
 * already verified for that business; the comparison is computed, never
 * estimated, and a category is skipped entirely when either side lacks data.
 */
export function comparePricingToPeers(
  listing: Listing,
  localPeers: Listing[],
  nationalPeers: Listing[] = [],
): PeerComparison[] {
  const out: PeerComparison[] = [];

  // Size-specific tent comparison first — it's what a renter actually shops
  // on, and a 20x40 next to other 20x40s is a fair comparison in a way that
  // "tents, generally" is not.
  for (const self of tentSizeBreakdown([listing])) {
    if (out.length >= MAX_TENT_SIZE_COMPARISONS) break;
    const sizeRange: RangeFn = (items) => {
      const stat = tentSizeBreakdown(items).find((t) => t.size === self.size);
      return stat ? { low: stat.low, high: stat.high, count: stat.count } : null;
    };
    const c = comparisonFor(`${self.size} tents`, sizeRange, listing, localPeers, nationalPeers);
    if (c) out.push(c);
  }

  const categories: { label: string; fn: RangeFn }[] = [
    { label: 'Tables', fn: tablePriceRange },
    { label: 'Chairs', fn: chairPriceRange },
    { label: 'Bounce houses', fn: bounceHousePriceRange },
    { label: 'Photo booths', fn: photoBoothPriceRange },
    { label: 'Water slides', fn: waterSlidePriceRange },
    { label: 'Delivery', fn: deliveryFeeRange },
    { label: 'Deposits', fn: depositRange },
  ];

  for (const { label, fn } of categories) {
    if (out.length >= MAX_COMPARISONS) break;
    const c = comparisonFor(label, fn, listing, localPeers, nationalPeers);
    if (c) out.push(c);
  }

  return out;
}

/** Where a company's published price sits against the local range, per
 * category. Deliberately three-state and conservative: "within" covers any
 * overlap with the local range, so we only ever say below/above when the
 * company's own floor genuinely clears the whole local spread. */
export type PricePosition = 'below' | 'within' | 'above';

export function pricePosition(c: PeerComparison): PricePosition {
  if (c.self.low < c.peers.low) return 'below';
  if (c.self.low > c.peers.high) return 'above';
  return 'within';
}
