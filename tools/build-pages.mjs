// Generates the two language pages from one template:
//   src/page.html (English copy, written for /en/)  ->  en/index.html
//   src/page.html + src/i18n/ar.json                ->  ar/index.html
//
// Usage: node tools/build-pages.mjs   (also runs as part of `npm run build`)
//
// For the Arabic page:
// - Elements with data-i18n="key" get their text replaced (they must contain text only).
// - data-i18n-attr="attr:key;attr2:key2" replaces those attribute values.
// - <html lang/dir>, canonical, og:url, og:locale, the home link and the
//   language switch's aria-current are adjusted for /ar/.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = readFileSync(join(root, "src", "page.html"), "utf8").replace(/\r\n/g, "\n");
const AR = JSON.parse(readFileSync(join(root, "src", "i18n", "ar.json"), "utf8"));

const DOCTYPE = "<!DOCTYPE html>\n";
if (!src.startsWith(DOCTYPE)) throw new Error("src/page.html must start with <!DOCTYPE html>");

const escapeText = (v) => v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const escapeAttr = (v) => escapeText(v).replace(/"/g, "&quot;");

const used = new Set();
const missing = new Set();
const lookup = (key) => {
  used.add(key);
  if (!(key in AR)) missing.add(key);
  return AR[key];
};

let ar = src;

let textSwaps = 0;
ar = ar.replace(
  /(<([a-z][a-z0-9]*)\b[^>]*\sdata-i18n="([^"]+)"[^>]*>)([^<]*)(<\/\2>)/g,
  (m, open, tag, key, text, close) => {
    textSwaps++;
    const v = lookup(key);
    return v == null ? m : open + escapeText(v) + close;
  },
);
const textMarkers = (src.match(/\sdata-i18n="/g) || []).length;
if (textSwaps !== textMarkers) {
  throw new Error(
    `${textMarkers - textSwaps} data-i18n element(s) were not translated: they must contain plain text only (no child tags)`,
  );
}

ar = ar.replace(/<[a-z][^>]*\sdata-i18n-attr="([^"]+)"[^>]*>/g, (tagSrc, spec) => {
  let t = tagSrc;
  for (const pair of spec.split(";")) {
    const i = pair.indexOf(":");
    const attr = pair.slice(0, i).trim();
    const key = pair.slice(i + 1).trim();
    const v = lookup(key);
    if (v == null) continue;
    const re = new RegExp(`(\\s${attr}=")[^"]*(")`);
    if (!re.test(t)) throw new Error(`attribute ${attr} not found on tag for key ${key}`);
    t = t.replace(re, (_, a, b) => a + escapeAttr(v) + b);
  }
  return t;
});

if (missing.size) {
  throw new Error(`Missing Arabic translations in src/i18n/ar.json: ${[...missing].join(", ")}`);
}
const unused = Object.keys(AR).filter((k) => !used.has(k));
if (unused.length) throw new Error(`Unused keys in src/i18n/ar.json (remove them or use them): ${unused.join(", ")}`);

const swaps = [
  ['<html lang="en" dir="ltr"', '<html lang="ar" dir="rtl"'],
  ['<link rel="canonical" href="https://ryotech.ly/en/">', '<link rel="canonical" href="https://ryotech.ly/ar/">'],
  ['<meta property="og:url" content="https://ryotech.ly/en/">', '<meta property="og:url" content="https://ryotech.ly/ar/">'],
  ['<meta property="og:locale" content="en_US">', '<meta property="og:locale" content="ar_LY">'],
  ['<meta property="og:locale:alternate" content="ar_LY">', '<meta property="og:locale:alternate" content="en_US">'],
  ['data-lang-switch="en" aria-current="page"', 'data-lang-switch="en"'],
  ['data-lang-switch="ar"', 'data-lang-switch="ar" aria-current="page"'],
];
for (const [from, to] of swaps) {
  if (ar.split(from).length !== 2) throw new Error(`expected exactly one occurrence of: ${from}`);
  ar = ar.replace(from, to);
}

const homeLink = /(<a href=")\/en\/("[^>]*data-i18n-attr="aria-label:brand\.home")/;
if (!homeLink.test(ar)) throw new Error("home link (href=\"/en/\" with brand.home) not found");
ar = ar.replace(homeLink, "$1/ar/$2");

const banner = (from) =>
  `${DOCTYPE}<!-- Generated from ${from} by tools/build-pages.mjs. Do not edit by hand; run npm run build. -->\n`;
const write = (dir, html, from) => {
  mkdirSync(join(root, dir), { recursive: true });
  writeFileSync(join(root, dir, "index.html"), html.replace(DOCTYPE, banner(from)));
};

write("en", src, "src/page.html");
write("ar", ar, "src/page.html and src/i18n/ar.json");
console.log(`en/index.html and ar/index.html written (${used.size} Arabic keys)`);
