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

/** LocalBusiness schema for a single listing. */
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
  // No aggregateRating on purpose (2026-11-18): the rating is Google's, from reviews this
  // site did not collect, and Google's review-snippet policy does not allow marking up
  // third-party ratings. The rating is still shown, labelled as Google's, on the page.
  return block;
}

/** WebPage with a dateModified that matches the "prices last checked" date printed on the page. */
export function webPageJsonLd(name: string, url: string, dateModified: string) {
  return { '@context': 'https://schema.org', '@type': 'WebPage', name, url, dateModified };
}

/** Trim text to at most `max` characters, cutting at a word boundary and
 * adding an ellipsis only when something was actually cut. Used for titles and
 * meta descriptions that embed a business name: a handful of real names are
 * very long ("Awesome Entertainment Party Rentals Columbus Cincinnati
 * Cleveland Ohio") and pushed listing titles to 98 characters and
 * descriptions to 204 in the 2026-09-19 crawl. */
export function clampText(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max - 1);
  const lastSpace = cut.lastIndexOf(' ');
  const base = lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut;
  return `${base.replace(/[\s,;:.\-–—]+$/, '')}…`;
}

/** FAQPage markup — Google no longer shows visual FAQ rich results, but this
 * markup measurably lifts citation rates in AI Overviews/ChatGPT/Perplexity
 * (the channel llms.txt + the robots.txt AI-crawler allowlist already target).
 * Answers must be the same text the page visibly renders. */
export function faqPageJsonLd(faqs: { q: string; a: string }[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  };
}

/** Site-level identity for the homepage — the one page that had no JSON-LD
 * at all. Establishes the WebSite/Organization entity for knowledge-graph
 * and AI systems. */
export function siteJsonLd() {
  return [
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'EventRentalCosts.com',
      url: SITE,
      description:
        'Independent comparison directory of real, published party and event rental pricing (tents, tables, chairs) across US metro areas.',
    },
    {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: 'EventRentalCosts.com',
      url: SITE,
      logo: `${SITE}/og-image.png`,
    },
  ];
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
