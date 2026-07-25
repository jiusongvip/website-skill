---
name: seo-site-builder
description: >
  SEO Site Builder — takes a Product PRD document + design direction and
  generates a complete, deployable Astro website using design-taste-frontend.
  This is the BUILD layer — reads the PRD and produces the actual code.
  Consumes output from seo-prd-builder and design-taste-frontend.
  ONLY generates Astro sites. NOT for Next.js, generic HTML, or static site generators.
---

# SEO Site Builder

## Why this skill exists

This is the **build layer** of the content-site pipeline:

- **seo-site-analyzer**: keyword data → strategic analysis (what to build, why)
- **seo-prd-builder**: strategic analysis → product-level PRD (how it works)
- **seo-site-builder** (this): product PRD → working Astro website (the actual code)
- **content-writer**: page template → article content

The analyzer and PRD builder produce **documents**. This skill produces **code**.

---

## External Skill Dependencies

| Skill | Path | Usage |
|-------|------|-------|
| **seo-prd-builder** (upstream) | `.agents\seo-prd-builder\SKILL.md` | Input: reads PRD document for page inventory, templates, priorities |
| **design-taste-frontend** (design) | `C:\Users\nec10\.agents\skills\design-taste-frontend\SKILL.md` | All design decisions: three-dial config, layout rules, typography, color, motion. **This is the SOLE design source.** |
| **content-writer** (downstream) | `.agents\content-writer\SKILL.md` | Post-build: fills article content into generated page templates |

---

## Input

### Required: PRD Document

A Product PRD file from `seo-prd-builder` — Markdown with these sections:
- Page Templates (page type specs with hero, H2 skeleton, modules, schema)
- Page Inventory (URL → page type → priority)
- User Flows
- Functional Specs (CMS/template system, APIs, tracking)
- Design Constraints (content-first vs conversion-first, mobile-first vs desktop-first)
- Product Priorities (P0/P1/P2/P3 phases)

### Required: Keyword

- `KEYWORD_FOLDER`: the keyword folder which IS the project directory, e.g. `china-massage`
- `PRIMARY_KEYWORD`: the main keyword, e.g. "china massage"

The PRD is read from `data/PRD-{topic}.md` inside `{KEYWORD_FOLDER}`.
The Astro project is initialized directly in `{KEYWORD_FOLDER}/`.

### Optional: Design Config

Override the default three-dial system from `design-taste-frontend`:
- `DESIGN_VARIANCE`: 1-10 (default 6)
- `MOTION_INTENSITY`: 1-10 (default 4)
- `VISUAL_DENSITY`: 1-10 (default 4)

Or a free-form design direction: "editorial, warm monochrome, calm"

---

## Pipeline

### Phase 0: Project Scaffold

Create the keyword folder and initialize the Astro project directly inside it:

```bash
New-Item -ItemType Directory -Path "{KEYWORD_FOLDER}" -Force
New-Item -ItemType Directory -Path "{KEYWORD_FOLDER}/data" -Force
Set-Location -LiteralPath "{KEYWORD_FOLDER}"
npx create-astro@latest . -- --template basics --no-install
Add-Content -Path ".gitignore" -Value "`ndata/"
```

Then install dependencies:
- `@astrojs/react` — for interactive components
- `@astrojs/sitemap` — SEO sitemap generation
- `@astrojs/rss` — RSS feed
- `tailwindcss` + `@tailwindcss/vite` — styling (v4)
- `motion` — animations (formerly framer-motion)
- `@fontsource/{font}` — self-hosted fonts (no Google Fonts CDN)
- `@phosphor-icons/react` — icons
- `@astrojs/mdx` — if PRD requires MDX content

**Use the Astro MCP server** (`Astro docs`) to verify the latest API for each integration. Do not guess import paths or config options.

For content sites, use these recommended design-taste-frontend dial values:

| Dial | Content Site | Local/Service | Commercial |
|------|-------------|---------------|------------|
| DESIGN_VARIANCE | 5-6 | 4-5 | 6-7 |
| MOTION_INTENSITY | 3-4 | 4-5 | 5-6 |
| VISUAL_DENSITY | 3-4 | 5-6 | 4-5 |

### Phase 1: Design System

**Do NOT write your own design rules here.** Load and follow `design-taste-frontend` (at `C:\Users\nec10\.agents\skills\design-taste-frontend\SKILL.md`) for all design decisions — typography, color, layout, motion, and content-site layout rules (hero stack discipline, eyebrow restraint, section-repetition bans, etc.).

**Key rules to enforce from design-taste-frontend:**
- Self-host fonts via `@fontsource`, NEVER Google Fonts CDN
- Use Geist / Outfit / Satoshi (not Inter by default)
- Grid over flex math: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`
- `min-h-[100dvh]` instead of `min-h-screen`
- No purple/AI gradients (The Lila Ban)
- Max 1 accent color, saturation < 80%
- Implement dark mode via `prefers-color-scheme` + Tailwind `dark:` variant

### Phase 2: Read PRD & Decide Architecture

Read the PRD document. Based on the page inventory and page templates defined in the PRD, decide the project architecture yourself:

- **Layouts**: What layout layers does the site need? Decide based on PRD page types.
- **Pages**: Follow the PRD's URL structure exactly. Generate pages matching the page inventory.
- **Components**: Create components based on PRD page templates (hero specs, H2 skeletons, modules). Name them for this project's domain, not generic names.
- **Content**: Set up content collections matching PRD content types. The schema should reflect PRD's content fields.

**DO NOT reuse the same architecture pattern across projects.** Each site gets its own layout structure, component naming, and content organization based on what the PRD actually needs.

### Phase 3: Build Standards (Quality Rules)

These rules apply to every site regardless of architecture. Enforce at code-generation time.

#### Technical SEO

| Rule | Implementation |
|------|---------------|
| SSR metadata in initial HTML, never JS-injected | SEO component in layout head |
| Self-referencing canonical URL, absolute | Each page: `<link rel="canonical" href="...">` |
| Title 50-60 chars, contains primary keyword | Pass as prop to SEO component |
| Meta description 150-160 chars, includes keyword + value prop | Same |
| Exactly 1 H1 per page, contains primary keyword | Enforce in page template |
| No skipped heading levels (H1→H2→H3, never H1→H3) | Review each page |
| Hyphenated, lowercase, descriptive URLs, trailing slash consistent | `astro.config.mjs` `trailingSlash: 'always'` |
| robots.txt allows crawling, references sitemap | Generate in public/ |
| Viewport meta tag | `width=device-width, initial-scale=1` |
| Mobile touch targets ≥48x48px | `min-h-12 min-w-12` |
| Body font ≥16px | Default `text-base` |

#### Core Web Vitals

| Metric | Target | How |
|--------|--------|-----|
| LCP <2.5s | `fetchpriority="high"` on hero image, preload hero font, `@fontsource` self-hosted |
| INP <200ms | Transform/opacity animations only, code-split React islands |
| CLS <0.1 | `width` + `height` on ALL `<img>` (or `aspect-ratio` CSS) |

**Image pattern (CLS prevention):**
```astro
<!-- Always set width + height -->
<img src={img.src} alt={alt} width="1200" height="630" decoding="async" />
```

#### Images

| Rule | Standard |
|------|----------|
| Format | WebP default; use `<picture>` chain: AVIF → WebP → JPEG fallback |
| Alt text | Present on every `<img>`, 10-125 chars, descriptive + keyword-natural. `role="presentation"` ONLY for decorative |
| Width + Height | Always set (CLS prevention). Never omit |
| Fetch priority | `fetchpriority="high"` on hero/LCP only; omit on below-fold |
| Lazy loading | `loading="lazy"` on below-fold only. **Never** lazy-load hero |
| Filename | `kebab-case-descriptive.webp`, lowercase, no special chars |

#### Schema Markup

| Rule | Standard |
|------|----------|
| Format | JSON-LD only. Never Microdata or RDFa |
| URLs | Absolute only (`https://site.com/page`, not `/page`) |
| Active types | Organization, WebSite, Article/BlogPosting, BreadcrumbList, FAQPage |
| Deprecated (never use) | HowTo, SpecialAnnouncement, ClaimReview |
| Per-page | BreadcrumbList on every page. Article on content pages. Organization globally. |

#### Security Headers

Generate `public/_headers` (for Netlify) or equivalent:

```
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### Phase 4: Configuration Files

#### `astro.config.mjs`

```javascript
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://{PROJECT-URL}.com',
  trailingSlash: 'always',
  integrations: [react(), sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
```

Verify integration APIs using Astro MCP server before writing config.

#### `package.json` scripts

```json
{
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "lint": "astro check"
  }
}
```

#### `tsconfig.json` — strict mode

#### `public/robots.txt`

```
User-agent: *
Allow: /
Sitemap: https://{PROJECT-URL}/sitemap-index.xml
```

#### `public/llms.txt`

AI crawler directive file. List key content URLs.

### Phase 5: Styling (Tailwind v4)

Set up `src/styles/global.css` with `@import "tailwindcss"`. Define theme tokens based on PRD design constraints + design-taste-frontend dials.

### Phase 6: Content Seed

Generate initial content files from PRD's page inventory for P0 pages. Match content types to the PRD's content model.

```markdown
---
title: "{Page Title}"
description: "{Meta description}"
published: {YYYY-MM-DD}
---

{If PRD includes content brief, write full article content.
 Otherwise, create a structured outline with <!-- TODO: --> placeholders
 for the content-writer skill to fill.}
```

### Phase 7: Sitemap & RSS

Sitemap is auto-generated by `@astrojs/sitemap`.

RSS endpoint at `src/pages/rss.xml.js`:
```javascript
import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const articles = await getCollection('articles');
  return rss({
    title: '{Site Title}',
    description: '{Site Description}',
    site: context.site,
    items: articles.map((a) => ({
      title: a.data.title,
      pubDate: a.data.published,
      description: a.data.description,
      link: `/${a.collection}/${a.slug}/`,
    })),
  });
}
```

### Phase 8: Verification

Before declaring complete, run:

```bash
cd {KEYWORD_FOLDER}
npx astro check          # Type-check and lint
npx astro build          # Production build
```

Verify:
- [ ] All PRD page URLs resolve (no 404s)
- [ ] Dark mode renders correctly
- [ ] Sitemap includes all pages
- [ ] RSS feed is valid XML
- [ ] SEO meta tags present on every page
- [ ] No Google Fonts CDN links
- [ ] Structured data validatable (Schema.org)

---

## What NOT to do

- Do NOT use Next.js, Remix, or any non-Astro framework
- Do NOT use Google Fonts CDN (`<link>` tags)
- Do NOT create duplicate pages (one URL = one file)
- Do NOT generate placeholder or lorem ipsum content — use `<!-- TODO -->` if content is pending
- Do NOT guess Astro integration APIs — use the Astro MCP server
- Do NOT ship without running `astro check` and `astro build`
- Do NOT write PRD or analysis — this skill only writes code
- **Do NOT reuse the same project architecture from a previous site.** Each site gets its own layout structure, component organization, and naming conventions based on the PRD.
