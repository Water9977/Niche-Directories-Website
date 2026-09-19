import {
  getAllListings,
  getPublishedMetros,
  matchingRows,
  type Listing,
  type PricingItem,
} from './listings';
import type { MetroMeta } from './metros';

/**
 * Statistics behind the category guide pages (/table-and-chair-rental-costs/,
 * /bounce-house-rental-costs/, /photo-booth-rental-costs/).
 *
 * Counting rule that matters: **each company gets one vote.** A few companies
 * publish dozens of near-identical rows for one category (one bounce-house
 * business alone lists 27 "combo bounce house dry" variants), so a median over
 * raw price points would mostly describe whichever company lists the most.
 * The "typical starting price" here is the median of each company's own
 * cheapest price in the category, which answers what a renter actually asks:
 * "what will a typical company charge me to start?" The full low-high range
 * still uses every price point.
 */

export interface CategoryPoint {
  listing: Listing;
  item: PricingItem;
  price: number;
}

export interface CategoryStats {
  /** Price points in the category. */
  points: number;
  /** Distinct companies publishing at least one. */
  companies: number;
  low: number;
  high: number;
  /** Median of each company's own cheapest price in this category. */
  typicalStart: number;
}

export type PricePredicate = (p: PricingItem) => boolean;

export function collectPoints(listings: Listing[], pred: PricePredicate): CategoryPoint[] {
  const out: CategoryPoint[] = [];
  for (const listing of listings) {
    for (const item of matchingRows(listing, pred)) {
      out.push({ listing, item, price: item.price_low! });
    }
  }
  return out;
}

export function median(nums: number[]): number {
  const s = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export function statsFor(points: CategoryPoint[]): CategoryStats | null {
  if (!points.length) return null;
  const cheapestByCompany = new Map<string, number>();
  for (const p of points) {
    const prev = cheapestByCompany.get(p.listing.slug);
    if (prev == null || p.price < prev) cheapestByCompany.set(p.listing.slug, p.price);
  }
  const prices = points.map((p) => p.price);
  return {
    points: points.length,
    companies: cheapestByCompany.size,
    low: Math.min(...prices),
    high: Math.max(...prices),
    typicalStart: median([...cheapestByCompany.values()]),
  };
}

export interface SubtypeSpec {
  label: string;
  /** One line on what falls in this bucket, shown under the label. */
  blurb: string;
  test: (item: PricingItem) => boolean;
}

export interface SubtypeRow {
  label: string;
  blurb: string;
  stats: CategoryStats;
}

/** Split a category into named sub-types. First matching spec wins, and
 * anything unmatched lands in a final "Other" row, so the rows always add up
 * to the category total instead of quietly dropping price points. */
export function subtypeBreakdown(
  points: CategoryPoint[],
  specs: SubtypeSpec[],
  otherLabel = 'Everything else',
  otherBlurb = 'Named or specialty items that don’t fit the groups above.',
): SubtypeRow[] {
  const buckets = new Map<string, CategoryPoint[]>(specs.map((s) => [s.label, []]));
  const other: CategoryPoint[] = [];
  for (const pt of points) {
    const spec = specs.find((s) => s.test(pt.item));
    if (spec) buckets.get(spec.label)!.push(pt);
    else other.push(pt);
  }
  const rows: SubtypeRow[] = [];
  for (const spec of specs) {
    const stats = statsFor(buckets.get(spec.label)!);
    if (stats) rows.push({ label: spec.label, blurb: spec.blurb, stats });
  }
  const otherStats = statsFor(other);
  if (otherStats) rows.push({ label: otherLabel, blurb: otherBlurb, stats: otherStats });
  return rows;
}

export interface MetroRow {
  meta: MetroMeta;
  stats: CategoryStats;
}

/** Per-metro view of a category, most companies first. Metros where no
 * company publishes the category are left out rather than shown empty. */
export function metroBreakdown(pred: PricePredicate): MetroRow[] {
  const rows: MetroRow[] = [];
  for (const { meta, listings } of getPublishedMetros()) {
    const stats = statsFor(collectPoints(listings, pred));
    if (stats) rows.push({ meta, stats });
  }
  return rows.sort(
    (a, b) => b.stats.companies - a.stats.companies || a.meta.name.localeCompare(b.meta.name),
  );
}

export interface CompanyRow {
  listing: Listing;
  points: number;
  low: number;
  high: number;
}

/** The companies with the most published prices in a category, each linking
 * to its own listing page. */
export function topCompanies(points: CategoryPoint[], limit: number): CompanyRow[] {
  const byCompany = new Map<string, CategoryPoint[]>();
  for (const p of points) {
    if (!byCompany.has(p.listing.slug)) byCompany.set(p.listing.slug, []);
    byCompany.get(p.listing.slug)!.push(p);
  }
  return [...byCompany.values()]
    .map((pts) => {
      const prices = pts.map((p) => p.price);
      return {
        listing: pts[0].listing,
        points: pts.length,
        low: Math.min(...prices),
        high: Math.max(...prices),
      };
    })
    .sort((a, b) => b.points - a.points || a.listing.name.localeCompare(b.listing.name))
    .slice(0, limit);
}

/** How many of the directory's companies publish this category at all, and in
 * how many published metros, for the sample-size line at the top of a guide. */
export function coverage(points: CategoryPoint[]): { companies: number; metros: number; totalCompanies: number } {
  const totalCompanies = getAllListings().length;
  const companies = new Set(points.map((p) => p.listing.slug)).size;
  const metroKeys = new Set(points.map((p) => p.listing.metro));
  const publishedKeys = new Set(getPublishedMetros().map((m) => m.meta.key));
  const metros = [...metroKeys].filter((k) => publishedKeys.has(k)).length;
  return { companies, metros, totalCompanies };
}

export const fmtMoney = (n: number): string => (n % 1 === 0 ? n.toFixed(0) : n.toFixed(2));

export function fmtRangeStats(s: Pick<CategoryStats, 'low' | 'high'>): string {
  return s.low === s.high ? `$${fmtMoney(s.low)}` : `$${fmtMoney(s.low)}–$${fmtMoney(s.high)}`;
}
