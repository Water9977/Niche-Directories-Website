import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Astro integration: after build, remove any URL from the generated
 * sitemap whose actual built HTML carries a noindex robots meta tag.
 *
 * Added 2026-09-12 after AdSense flagged the site and, separately, we found
 * `/quote-sent/` was `noindex` in BaseLayout but still listed in
 * sitemap-index.xml — a real contradiction (a URL search engines are told
 * not to index, submitted to them anyway as "here, index this").
 *
 * The root problem isn't that one page — it's that `noindex` is set as a
 * per-page prop in BaseLayout with nothing keeping the sitemap in sync. A
 * manually maintained exclude-list would just move the same bug one file
 * over: someone adds a `noindex` page later, forgets the list, same
 * contradiction. So instead of a list, this reads the real signal — the
 * `<meta name="robots" content="noindex...">` tag actually present in each
 * built HTML file — directly from `dist/` after the build, and strips any
 * matching URL out of every `sitemap-*.xml` file. It cannot go stale,
 * because it isn't tracking a second copy of the truth; it's reading the
 * same one Google's crawler reads.
 */
export default function pruneNoindexFromSitemap() {
  return {
    name: 'prune-noindex-from-sitemap',
    hooks: {
      'astro:build:done': async ({ dir, logger }) => {
        const distDir = fileURLToPath(dir);
        const noindexPaths = collectNoindexPaths(distDir);

        const log = (msg) => (logger?.info ? logger.info(msg) : console.log(`[prune-noindex-from-sitemap] ${msg}`));

        if (noindexPaths.size === 0) {
          log('no noindex pages found in dist/ — nothing to prune');
          return;
        }

        const sitemapFiles = fs
          .readdirSync(distDir)
          .filter((f) => /^sitemap-\d+\.xml$/.test(f));

        if (sitemapFiles.length === 0) {
          log('no sitemap-*.xml files found — is @astrojs/sitemap registered before this integration?');
          return;
        }

        let prunedTotal = 0;
        const prunedUrls = [];
        for (const file of sitemapFiles) {
          const full = path.join(distDir, file);
          const xml = fs.readFileSync(full, 'utf-8');
          const { result, pruned } = pruneXml(xml, noindexPaths, prunedUrls);
          if (pruned > 0) {
            fs.writeFileSync(full, result, 'utf-8');
            prunedTotal += pruned;
          }
        }

        if (prunedTotal > 0) {
          log(`removed ${prunedTotal} noindex URL(s) from the sitemap: ${prunedUrls.join(', ')}`);
        } else {
          log(`found ${noindexPaths.size} noindex page(s) but none were present in the sitemap already`);
        }
      },
    },
  };
}

/** Every built HTML file under distDir whose actual meta robots tag says
 * noindex, as the URL pathname it will appear under in the sitemap. */
function collectNoindexPaths(distDir) {
  const noindex = new Set();
  const robotsNoindexRe = /<meta\s+name=["']robots["']\s+content=["'][^"']*noindex[^"']*["']/i;

  walk(distDir, (filePath) => {
    if (!filePath.endsWith('.html')) return;
    const html = fs.readFileSync(filePath, 'utf-8');
    if (!robotsNoindexRe.test(html)) return;

    let rel = path.relative(distDir, filePath).split(path.sep).join('/');
    if (rel.endsWith('/index.html')) {
      rel = rel.slice(0, -'index.html'.length);
    } else if (rel.endsWith('.html')) {
      rel = rel.slice(0, -'.html'.length) + '/';
    }
    noindex.add('/' + rel.replace(/^\/+/, ''));
  });

  return noindex;
}

function walk(dir, onFile) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, onFile);
    else onFile(full);
  }
}

function pruneXml(xml, noindexPaths, prunedUrls) {
  let pruned = 0;
  const result = xml.replace(/<url>[\s\S]*?<\/url>/g, (block) => {
    const m = block.match(/<loc>([^<]+)<\/loc>/);
    if (!m) return block;
    let pathname;
    try {
      pathname = new URL(m[1]).pathname;
    } catch {
      return block;
    }
    if (noindexPaths.has(pathname)) {
      pruned++;
      prunedUrls.push(pathname);
      return '';
    }
    return block;
  });
  return { result, pruned };
}
