import type { Listing } from './listings';
import { stateAbbr } from './listings';

const SITE = 'https://eventrentalcosts.com';

export function breadcrumbJsonLd(items: { label: string; href: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.label,
      item: new URL(item.href, SITE).toString(),
    })),
  };
}

/** Our `address` field is the full Maps-formatted string ("123 Main St, City,
 * ST 12345") but PostalAddress.streetAddress should be just the street
 * portion — city/state/zip already have their own fields. Splitting on the
 * first comma matches every address we've ingested so far (verified against
 * real data, not assumed); falls back to the full string if a business ever
 * has no comma at all rather than silently dropping data. */
function streetOnly(fullAddress: string): string {
  const idx = fullAddress.indexOf(',');
  return idx === -1 ? fullAddress : fullAddress.slice(0, idx).trim();
}

/** LocalBusiness schema for a single listing — only includes rating/review fields
 * when we actually have real values, per the brief's rule against fabricated
 * aggregateRating. */
export function localBusinessJsonLd(listing: Listing, url: string) {
  const block: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    name: listing.name,
    address: {
      '@type': 'PostalAddress',
      streetAddress: streetOnly(listing.address),
      addressLocality: listing.city,
      addressRegion: stateAbbr(listing.state),
      postalCode: listing.postal_code ?? undefined,
      addressCountry: 'US',
    },
    url,
  };
  if (listing.phone) block.telephone = listing.phone;
  if (listing.website) block.sameAs = listing.website;
  if (listing.lat != null && listing.lng != null) {
    block.geo = { '@type': 'GeoCoordinates', latitude: listing.lat, longitude: listing.lng };
  }
  if (listing.rating != null && listing.review_count != null && listing.review_count > 0) {
    block.aggregateRating = {
      '@type': 'AggregateRating',
      ratingValue: listing.rating,
      reviewCount: listing.review_count,
    };
  }
  return block;
}

export function itemListJsonLd(listings: Listing[], baseUrl: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    itemListElement: listings.map((listing, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      url: new URL(`/listing/${listing.slug}/`, baseUrl).toString(),
      name: listing.name,
    })),
  };
}
