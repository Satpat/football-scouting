// Observable Framework hardcodes `maximum-scale=1` in its HTML template
// (node_modules/@observablehq/framework/dist/render.js), which disables pinch-zoom —
// a WCAG 1.4.4 violation. There's no config option to change it, so this strips it
// from the built HTML after `observable build` runs (wired up as an npm postbuild
// hook in package.json — do not call this script directly).
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const DIST = join(dirname(fileURLToPath(import.meta.url)), "..", "dist");
const VIEWPORT_RE = /(<meta name="viewport" content="[^"]*?)(,\s*maximum-scale=1)([^"]*")/;

function walk(dir) {
  let patched = 0;
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) { patched += walk(p); continue; }
    if (!entry.endsWith(".html")) continue;
    const html = readFileSync(p, "utf8");
    const next = html.replace(VIEWPORT_RE, "$1$3");
    if (next !== html) { writeFileSync(p, next); patched++; }
  }
  return patched;
}

const count = walk(DIST);
console.log(`patch-viewport: removed maximum-scale=1 from ${count} file(s) in site/dist`);
