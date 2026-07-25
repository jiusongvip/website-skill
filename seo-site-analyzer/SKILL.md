---
name: seo-site-analyzer
description: >
  SEO Site Analyzer — takes a keyword + SEMrush CSV export and produces a 
  strategic analysis document: site type, filter decisions, decision matrix, 
  site architecture, URL system, content strategy, internal links, and 
  commercial logic. This is the ANALYSIS layer ONLY — it answers "what kind 
  of site should this be, what pages are needed, and why." It does NOT 
  produce product-level PRDs (page IA, user flows, functional specs). Use 
  this whenever someone provides a keyword research CSV and wants to 
  understand the SEO opportunity and site structure before building. The 
  output feeds directly into seo-prd-builder for product-level PRD generation.
---
# SEO Site Analyzer

## Why this skill exists

This is the **analysis layer** of a two-skill system:
- **seo-site-analyzer** (this): keyword data → strategic analysis
- **seo-prd-builder** (separate): strategic analysis → product-level PRD

This skill does NOT generate PRDs. It generates **analysis documents** that answer:
- Is this keyword set worth building a site for?
- What kind of site does the data suggest?
- What pages should exist, and why?
- What should NOT be built?
- What's the priority order?

---

## Input format

The user provides:
- **A keyword** (e.g., "china massage")
- **One or more SEMrush CSV exports**
- **Optional context**: site type, target market

### Parsing SEMrush CSVs

CSV columns vary. Detection logic:
- If a cell looks like `"2,400"` or `2400` → Volume
- If a cell is `0-100` integer → KD
- If a cell is `I/C/T/N` → Intent
- Parse the header row for clues (`sm-cell-intent__element`, `sm-cell-kd__data`, etc.)
- When ambiguous, infer by position

---

## Pipeline

### Phase 0: Parse & Clean

Build a keyword table: keyword, intent, volume, kd, cpc, trend, results.

Apply filters **in order**:

**Filter 1 — Explicit content**
Keywords containing sex, porn, adult, erotic, xxx, nude, escort, or other NSFW terms → Exclude, note in document.

**Filter 2 — Near-duplicate merge**
Group keywords differing only by: word order, pluralization, function words, minor spelling. Pick highest-volume as canonical.

**Filter 3 — Local vs General**
Keywords with near me, nearby, city names, open now → split into Local bucket and General bucket.

**Filter 4 — Intent re-classification**
Correct wrong intent labels from CSV. what-is/how-to/benefits → I. near me/buy → T. vs/best → C.

### Phase 1: Domain Analysis

**Intent distribution** → Site type:
- >40% Transactional + near me → Local Service
- >60% Informational → Content/Authority
- >40% Commercial + high CPC → Affiliate/Commercial
- Mixed → Hybrid

**Volume distribution** → Market breadth:
- Top 3 >10,000/mo → Broad, competitive
- Top <2,000/mo → Niche, easier
- Many <500/mo → Cluster strategy

**Local signal** → Strong if >15% volume from local terms.

### Phase 2: Decision Matrix

| KD Range | Volume Range | Decision |
|----------|-------------|----------|
| 0–20 | any | BUILD |
| 0–20 | <100 | BUILD as cluster |
| 20–40 | >500 | PRIORITY |
| 20–40 | <500 | BUILD if related to pillar |
| 40–60 | >2000 | CONSIDER |
| 40–60 | <2000 | SKIP or defer |
| 60+ | any | SKIP for new site |
| any | <50 | EXCLUDE |

New site: +15 effective KD. Existing site: use raw KD.

### Phase 3: Architecture Generation

Based on Domain Analysis, build structure:
- Pillar selection (2–4 themes)
- Cluster organization (question type / entity)
- Depth: 1-level / 2-level / 3-level

### Phase 4: URL System

| Content type | URL pattern |
|-------------|-------------|
| What-is | `/what-is-{keyword}` |
| How-to | `/how-to-{keyword}` |
| Benefits | `/{keyword}-benefits` |
| Comparison | `/{keyword}-vs-{competitor}` |
| Best-of | `/best-{keyword}` |
| Local | `/near-me/{city}` |

Mark canonical + aliases for merged groups.

### Phase 5: Content Strategy

Plan content types: How-to, What-is, Comparison, Problem-solving, Listicle.
Prioritize first 10 articles by: low KD × decent volume × diversity.
Growth path: 0-10 → 10-30 → 30-60 → 60+.

### Phase 6: Internal Link System

Pillar → Cluster → Article link flow. Orphan prevention check.

### Phase 7: Commercial Logic

Assess commercial viability, separation plan, risk analysis.

---

## Output format

Output a single analysis document named `data/{keyword-or-topic}-analysis.md` within the keyword folder. Save to `data/{keyword-or-topic}-analysis.md`.

```markdown
# SEO Site Analysis: {keyword}

## 1. Data Overview
- Total keywords, after-filter counts, intent/volume distribution, key stats

## 2. Domain Analysis
- Site type, primary user need, content viability, local viability

## 3. Filter Decisions
- Excluded terms, near-duplicate merges, local/general split

## 4. Decision Matrix
- Table: cluster | KD | Volume | Decision | Priority

## 5. Site Architecture
- Structure tree, pillar definitions, depth rationale

## 6. URL System
- URL patterns, canonical assignments, aliases

## 7. Keyword → Page Mapping
- keyword → URL → page type → priority

## 8. Content Strategy
- First 10 articles, content types, growth milestones

## 9. Internal Link System
- Link flow diagram, orphan prevention

## 10. Commercial Strategy
- Monetization assessment, separation plan, risk analysis

## 11. Growth Model
- Phase plan, traffic progression
```

This document is the **input contract** for seo-prd-builder. The builder reads it to generate page-level IA, user flows, functional specs, and design constraints.

---

## Examples

**Input:**
```
KEYWORD: china massage
SITE TYPE: content site
FILES: 新词_China massage.csv
```

**Expected output:** china-massage-analysis.md with 11 sections showing hybrid site type, local+general split, decision matrix.

**Input:**
```
KEYWORD: chinese herbal tea
SITE TYPE: content site
FILES: 新词_chinese herbal tea.csv
```

**Expected output:** chinese-herbal-tea-analysis.md with 11 sections showing niche authority type, low-KD opportunity, pillar/cluster structure.
