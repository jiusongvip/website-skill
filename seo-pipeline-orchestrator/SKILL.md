---
name: seo-pipeline-orchestrator
description: >
  SEO Pipeline Orchestrator — chains the entire content-site pipeline from
  keyword research CSV to deployed Astro website in one flow.
  Steps: Vision Definition → Site Analyzer → PRD Builder → Site Builder → Content Writer.
  Use this when you have SEMrush CSV files and want to go from raw keyword data
  to a complete, production-ready Astro website without manual handoffs.
  This is the ORCHESTRATION layer — it delegates to specialized sub-skills
  and manages the document handoffs between them.
---

# SEO Pipeline Orchestrator

## Why this skill exists

This is the **orchestration layer** that chains the entire content-site pipeline:

```
               ┌─────────────────┐
               │  Vision Definer  │  ← 先定义问题：帮谁？解决什么？为什么值得用？
               └────────┬────────┘
                        │ data/vision.md
               ┌────────▼────────┐
               │ seo-site-analyzer│  ← CSV → 战略分析（11-section 文档）
               └────────┬────────┘
                        │ data/{keyword}-analysis.md
               ┌────────▼────────┐
               │ seo-prd-builder  │  ← 分析 → 产品 PRD
               └────────┬────────┘
                        │ data/PRD-{topic}.md
               ┌────────▼────────┐
               │ seo-site-builder  │  ← PRD → Astro 网站代码
               └────────┬────────┘
                         │ {KEYWORD_FOLDER}/
               ┌────────▼────────┐
               │ content-writer (×N)│  ← 批量填充文章内容
               └────────┬────────┘
                        │ filled articles
               ┌────────▼────────┐
               │  Verification    │  ← astro check + build + review
               └─────────────────┘
```

Without this skill, the user must manually run 5+ skills in sequence and manage
document handoffs between them. This skill does it in one command.

---

## Input

### Required

- **One or more SEMrush CSV files** — named `新词_{keyword}.csv` or `{keyword}.csv`
- **The main keyword** (e.g. "tesla charging guide", "china massage")

### Optional

- **Target audience** — description of who the site serves
- **Core value proposition** — what problem the site solves
- **Site type preference** — e.g. "content site", "local service", "hybrid", "affiliate"
- **Design direction** — e.g. "editorial calm", "premium consumer", "minimalist"
- **Design dials override** — `DESIGN_VARIANCE`, `MOTION_INTENSITY`, `VISUAL_DENSITY`
- **Design skill path** — defaults to design-taste-frontend

---

## Pipeline

### Phase 0: Problem Definition (Vision Definer)

**Before touching keywords**, define the site's foundation:

1. **Who is it for?** — Describe target reader in detail
   - Demographics, pain points, what they search for, what they need
2. **What problem does it solve?** — Core value proposition in one sentence
3. **Why is it worth using?** — Differentiation from existing sites
4. **Content boundaries** — What is in scope vs out of scope
5. **Target columns/sections** — List 4-8 content categories
6. **First 5 pages** — Tentative page titles to validate with keyword data

Output: `data/vision.md` — a brief one-page document.

Use user-provided audience and value prop if given. If not, infer from the CSV keywords:
- If keywords include "near me" + city names → target is local searchers looking for services
- If keywords include "what is", "how to", "benefits" → target is informational learners
- If keywords include "best", "vs", "review" → target is commercial buyers

**If the user has not thought about these questions, ask them before proceeding.**

### Phase 1: Analyze (seo-site-analyzer)

Call `seo-site-analyzer` with:
- Keyword from CSV filename
- CSV file content
- Optional site type from Phase 0

Expected output: `data/{keyword}-analysis.md` (11-section analysis document)

### Phase 2: PRD (seo-prd-builder)

Call `seo-prd-builder` with the analysis document from Phase 1.

Expected output: `data/PRD-{topic}.md` (7-section product PRD)

### Phase 3: Build (seo-site-builder)

Call `seo-site-builder` with:
- PRD document from Phase 2 (at `data/PRD-{topic}.md`)
- Project name (derived from keyword)
- Design direction from Phase 0 (or inferred)

The project IS the keyword folder itself. The Astro project is initialized directly in `{KEYWORD_FOLDER}/`.

Use the Astro MCP server (`Astro docs`) to verify integration APIs.

**Build standards are baked in:** seo-site-builder now includes audit-driven standards for Technical SEO (SSR metadata, CWV, images, schema) derived from `C:\Users\nec10\.agents\skills\seo-technical\SKILL.md`, `seo-schema\SKILL.md`, `seo-images\SKILL.md`, and `seo-page\SKILL.md`. Code is generated to pass these audits at build time, not fixed after.

Expected output: Complete Astro project directory

### Phase 4: Write Content (content-writer × Batch)

For each P0/P1 page in the PRD's page inventory:

Call `content-writer` with the page's content brief from the PRD.

**Important:** content-writer now integrates:
1. `C:\Users\nec10\.agents\skills\seo-content\SKILL.md` as a quality gate — every article is auto-audited for E-E-A-T (XX/25 per factor), Content Quality Score (XX/100), and AI Citation Readiness (XX/100)
2. `C:\Users\nec10\.agents\skills\seo-geo\SKILL.md` standards — answer blocks 134-167 words, direct answer in first 40-60 words, question-based H2s
3. Readability (Flesch 60-70), freshness (<3 months for AI visibility), and specific-stat requirements

Audit score is appended to the output. Any factor <15/25 or AICR <60/100 triggers revision.

Generate content for pages in priority order:
1. P0 pages (foundation) — pillar pages, key guides
2. P1 pages (expansion) — cluster articles, category pages
3. P2+ pages (optional) — commercial pages, advanced topics

### Phase 5: Build Verification

Run build validation:
```bash
cd {KEYWORD_FOLDER}
npx astro check
npx astro build
```

Verify checklist:
- [ ] `astro check` passes with no errors
- [ ] `astro build` completes successfully
- [ ] All PRD page URLs exist in the built output
- [ ] Navigation works (no broken links)
- [ ] Sitemap includes all expected pages
- [ ] RSS feed is valid
- [ ] Homepage loads and looks correct

### Phase 6: SEO Audit (seo-site-verifier)

After the build passes, run SEO quality gates using `seo-site-verifier`:

Call `seo-site-verifier` with:
- Site URL: `http://localhost:4321` (preview server)
- **Project directory** — `./{KEYWORD_FOLDER}`

This runs 4 audits in sequence:
1. Technical SEO (robots, sitemap, canonicals, meta, CWV)
2. Schema markup (Organization, Article, BreadcrumbList, FAQ)
3. Content quality (E-E-A-T, keywords, internal links)
4. Page-level deep check (homepage, pillar, article)

Output: `data/verification-report.md`

**If critical issues found** → stop, report, fix, re-run.
**If no critical issues** → site is ready for launch.

---

## Output

### Summary Document: `data/pipeline-{keyword}-report.md`

A one-page report summarizing the full pipeline:

```markdown
# Pipeline Report: {keyword}

## Vision
- Target user: ...
- Core problem: ...
- Content columns: ...
- Design direction: ...

## Analysis Summary
- Total keywords: ...
- Site type: ...
- Recommended pages: ...

## Build Output
- Project: ./{KEYWORD_FOLDER}
- Pages generated: ...
- P0 pages: ...
- P1 pages: ...

## Verification
- astro check: ✅
- astro build: ✅
- Sitemap URLs: ...

## Next Steps
- Content to fill: ...
- Pages to add next: ...
- Launch checklist: ...
```

### Tangible Deliverables

```
{workspace}/
└── {KEYWORD_FOLDER}/                       ← keyword folder = Astro project root
    ├── data/                               ← all analysis, planning & verification docs
    │   ├── vision.md                              ← Phase 0
    │   ├── {keyword}-analysis.md                  ← Phase 1
    │   ├── PRD-{topic}.md                         ← Phase 2
    │   ├── pipeline-{keyword}-report.md           ← This file
    │   ├── verification-technical.md              ← Phase 6
    │   ├── verification-schema.md
    │   ├── verification-content.md
    │   ├── verification-pages.md
    │   └── verification-report.md
    ├── src/
    │   ├── layouts/
    │   ├── pages/
    │   ├── components/
    │   ├── content/
    │   ├── data/                           ← static JSON (site-nav.json etc.)
    │   └── styles/
    ├── public/
    ├── astro.config.mjs
    └── package.json
```

---

## Phase Priority Rules

| Phase | Condition | Action |
|-------|-----------|--------|
| Phase 0 | User has clear audience + value | Skip Q&A, write vision.md directly |
| Phase 0 | User is unsure | Ask 3 questions max, then infer from CSV |
| Phase 1 | CSV has < 50 keywords | Full analysis |
| Phase 1 | CSV has 50-200 keywords | Full analysis, auto-cluster |
| Phase 2 | Analysis shows clear site type | Full PRD |
| Phase 2 | Analysis is ambiguous | Flag in PRD as open question |
| Phase 3 | PRD has 10+ pages | Batch: templates first, then individual pages |
| Phase 3 | PRD has < 10 pages | Generate all pages in one pass |
| Phase 4 | P0 pages > 5 | Batch content-writer calls (3 at a time) |
| Phase 4 | P0 pages ≤ 5 | All at once |

---

## What NOT to do

- Do NOT skip Phase 0 (Vision Definition) — this is the most important step
- Do NOT run phases out of order (each depends on the previous output)
- Do NOT modify the intermediate documents — pass them as-is
- Do NOT generate duplicate content for the same keyword
- Do NOT deploy without running verification
- Do NOT mix multiple sites into one project
- Do NOT override the sub-skills' logic — delegate, don't micromanage
- Do NOT proceed if a sub-skill fails — stop and report the error
