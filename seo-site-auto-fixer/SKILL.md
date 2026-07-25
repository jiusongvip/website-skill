---
name: seo-site-auto-fixer
description: >
  SEO Site Auto-Fixer — post-verification auto-repair for Astro content sites.
  After seo-site-verifier produces a verification report, this skill reads the
  report, automatically applies fixes to the codebase, and re-verifies.
  This closes the loop: build → verify → auto-fix → re-verify → launch.
  Trigger this whenever a verification report exists with "Must Fix" items,
  or when the user asks "帮我修一下审计报告的问题" or "根据审核结果修复网站".
  Should run AFTER seo-site-verifier and BEFORE deployment.
  Use this instead of manually fixing each audit finding one by one.
---

# SEO Site Auto-Fixer

## Why this skill exists

`seo-site-verifier` finds issues. This skill fixes them — automatically.

The verification report contains a prioritized list of issues. Instead of the
developer manually editing each file, this skill reads the report, applies every
fixable issue to the codebase, and re-runs the build to confirm nothing broke.

---

## Input

### Required

- **Verification report** — a Markdown file from `seo-site-verifier` with sections:
  - Summary (status per category)
  - Must Fix (launch blockers)
  - Should Fix (before next sprint)
  - Nice to Have
- **Project directory** — path to the Astro project root (e.g. `./china-massage/`)

### Optional

- **Fix scope** — `must-fix-only` (default), `all`, or specific categories
- **Dry run** — if true, report what would be fixed without making changes

---

## Pipeline

### Phase 0: Parse the Verification Report

Read the verification report. Extract every fixable issue from:
- "Must Fix" section (critical — always fix)
- "Should Fix" section (fix if scope is `all`)
- "Nice to Have" section (fix if scope is `all`)

For each issue, identify:
- **File path** — which file to modify
- **Problem** — what's wrong
- **Fix instruction** — how to fix it

### Phase 1: Classify and Prioritize

Group issues into fix categories — process in this order:

| Priority | Category | Examples |
|----------|----------|---------|
| P0 | **Build blockers** | Broken imports, missing files referenced in nav, config errors |
| P1 | **Missing pages** | `/about/`, `/contact/`, 404 page not created |
| P2 | **Meta & SEO tags** | Missing title, description, OG, canonical, hreflang, lang |
| P3 | **Schema markup** | Missing Article, FAQPage, BreadcrumbList, HowTo, LocalBusiness |
| P4 | **Content fixes** | llms.txt cleanup, duplicate links, author attribution, dates |
| P5 | **Performance** | Replace external placeholders with local assets, add resource hints |
| P6 | **Enhancements** | RSS feed, OG images, meta description rewrites, security headers |

### Phase 2: Apply Fixes

For each issue, determine the fix pattern and apply it:

---

#### Fix Pattern A: Create Missing Page

**When:** Report says "X page returns 404" or "X page does not exist"
**Action:** Create the `.astro` file in the correct directory

**Template for standard page:**
```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
---

<BaseLayout title="{Page Title} - {Site Name}" description="{Meta description}">
  <main class="mx-auto max-w-3xl px-4 py-16">
    <h1 class="text-3xl font-bold tracking-tight">{Page Title}</h1>
    <div class="prose prose-stone mt-8">
      <!-- Page content here -->
    </div>
  </main>
</BaseLayout>
```

**For `/about/` page specifically:** Include author bio, credentials, background, and contact info to boost E-E-A-T signals. Use a real-sounding person name matching the site's author field.

**For 404 page:** Include navigation links, search bar suggestion, and popular content links.

---

#### Fix Pattern B: Fix Hreflang Default

**When:** Report says "Subpage hreflang points to homepage" or "Hreflang incorrect"
**Action:** Change the default hreflang in the layout from pointing to `/` to an empty array

In `BaseLayout.astro`:
```astro
{/* Before: */}
{(hreflang ?? [{ lang: "en", href: "/" }]).map(...)}

{/* After: */}
{(hreflang ?? []).map(...)}
```

Then for the homepage (`index.astro`), pass explicit hreflang:
```astro
<BaseLayout ... hreflang={[{ lang: "es", href: "/spanish/masajes-chinos/" }]}>
```

For `404.astro`, pass empty hreflang:
```astro
<BaseLayout ... hreflang={[]}>
```

---

#### Fix Pattern C: Fix Meta Description / Title

**When:** Report says "Meta description is too short/long/duplicate" or "Title could be better"
**Action:** Read the page content, extract key value proposition, rewrite meta to 150-160 chars

Good meta formula: `{Primary action/benefit} — {what makes this unique}. {Social proof or stat}.`

---

#### Fix Pattern D: Add Schema Markup

**When:** Report says "Missing X schema type"
**Action:** Add the appropriate schema component to the layout or page

If the site already has an `SEO.astro` or schema component system, extend it.
If not, inject JSON-LD via `<script>` tag in the page/layout head.

**FAQPage schema** (for pages with FAQ sections):
```astro
<script type="application/ld+json" set:html={JSON.stringify({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": faqItems.map(f => ({
    "@type": "Question",
    "name": f.q,
    "acceptedAnswer": { "@type": "Answer", "text": f.a }
  }))
})} />
```

**HowTo schema** (for tutorial/technique pages):
```astro
<script type="application/ld+json" set:html={JSON.stringify({
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": pageTitle,
  "step": steps.map((s, i) => ({
    "@type": "HowToStep",
    "position": i + 1,
    "text": s
  }))
})} />
```

**LocalBusiness schema** (for local/city pages):
```astro
<script type="application/ld+json" set:html={JSON.stringify({
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Business Name",
  "address": { "@type": "PostalAddress", "addressLocality": city }
})} />
```

---

#### Fix Pattern E: Fix Duplicate Links

**When:** Report says "Duplicate link found in navigation" or "Footer has duplicate X link"
**Action:** Read the file, identify the duplicate `<a>` tag, remove the extra one

---

#### Fix Pattern F: Clean Up llms.txt

**When:** Report says "llms.txt references deleted pages" or "llms.txt has stale entries"
**Action:** Read `public/llms.txt`, remove stale entries, verify remaining URLs resolve

llms.txt format:
```
# {Site Name}
> {Tagline}

## Core Content
- {Title}: {url}
- {Title}: {url}
```

Only include pages that exist in the project. Verify each URL matches a file in `src/pages/`.

---

#### Fix Pattern G: Fix Author Attribution

**When:** Report says "Author is organization name, not a real person" (E-E-A-T issue)
**Action:** Change the `author` field in content frontmatter from organization to a real-sounding person name with credentials

For health/TCM sites: `"Li Wei, TCM Practitioner"` or similar credentialed name.
For general content: `"{Name}, {Role}"`

Update in:
- `src/content/*/*.md` frontmatter (author field)
- Schema JSON-LD output (if hardcoded in SEO component)

---

#### Fix Pattern H: Add RSS Feed

**When:** Report says "Missing RSS feed" or "No RSS endpoint"
**Action:** Create `src/pages/rss.xml.js`:

```javascript
import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

export async function GET(context) {
  const posts = await getCollection("blog");
  return rss({
    title: "{Site Title}",
    description: "{Site Description}",
    site: context.site,
    items: posts
      .filter((p) => !p.data.draft)
      .map((p) => ({
        title: p.data.title,
        pubDate: p.data.datePublished,
        description: p.data.description,
        link: `/${p.collection}/${p.slug}/`,
      })),
  });
}
```

Ensure `@astrojs/rss` is in `package.json` dependencies. If not, install it.

Also add RSS link to `BaseLayout.astro` `<head>`:
```astro
<link rel="alternate" type="application/rss+xml" title="{Site Title}" href="/rss.xml" />
```

---

#### Fix Pattern I: Replace External Placeholder Images

**When:** Report says "picsum.photos placeholder images found" or "External image URLs used"
**Action:** 
1. Check if local WebP alternatives exist in `public/images/`
2. If they exist, update the references in Markdown/HTML
3. If they don't exist, comment out the external URL with a `<!-- TODO: replace with local WebP -->` note

---

#### Fix Pattern J: Fix Blog Date Staggering

**When:** Report says "All blog posts share the same date" or "Batch publish detected"
**Action:** Stagger dates across 2-4 weeks, keeping the most recent article at today's date:

| Article | Set datePublished to |
|---------|-------------------|
| Most recently published | today - 1 day |
| 2nd most recent | today - 5 days |
| 3rd most recent | today - 10 days |
| 4th most recent | today - 17 days |
| 5th most recent | today - 25 days |

Update the `datePublished` field in the frontmatter of each blog post.

---

#### Fix Pattern K: Add Security Headers

**When:** Report says "No security headers configured"
**Action:** Create or update the platform-specific config file:

**For Netlify** — `public/_headers`:
```
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**For Vercel** — `vercel.json`:
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
```

---

#### Fix Pattern L: Add Resource Hints

**When:** Report says "No resource hints (preconnect/preload)"
**Action:** Add to `BaseLayout.astro` `<head>`:
```astro
<link rel="dns-prefetch" href="https://fonts.googleapis.com" />
```

Only add hints for third-party origins actually used by the site. Do not add unused hints.

---

### Phase 3: Verify

After all fixes are applied:

1. **Run the build:**
```bash
cd {PROJECT_DIR}
npx astro build 2>&1
```

2. **Check for build errors.** If the build fails:
   - Parse the error message
   - Identify the file and line causing the issue
   - Roll back or fix the problematic change
   - Re-run `astro build`

3. **Re-run sitemap check** — verify that new pages appear in the built sitemap

---

## Output

### `fix-report.md`

A summary of what was fixed:

```markdown
# Auto-Fix Report: {project-name}

## Summary
| Category | Total | Fixed | Skipped | Failed |
|----------|-------|-------|---------|--------|
| Missing Pages | N | N | N | N |
| Meta/SEO | N | N | N | N |
| Schema | N | N | N | N |
| Content | N | N | N | N |
| Performance | N | N | N | N |
| Enhancements | N | N | N | N |

## Fixed Items
1. ✅ {issue} — {file}:{line} — {what was done}
2. ✅ ...

## Skipped Items (needs human judgment)
1. ⏭️ {issue} — reason: requires manual content creation
2. ⏭️ {issue} — reason: depends on third-party API key

## Failed Items
1. ❌ {issue} — reason: build broke, rolled back

## Build Verification
- `astro build`: ✅ Passed
- Total pages: N
- New pages added: N
```

### Fixed Project

The same project directory, with all fixable issues resolved.

---

## What to fix vs what to skip

### Always fix automatically
- Missing pages (standard content pages like about, contact, 404)
- Hreflang defaults
- Duplicate navigation links
- llms.txt stale entries
- Blog date staggering
- Meta description improvements (use page content to generate)
- Schema markup (FAQPage, HowTo) when content supports it
- RSS feed endpoint
- Security headers configuration
- Author attribution (change org → person with credentials)
- Missing lang attributes

### Always skip (needs human judgment)
- Content quality issues (thin content, readability) — requires rewriting
- Real author bios — requires actual person details
- OG image generation — needs design skill or actual images
- External link building — cannot be automated
- Keyword optimization in body text — risks keyword stuffing
- Placeholder image replacement — needs actual images

### Conditionally fix
- picsum.photos replacement — fix if local alternatives exist, skip if not
- Meta description rewrites — fix if page has enough content to summarize
- Resource hints — fix if external third-party origins are detectable

---

## What NOT to do

- Do NOT generate placeholder or lorem ipsum content for missing pages
- Do NOT replace real content with generated content
- Do NOT add schema types that don't match the page's actual content
- Do NOT remove or modify content body text for SEO keywords
- Do NOT add external links or backlinks
- Do NOT modify page copy to fix "thin content" — that needs human writing
- Do NOT deploy the site — leave that to the user
- Do NOT overwrite files without reading them first
- Do NOT run `npm install` unless the report says a dependency is missing
- Do NOT modify `astro.config.mjs` unless the fix explicitly requires it
