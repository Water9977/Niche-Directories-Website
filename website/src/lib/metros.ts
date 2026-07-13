// Maps the raw `metro` value in the data to clean display metadata + URL slug.
// A metro only gets a page + homepage card once it clears MIN_LISTINGS — this
// enforces the ~5-listing thin-content floor from the SEO research (a metro
// page below it would read as thin and risk dragging down domain-wide quality).
// Metros auto-graduate as data grows; nothing to change here when they cross it.

export const MIN_LISTINGS = 5;

export interface MetroMeta {
  /** Raw value as it appears in listings.json `metro` field. */
  key: string;
  slug: string;
  name: string;
  state: string;
  /** Short, factual local-market context for the page intro. */
  blurb: string;
}

export const METROS: MetroMeta[] = [
  {
    key: 'Charlotte-Concord-Gastonia',
    slug: 'charlotte-nc',
    name: 'Charlotte, NC',
    state: 'NC',
    blurb:
      "Charlotte's wedding and event market moves roughly $508 million a year across an estimated 13,900+ weddings, on top of corporate events, festivals, and backyard parties from NoDa to South End to Ballantyne and the surrounding towns of Concord, Huntersville, Mooresville, Indian Trail, and Monroe.",
  },
  {
    key: 'Raleigh-Durham',
    slug: 'raleigh-durham-nc',
    name: 'Raleigh–Durham, NC',
    state: 'NC',
    blurb:
      'The Raleigh–Durham Triangle — Raleigh, Durham, Cary, Chapel Hill and the surrounding towns — pairs a fast-growing population with a busy university and corporate event calendar, supporting a deep bench of local party and event rental companies.',
  },
  {
    key: 'Indianapolis',
    slug: 'indianapolis-in',
    name: 'Indianapolis, IN',
    state: 'IN',
    blurb:
      'Indianapolis and its ring of suburbs — Carmel, Fishers, Greenwood, Noblesville — host a heavy convention, wedding, and festival calendar year-round, from downtown corporate events to backyard parties across Hamilton County.',
  },
  {
    key: 'Columbus',
    slug: 'columbus-oh',
    name: 'Columbus, OH',
    state: 'OH',
    blurb:
      'Columbus, Ohio and its suburbs — Dublin, Westerville, Grove City, Hilliard — combine a large university population with a steady stream of weddings, corporate events, and community festivals that keep local rental companies busy through the warm months.',
  },
  {
    key: 'Greensboro-Winston-Salem',
    slug: 'greensboro-nc',
    name: 'Greensboro & Winston-Salem, NC',
    state: 'NC',
    blurb:
      'The North Carolina Triad — Greensboro, Winston-Salem, High Point — anchors a mid-size but active event market, with weddings, furniture-market trade events, and community gatherings drawing on a network of local rental companies.',
  },
  {
    key: 'Richmond',
    slug: 'richmond-va',
    name: 'Richmond, VA',
    state: 'VA',
    blurb:
      'Richmond, Virginia and its surrounding counties host a growing wedding and event scene across historic venues and modern spaces.',
  },
  {
    key: 'Jacksonville',
    slug: 'jacksonville-fl',
    name: 'Jacksonville, FL',
    state: 'FL',
    blurb:
      'Jacksonville, Florida — one of the largest cities by land area in the US — supports a large, active rental market spanning beach weddings, corporate events, and year-round outdoor parties across a wide metro footprint.',
  },
  {
    key: 'Pittsburgh',
    slug: 'pittsburgh-pa',
    name: 'Pittsburgh, PA',
    state: 'PA',
    blurb:
      'Pittsburgh, Pennsylvania hosts weddings, corporate events, and community gatherings across its riverfront venues and historic neighborhoods.',
  },
  {
    key: 'Greenville',
    slug: 'greenville-sc',
    name: 'Greenville, SC',
    state: 'SC',
    blurb:
      'Greenville, South Carolina is one of the fastest-growing mid-size cities in the Southeast, with a growing wedding and event scene downtown and across the Upstate.',
  },
];

export function metroBySlug(slug: string): MetroMeta | undefined {
  return METROS.find((m) => m.slug === slug);
}

export function metroByKey(key: string): MetroMeta | undefined {
  return METROS.find((m) => m.key === key);
}
