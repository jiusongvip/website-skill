---
name: seo-prd-builder
description: >
  SEO Product PRD Builder — takes the analysis document from seo-site-analyzer 
  and generates a complete product-level PRD that designers and developers can 
  build from. Covers page-level IA, user flows, functional specs, design 
  constraints, and product priorities. Trigger when the user has an SEO analysis 
  document (the 11-section output from seo-site-analyzer) and wants to turn it 
  into a "可开工的PRD" (buildable product spec). This is the PRODUCT layer — 
  it answers "what does each page look like, how does the user flow, what does 
  the system need to support, and what should we build first?"
---
# SEO Product PRD Builder

## Why this skill exists

This is the **product layer** of a two-skill system:
- **seo-site-analyzer**: keyword data → strategic analysis (what to build, why)
- **seo-prd-builder** (this): strategic analysis → product-level PRD (how it works, what it looks like)

The analyzer answers "what pages and why." This skill answers "what does each page look like, how does the user move through them, what does the system need, and what's the build order."

**This skill does NOT do keyword-level page-inventory decisions** (which pages to build, which keywords to target — that's the analyzer's job). It reads the page inventory from the analyzer's output and builds **page-level architecture** on top: templates, H2 skeletons, modules, schemas, user flows, and functional specs.

---

## Input

The input is an analysis document produced by seo-site-analyzer — a Markdown file with 11 sections. The user provides this file directly.

Read the file and extract:
- **Site type** (Content / Local / Hybrid / Affiliate / Mixed)
- **Page inventory**: for each page listed in Keyword → Page Mapping and Site Architecture:
  - URL
  - Page type (pillar / cluster / local / comparison / commercial / listicle / how-to / benefits / journal)
  - Target keyword
  - Priority (H/M/L)
- **Content types** needed
- **Commercial strategy** (separation plan, monetization model)
- **Growth phases** (0-10, 10-30, 30-60, 60+)

If the input file is missing any of these sections, ask the user to run seo-site-analyzer first.

---

## Pipeline

### Phase 0: Classify Page Types

For each URL in the page inventory, classify it into a **page type template**. Each template has known patterns for content blocks, user flow, and conversion path.

| Page Type | Primary Intent | Key Blocks | Conversion Goal |
|-----------|---------------|------------|-----------------|
| **Pillar / Guide** | Informational (what-is) | Hero + TOC + Content sections + FAQ + Internal link grid | Trust building, cluster discovery |
| **How-to** | Informational (procedural) | Hero + Step list + Media blocks + Tips + CTA | Engagement, next article |
| **Benefits** | Informational (persuasive) | Hero + Benefit cards + Evidence + Comparison + CTA | Consideration, commercial intent |
| **Comparison** | Commercial (A vs B) | Hero + Comparison table + Pros/Cons + Verdict + Affiliate CTA | Conversion |
| **Local / City** | Transactional (near me) | Hero + Map + Listing cards + Reviews + Call CTA + Schema | Lead gen / Phone call |
| **Local hub** | Transactional (directory) | Hero + City list + Filter + Map overview + SEO text | City page distribution |
| **Best-of / Listicle** | Commercial (best X) | Hero + Item cards + Comparison + Price + Affiliate CTA | Affiliate conversion |
| **Product review** | Commercial (buy X) | Hero + Specs + Review + Pros/Cons + Price + Buy button | Affiliate conversion |
| **Journal / Blog** | Informational (long-tail) | Hero + Content + Author + Related posts | Freshness, topical authority |

---

## Page Standards (Audit-Driven)

These rules are derived from the global `seo-*` audit skills (`C:\Users\nec10\.agents\skills\seo-*`). Apply them when defining page templates and content specs.

### Schema Type Mapping (from seo-schema)

Every page type must have correct Schema.org markup. Use JSON-LD format only. **Never use deprecated types.**

| Page Type | Schema Type | Status | Notes |
|-----------|------------|--------|-------|
| Pillar / Guide | Article | ✅ Active | Include author, datePublished, dateModified |
| How-to | Article | ✅ Active (HowTo rich results deprecated, use Article) | Structure steps in H2 list |
| Benefits | Article | ✅ Active | |
| Comparison | Article + Product (if affiliate) | ✅ Active | Product schema only for specific products reviewed |
| Local / City | LocalBusiness (correct industry subtype) | ✅ Active | Include geo with 5+ decimals, openingHours |
| Local hub | WebSite + BreadcrumbList | ✅ Active | |
| Best-of / Listicle | Article + Product (per item) | ✅ Active | |
| Product review | Product + Review | ✅ Active | |
| Journal / Blog | BlogPosting | ✅ Active | Include author, datePublished |
| FAQ section | FAQPage | ⚠️ No rich result (retired May 2026), keep for AI entity resolution | Use QAPage for genuine multi-user Q&A |
| HowTo steps | HowTo | ❌ Deprecated — never use | Use Article with step structure instead |

### Word Count Per Page Type (from seo-content, seo-page)

Set these as minimum content targets in page template specs:

| Page Type | Min Words | Notes |
|-----------|-----------|-------|
| Pillar / Guide | 1,500 | Covers topic comprehensively |
| How-to | 800 | Steps + tips + prerequisites |
| Comparison | 1,200 | Pros/cons + verdict + context |
| Local / City | 500-600 | Unique content per location |
| Local hub | 800 | Area overview + city list |
| Best-of / Listicle | 1,200 | Per-item detail + comparison |
| Product review | 300+ (400+ complex) | Specs + review + verdict |
| Journal / Blog | 1,200 | Timely, fresh perspective |
| Homepage | 500 | Value prop + navigation |

### Multi-Location Guardrails (from seo-local)

If the PRD involves local city pages:
- **30+ pages**: flag warning — each page must have >60% unique content
- **50+ pages**: **HARD STOP** — auto-generation without human oversight will create thin content. Require manual content plan

---

### Phase 1: Page-Level IA

For each page type present in the analysis, define:

#### Hero Section
- Title pattern (include keyword)
- Subtitle / value prop
- Primary CTA (what action, where it leads)
- Hero image/video hint

#### Content Body (H2/H3 skeleton)
- Which subheadings are required vs optional
- What question each H2 answers
- Content type suggestions (text vs table vs media vs quote)

#### Modules
- **FAQ block**: required? which questions?
- **Comparison table**: required? what dimensions?
- **Media block**: images? video? diagram?
- **Map block**: static vs interactive?
- **Review cards**: user review? expert review?
- **Related / Internal links**: auto-generated grid? manual curation?
- **Schema**: which schema types? (Article, FAQPage, LocalBusiness, Product, BlogPosting — never use HowTo)

#### Footer CTA
- What action should the user take after reading?
- Where does the CTA link to?
- Is this a conversion CTA or a content CTA?

### Phase 2: User Flows

Define 3 core user flows based on site type:

#### Flow A: Informational User
```
Google Search (what-is / how-to keyword)
  → Landing on Pillar or Cluster page
  → Reads content, scans FAQ
  → Clicks internal link to related cluster
  → (Optional) Clicks comparison CTA
  → (Optional) Clicks commercial CTA
```

Output: Flow diagram showing page transitions, with key CTAs and decision points labeled.

#### Flow B: Local/Transactional User
```
Google Search ("X near me" keyword)
  → Landing on Local hub or City page
  → Sees map + listing cards
  → Filters by criteria (optional)
  → Clicks listing → sees detail
  → Calls / Books / Gets directions
```

Output: Flow diagram with entry point, filtering, detail view, conversion action.

#### Flow C: Commercial/Comparison User
```
Google Search ("best X" / "X vs Y" keyword)
  → Landing on Comparison or Best-of page
  → Reads comparison / scans products
  → Clicks affiliate link
  → Leaves site
```

Output: Flow diagram showing how commercial traffic flows through to conversion without diluting editorial weight.

For each flow, define:
- Entry point (which searches land here)
- Decision points (what user considers before next click)
- Drop-off risk (where users might leave)
- Conversion action (what success looks like)

### Phase 3: Functional Specs

Define the system requirements to build this site:

#### CMS / Page Generation
- Which pages are **templates** (parameterized, auto-generated)?
  - Local city pages: template with city name, map, listings
  - Comparison pages: template with entities X and Y
  - Listicle pages: template with item list
- Which pages are **hand-crafted content**?
  - Pillar, guides, how-to articles
- **CMS fields needed**: title, H2s, body, FAQ items, related links, schema type, images, CTA

#### APIs & Services
| Service | Usage | Page Types | Priority |
|---------|-------|------------|----------|
| Maps (Google / Mapbox) | Location display, city pages | Local hub, City pages | P0 if local exists |
| Reviews (Google Places / Yelp) | Listing review data | Local, Comparison | P1 |
| Lead form (Typeform / custom) | Booking inquiries | Local city pages | P2 |
| Affiliate (Amazon / ShareASale) | Product links | Best-of, Product review | P1 if commercial |
| Analytics (GA4) | All pages | All | P0 |
| Search Console API | Performance data | All | P0 |

#### Tracking Events
Define what to track per page type:
- Page view (all pages)
- CTA click (email, phone, booking, affiliate)
- Map interaction (local pages)
- Filter usage (local hub, comparison)
- Internal link clicks (all pages)
- Schema event tracking (FAQ toggles, HowTo steps)

### Phase 4: Design Constraints

Define the design direction for the UI team:

#### Content-First vs Conversion-First
- **Content-first**: hero is minimal, body content is prominent, CTAs are contextual. Use for informational pillar/cluster pages.
- **Conversion-first**: hero has strong CTA, content supports the conversion goal. Use for local city pages and commercial pages.

#### Mobile-First vs Desktop-First
- **Mobile-first**: local pages (maps, phone, directions are mobile-primary actions)
- **Desktop-first**: comparison tables, long-form guides, media-rich content

#### Visual Hierarchy Rules
- Which page type gets full-width hero vs narrow content?
- Which modules should be above the fold vs below?
- How prominent should CTAs be per page type?
- Image-to-text ratio per page type

### Phase 5: Product Priorities

Convert the analysis's priority (H/M/L) into product development phases:

| Phase | Focus | What ships | Pages |
|-------|-------|------------|-------|
| **P0 (Foundation)** | Core systems + highest-ROI content | Template system, CMS, analytics, tracking; pillar + top clusters | ~10 pages |
| **P1 (Expansion)** | Scale content + local system | Local page template, map API, listing cards; all cluster + city pages | ~20 pages |
| **P2 (Commercial)** | Monetization features | Affiliate link system, lead forms, review aggregation; commercial pages | ~10 pages |
| **P3 (Enhancement)** | Polish + automation | Review system, related content engine, schema automation; journal content | ongoing |

---

## Output format

Output a single Markdown PRD file named `data/PRD-{topic}.md` within the keyword folder. Save to `data/PRD-{topic}.md`.

```markdown
# Product PRD: {Topic}

## Source Analysis
- Reference to the seo-site-analyzer document used
- Summary of key findings (site type, total pages, commercial viability)

## 1. Page Templates
For each page type present in the analysis:
### {Page Type} Template
- Intent
- Hero spec (title pattern, CTA, image)
- H2/H3 skeleton (required vs optional)
- Modules (FAQ, table, map, reviews, etc.)
- Schema types
- Conversion path
- Design notes

## 2. Page Inventory (with Template Assignment)
For each page from the analysis:
- URL, page type template assigned, priority, notes

## 3. User Flows
- Flow A: Informational
- Flow B: Local/Transactional
- Flow C: Commercial/Comparison
- Decision points and conversion actions

## 4. Functional Specs
- CMS / template system
- APIs and services
- Tracking events

## 5. Design Constraints
- Content-first vs conversion-first rules
- Mobile-first vs desktop-first rules
- Visual hierarchy guidelines

## 6. Product Priorities
- P0 / P1 / P2 / P3 phases
- What ships in each phase

## 7. Open Questions
- What decisions are deferred
- What needs user testing
- What depends on third-party data
```

---

## Examples

**Input:** `china-massage-analysis.md` (from seo-site-analyzer, showing Hybrid site with 25+ pages across learn/techniques/compare/best/near-me)

**Expected output:** `PRD-china-massage.md` with:
- 5 page templates defined (Pillar, How-to, Comparison, Local hub, Local city)
- Each page in the 25+ inventory assigned a template
- 3 user flows (Info, Local, Comparison)
- CMS templating for local city pages (parameterized by city)
- Map API integration spec
- P0 → pillar + templates + local hub; P1 → all city pages; P2 → affiliate pages

**Input:** `chinese-herbal-tea-analysis.md` (showing Niche Content site with 1 pillar + 10 clusters)

**Expected output:** `PRD-chinese-herbal-tea.md` with:
- 4 page templates defined (Pillar/Guide, How-to, Comparison, Listicle)
- Each of 10+ pages assigned a template
- 2 user flows (Info, Commercial)
- No local/map components needed
- P0 → pillar + key content; P1 → all clusters; P2 → commercial pages
