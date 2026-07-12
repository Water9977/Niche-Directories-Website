import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://eventrentalcosts.com',
  integrations: [sitemap()],
});
