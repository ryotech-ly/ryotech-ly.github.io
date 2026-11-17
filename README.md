# ryotech.ly

Corporate landing page for **Ryotech** (ريوتك): FinTech, microservices and distributed-systems engineering.

The site is static and bilingual, served by GitHub Pages from this repository:

- **English:** https://ryotech.ly/en/ ([`en/index.html`](en/index.html)), left-to-right.
- **Arabic:** https://ryotech.ly/ar/ ([`ar/index.html`](ar/index.html)), right-to-left.
- **Root:** https://ryotech.ly/ ([`index.html`](index.html)) only redirects: to the language the visitor chose before, otherwise to `/en/`. Without JavaScript it falls back to `/en/`.
- Both language pages are **generated** from one template, [`src/page.html`](src/page.html), and the Arabic dictionary [`src/i18n/ar.json`](src/i18n/ar.json), so search engines index real content in both languages. They are linked with `hreflang` (`x-default` is `/en/`).
- **JavaScript:** only a few lines that remember the visitor's language choice. Both pages work fully without it.
- **Styling:** Tailwind CSS v4, compiled ahead of time into [`assets/css/main.css`](assets/css/main.css). The browser never runs Tailwind.
- **Fonts:** Inter for English and Cairo for Arabic, loaded from Google Fonts.

## Repository layout

| Path | Purpose |
|---|---|
| `src/page.html` | **Single source of the markup**, with the English copy, written for `/en/`. Translatable elements carry `data-i18n` / `data-i18n-attr` keys. |
| `src/i18n/ar.json` | Arabic text for every key. |
| `en/index.html`, `ar/index.html` | **Generated. Do not edit by hand.** Built by `tools/build-pages.mjs` from `src/page.html` (+ `src/i18n/ar.json` for Arabic). Commit them. |
| `index.html` | Root redirect page (`/` to `/en/` or `/ar/`). |
| `404.html` | Bilingual not-found page with no JavaScript. GitHub Pages serves it for unknown paths, so it uses root-absolute asset paths. |
| `src/input.css` | Tailwind entry: design tokens (`ink`, `brand`, `steel`), base layer (Arabic typography, reduced motion), custom utilities. |
| `assets/css/main.css` | **Built file. Commit it.** Rebuild after any change to `src/page.html`, `index.html`, `404.html` or `src/input.css`. |
| `tools/build-pages.mjs` | Generates `en/index.html` and `ar/index.html`; fails if any key has no Arabic translation. |
| `assets/img/` | Logo marks, hero emblem, app icons, social preview, CTA texture. All generated from the brand sources by `tools/generate_assets.py`. |
| `favicon.ico`, `apple-touch-icon.png`, `site.webmanifest` | Icons and manifest. |
| `CNAME` | Custom domain for GitHub Pages: `ryotech.ly`. |
| `.gitattributes` | Forces LF line endings on checkout so the page generator behaves the same on every OS. |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are, without running Jekyll. |
| `robots.txt`, `sitemap.xml` | Crawler hints. Update `<lastmod>` in the sitemap when content changes. |

## Develop

Requires Node 20+ (dependencies are pinned in `package-lock.json`).

```bash
npm ci              # install Tailwind (dev only)
npm run build        # generate en/ and ar/ pages, then compile assets/css/main.css (minified)
npm run build:pages  # only regenerate the two language pages
npm run watch        # recompile CSS on change (run npm run build:pages after copy changes)
python -m http.server 8080   # preview at http://localhost:8080/  (root-absolute paths need a server, not file://)
```

### Editing copy

1. **English and layout:** edit `src/page.html` only. Translatable elements carry `data-i18n="key"` (text only inside them), and translated attributes carry `data-i18n-attr="attr:key"`.
2. **Arabic:** edit the matching key in `src/i18n/ar.json`. Every key used in the markup needs an Arabic entry, or the build fails.
3. **Rebuild:** run `npm run build`. It regenerates `en/index.html`, `ar/index.html` and the CSS. Commit them.

Line-break guards in the copy are invisible:
- Hyphenated English compounds are written `event-&#8288;driven` (a hyphen plus a word joiner), so they never split across lines. A non-breaking hyphen is not used because Inter has no glyph for it.
- `&nbsp;` in the markup and `\u00a0` in `ar.json` keep two words together, for example an em dash with the word before it, or a two-word Arabic term.

Language selection works like this:
- The EN | AR switch is two plain links, `/en/` and `/ar/`.
- `/en/` and `/ar/` never redirect away from what the visitor opened. Each page remembers its own language in `localStorage` (also when restored by the Back button).
- Only the root `/` redirects: to the remembered language, otherwise to `/en/`.
- Old links with `?lang=ar` or `?lang=en` still work on any page: they go to the requested language (`/?lang=ar` → `/ar/`), keeping other query parameters and the `#hash`, even when the browser blocks storage.

### Regenerating images

All images are generated from the two brand sources, a 2048×2048 logo and a 3584×1184 banner. You need Python 3 with Pillow and numpy:

```bash
python tools/generate_assets.py --logo path/to/logo.jpg --banner path/to/banner.jpg
# or through npm; arguments after `--` are passed to the script, and both are required:
npm run assets -- --logo path/to/logo.jpg --banner path/to/banner.jpg
```

The script writes everything under `assets/img/`, plus `favicon.ico` and `apple-touch-icon.png`. It also checks its own output and stops with an error if:
- the cut-out logo no longer matches the original closely enough, or
- the edges of the cut-out are not fully transparent.

### Checks before publishing

```bash
npm run build
npx html-validate index.html en/index.html ar/index.html 404.html
```

## Deploy to GitHub Pages with the custom domain

Do these steps in this order.

1. **Verify the domain for the organisation**, to protect it against takeover.
   1. Go to *Organization settings → Pages → Add a domain* and enter `ryotech.ly`.
   2. Add the TXT record GitHub shows (host `_github-pages-challenge-ryotech-ly`), then click **Verify**.
   3. Keep the record afterwards.
2. **Publish the site.**
   1. Run `npm run build`, then commit everything, including `assets/css/main.css`.
   2. Push to `main` of the public repository `ryotech-ly/ryotech-ly.github.io`.
   3. In the repository, go to *Settings → Pages → Build and deployment*. Set **Source** to *Deploy from a branch*, then choose `main` and `/ (root)`.
3. **Set the custom domain.** In the same Pages settings, enter `ryotech.ly` as the custom domain. The `CNAME` file already contains it.
4. **Configure DNS** at the DNS host for `ryotech.ly`:

   | Type | Name | Value |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | AAAA (optional, IPv6) | `@` | `2606:50c0:8000::153` |
   | AAAA (optional, IPv6) | `@` | `2606:50c0:8001::153` |
   | AAAA (optional, IPv6) | `@` | `2606:50c0:8002::153` |
   | AAAA (optional, IPv6) | `@` | `2606:50c0:8003::153` |
   | CNAME | `www` | `ryotech-ly.github.io` |

   When you set this up:
   - Remove any parking or default A/CNAME records the registrar created for `@` or `www`.
   - Do not add wildcard (`*`) records.
   - If the domain has CAA records, one of them must allow `letsencrypt.org`.
   - If you use Cloudflare, keep these records **DNS only** (grey cloud).
5. **Turn on HTTPS.** Once GitHub has issued the certificate (usually minutes, up to 24 hours), tick **Enforce HTTPS**. If you add `www` later, remove and re-add the custom domain so the certificate covers both names.
6. **Check:** `nslookup ryotech.ly` should return the four `185.199.x.153` addresses.

### Email

The contact buttons use `mailto:contact@ryotech.ly`, so that mailbox must exist.
- Keep the domain's **MX** records when you edit DNS.
- Add **SPF** and **DMARC** records from your email provider, so mail from the domain gets delivered.
