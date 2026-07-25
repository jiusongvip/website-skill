---
name: seo-site-verifier
description: >
  SEO Site Verifier — post-build quality gate for Astro content sites.
  After seo-site-builder finishes generating a site, this skill runs the
  global seo-* audit skills (technical, schema, content, page) against
  the built site and produces a consolidated fix list.
  This is the VERIFICATION layer — it answers "does this site pass SEO
  quality standards before launch?"
  Automatically triggered by seo-pipeline-orchestrator after Phase 3 (Build).
  Can also be used standalone: "帮我审核刚建好的站"
---

# SEO Site Verifier

## Why this skill exists

`seo-site-builder` generates the code. But code that compiles is not code that ranks.
This skill closes the loop: build → audit → fix → launch.

It delegates to the global `seo-*` audit skills installed at
`C:\Users\nec10\.agents\skills\seo-*/` (from the AgriciDaniel/claude-seo repo).

---

## Input

### Required

- **Site URL** — where the site is running (local preview or deployed)
  - Local: `http://localhost:4321` (Astro default)
  - Deployed: `https://example.com`
- **Project directory** — path to the Astro project root (for file-level fixes)

### Optional

- **Audit scope** — which checks to run (default: all 4 core)
- **Design direction** — passed through for visual consistency fixes

---

## Pipeline

### Phase 1: Technical SEO Audit

Run `/seo technical <url>` (from global `seo-technical` skill).

Checks:
- robots.txt exists and allows crawling
- Sitemap exists and is valid
- Canonical URLs are set (self-referencing)
- No `noindex` on important pages
- Title tags: present, unique, 50-60 chars
- Meta descriptions: present, unique, 150-160 chars
- H1: single per page, contains keyword
- Heading hierarchy (no skipped levels)
- HTTPS enforced (if deployed)
- Viewport meta tag correct
- Core Web Vitals (LCP < 2.5s, CLS < 0.1, INP < 200ms)

Output: `data/verification-technical.md`

### Phase 2: Schema Audit

Run `/seo schema <url>` (from global `seo-schema` skill).

Checks:
- Organization schema present and valid
- WebSite schema with searchAction (if site has search)
- Article/BlogPosting schema on content pages
- BreadcrumbList schema on all pages
- FAQPage schema on FAQ sections
- No deprecated schema types
- JSON-LD format (preferred)
- All @id references resolve correctly

Output: `data/verification-schema.md`

### Phase 3: Content Quality Audit

Run `/seo content <url>` (from global `seo-content` skill).

Checks:
- E-E-A-T signals: author attribution, dates, citations
- Keyword presence: primary keyword in H1, first 100 words, at least one H2
- Content length meets page type minimums
- Internal linking: 3-5 links per 1000 words, descriptive anchor text
- No thin content pages
- No duplicate content across pages
- Readability appropriate for target audience

Output: `data/verification-content.md`

### Phase 4: Single-Page Deep Check

Run `/seo page <url>` on the 3 most important pages:
1. Homepage (`/`)
2. Primary pillar page (from PRD)
3. A representative article page

Output: `data/verification-pages.md`

### Phase 5: Consolidated Report

Combine all findings into a single action document:

```markdown
# SEO Verification Report: {site-name}

## Summary
| Check | Status | Issues |
|-------|--------|--------|
| Technical SEO | ✅/⚠️/❌ | N critical, M warnings |
| Schema Markup | ✅/⚠️/❌ | N critical, M warnings |
| Content Quality | ✅/⚠️/❌ | N critical, M warnings |
| Page-level | ✅/⚠️/❌ | N critical, M warnings |

## Must Fix (Launch Blockers)
1. {issue} — {file}:{line} — {fix instruction}
2. ...

## Should Fix (Before Next Sprint)
1. {issue} — {fix instruction}
2. ...

## Nice to Have
1. {suggestion}
2. ...

## Score: {X}/100
```

### Phase 6: Auto-Fix (Optional)

For fixable issues in the local project, apply corrections:
- robots.txt: write missing directives
- Missing meta tags: add to BaseLayout.astro or SEO component
- Broken canonical: fix astro.config.mjs site URL
- Missing alt text: add to images
- Schema issues: fix in SEO component or schema components

---

## Output

```
{project-dir}/
└── data/
    ├── verification-technical.md
    ├── verification-schema.md
    ├── verification-content.md
    ├── verification-pages.md
    └── verification-report.md       ← consolidated, actionable
```

---

## Priority Rules

| Condition | Action |
|-----------|--------|
| Site is localhost (not deployed) | Skip HTTPS check, skip external API enrichment |
| Site has < 5 pages | Skip pagination/bulk checks |
| Critical issues == 0 | Pass: report is green, ready to launch |
| Critical issues > 0 | Block: report must be resolved before launch |
| Warnings > 10 | Flag: schedule cleanup sprint |

---

## What NOT to do

- Do NOT modify the site without reporting first (report → fix, not fix → report)
- Do NOT run checks that require deployed URLs on localhost sites
- Do NOT guess schema — use the global `seo-schema` skill's detection
- Do NOT rewrite content — flag issues for `content-writer` to fix
- Do NOT deploy if critical issues remain
- Do NOT skip this phase — verification is mandatory before launch
