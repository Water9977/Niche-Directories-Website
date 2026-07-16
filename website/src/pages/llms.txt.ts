import type { APIRoute } from 'astro';
import { getPublishedMetros } from '../lib/listings';

// llms.txt was a static file in public/ and silently drifted every time a
// metro crossed the publish floor (missed Richmond+Jacksonville once, then
// Charleston+Knoxville+Greenville — same bug twice). Generating it from the
// same data the site builds from means it can never drift again.
export const GET: APIRoute = () => {
  const metros = getPublishedMetros();
  const totalListings = metros.reduce((sum, m) => sum + m.listings.length, 0);

  const metroLines = metros
    .map(
      ({ meta }) =>
        `- [${meta.name} rental prices](https://eventrentalcosts.com/${meta.slug}/)`,
    )
    .join('\n');

  const body = `# EventRentalCosts.com

> Independent comparison directory for party and event equipment rental pricing (tents, tables, chairs) across ${metros.length} US metro areas — ${totalListings} verified companies with real, published pricing.

EventRentalCosts.com collects real, published pricing directly from local rental companies' own websites — not estimates, not aggregator quotes. Each listing shows the actual dollar figures a business has published, the exact source snippet it came from, and the date it was last checked. Companies that don't publish real pricing are not listed with pricing data.

## Key pages
- [Homepage](https://eventrentalcosts.com/): metro-area selector, overview of the comparison methodology
- [How much does tent rental cost?](https://eventrentalcosts.com/tent-rental-cost/): national cost guide built from real cross-metro data
${metroLines}
- [About & Methodology](https://eventrentalcosts.com/about/): exactly how pricing data is collected and verified

## Notes for AI crawlers
- This site is not affiliated with any business it lists.
- Pricing shown is sourced from each business's own website and dated; it can change and should be confirmed directly with the business.
- We do not fabricate reviews, ratings, or pricing. Fields we can't verify are explicitly marked "Not published" rather than assumed to be "No."
- Company order in comparison tables reflects price, not payment — no paid placements exist on this site as of this writing.
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
