import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import pruneNoindexFromSitemap from './scripts/prune-noindex-from-sitemap.mjs';

import cloudflare from "@astrojs/cloudflare";

export default defineConfig({
  site: 'https://eventrentalcosts.com',
  // pruneNoindexFromSitemap must come after sitemap() — it edits the
  // sitemap-*.xml files sitemap() just wrote, based on the real noindex meta
  // tag in each page's built HTML (see the integration for why: a
  // /quote-sent/ noindex page was still listed in the sitemap, a real
  // contradiction found 2026-09-12).
  integrations: [sitemap(), pruneNoindexFromSitemap()],
  adapter: cloudflare()
});