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

/** Lowest real price found across a listing's pricing items, for sorting/display. */
export function lowestPrice(listing: Listing): number | null {
  const prices = listing.pricing.map((p) => p.price_low).filter((p): p is number => p != null);
  return prices.length ? Math.min(...prices) : null;
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
export function tentSizeBreakdown(items: Listing[]): TentSizeStat[] {
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
