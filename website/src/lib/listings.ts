import rawListings from '../data/listings.json';

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
  delivery_available: 'yes' | 'no' | 'unknown';
  setup_included: 'yes' | 'no' | 'unknown';
  weekend_surcharge: 'yes' | 'no' | 'unknown';
  pricing: PricingItem[];
  slug: string;
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
    // Collision (e.g. two near-identically-named but genuinely different real
    // businesses at different addresses) — disambiguate with postal code
    // rather than silently dropping either one.
    const withPostal = slugify(`${l.name}-${l.city}-${l.postal_code ?? ''}`);
    const n = (seen.get(withPostal) ?? 0) + 1;
    seen.set(withPostal, n);
    return { ...l, slug: n > 1 ? `${withPostal}-${n}` : withPostal };
  });
}

const listings: Listing[] = makeUniqueSlugs(rawListings as Omit<Listing, 'slug'>[]);

export const METRO_SUBURB_CITIES = ['Concord', 'Huntersville', 'Mooresville', 'Indian Trail', 'Monroe'];

export function getAllListings(): Listing[] {
  return listings;
}

export function getListingBySlug(slug: string): Listing | undefined {
  return listings.find((l) => l.slug === slug);
}

export function getCharlotteListings(): Listing[] {
  return listings.filter((l) => l.city === 'Charlotte');
}

export function getMetroSuburbListings(): Listing[] {
  return listings.filter((l) => METRO_SUBURB_CITIES.includes(l.city));
}

export function getMetroSuburbListingsByCity(): Record<string, Listing[]> {
  const grouped: Record<string, Listing[]> = {};
  for (const city of METRO_SUBURB_CITIES) {
    const cityListings = listings.filter((l) => l.city === city);
    if (cityListings.length > 0) grouped[city] = cityListings;
  }
  return grouped;
}

/** Lowest real per-day-ish price found across a listing's pricing items, for sorting/display. */
export function lowestPrice(listing: Listing): number | null {
  const prices = listing.pricing.map((p) => p.price_low).filter((p): p is number => p != null);
  return prices.length ? Math.min(...prices) : null;
}
