import rawListings from '../data/listings.json';
import { METROS, MIN_LISTINGS, metroByKey, type MetroMeta } from './metros';

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

export function getMetroForListing(listing: Listing): MetroMeta | undefined {
  return metroByKey(listing.metro);
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
