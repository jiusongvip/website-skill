---
name: content-writer
description: >
  Produces high-quality, E-E-A-T compliant page content and blog posts for informational/commercial websites.
  Use this skill when you need to: fill a page template with real substantive content (not placeholder/lorem ipsum),
  write a blog post or article from a topic/keyword brief, generate content from a PRD or SEO analysis,
  or replace thin/placeholder content with editorial writing that satisfies search intent.
  Also use when the user asks to "write content", "fill the pages", "write a blog post", "create article content",
  "make the site not feel empty", or says "写文章", "改文章", "生产内容", "填充内容", "写博客", "写正文".
  Do NOT use for code generation, SEO analysis, metadata writing, or image creation.
---

# Content Writer Skill — facialcupping.com

## Project Context

This skill is for **facialcupping.com** — an Astro-based content site about facial cupping (a skincare technique using suction cups on the face). The site runs on Astro v7 with content collections (MD files). All content is published via Cloudflare Pages.

**Content structure:**
- Articles live at `src/content/articles/{section}/{slug}.md`
- Section hub pages at `src/content/sections/{section}.md` (title, description, order, status)
- Routes: `/{section}/{slug}/` for articles, `/{section}/` for section hubs

**Domain:** https://www.facial-cupping.com

---

## Article Frontmatter Schema (Required Fields)

Every article must have these frontmatter fields. The Astro build will fail if required fields are missing or invalid.

```yaml
---
title: "string"              # Required. Descriptive, keyword-rich. 50-65 chars ideal.
description: "string"        # Required. 120-160 chars. Should include primary keyword and CTA angle.
section: "string"            # Required. Must match a section slug (see sections below).
status: "published"          # "published" | "draft" | "dev". Default: "published".
author: "string"             # Recommended. Use named author (see Authors below).
datePublished: "2026-01-01"  # Recommended. YYYY-MM-DD format.
dateUpdated: "2026-07-11"    # Optional. YYYY-MM-DD. Update when content is revised.
---
```

### Status Behaviors
| Status | Build | Sitemap | Footer/Nav |
|--------|-------|---------|------------|
| `published` | Generated | Included | Visible |
| `draft` | Generated (dev only) | Excluded | Hidden |
| `dev` | Generated (dev only) | Excluded | Hidden |

The visibility logic is in `src/lib/visibility.ts` — articles with status `"draft"` are completely hidden from production builds (not in sitemap, not in footer nav, not in section hub listings).

---

## Sections

### Published Sections (active on live site)

| Section Slug | Title | Article Count | Focus Keywords |
|---|---|---|---|
| `learn` | Learn | 5 | facial cupping, what is facial cupping, how facial cupping works |
| `benefits` | Benefits | 10 | facial cupping benefits, facial cupping before and after, facial cupping results |
| `how-to` | How To | 6 | how to do facial cupping, facial cupping techniques, facial cupping step by step |
| `safety` | Safety | 7 | facial cupping safety, facial cupping side effects, facial cupping safe |
| `tools` | Tools | 4 | best facial cupping sets, facial cupping tools, silicone vs glass facial cups |
| `research` | Research | 3 | facial cupping research, facial cupping scientific studies, facial cupping evidence |
| `about` | About | 4 | about, editorial guidelines, contact, review process |

### Draft Sections (not yet live)

| Section Slug | Title | Article Count | Focus Keywords |
|---|---|---|---|
| `oils` | Oils | 2 | facial cupping oil, best oil for facial cupping |
| `comparisons` | Comparisons | 3 | facial cupping vs gua sha, vs jade roller, vs microcurrent |
| `brands` | Brands | 4 | best facial cupping brands, bellabaci, primally pure, rena christina |
| `glowcup` | GlowCup | 5 | glowcup facial cupping, glowcup reviews |

---

## Authors

Two named authors available. Use them to strengthen E-E-A-T. Never use `"FacialCupping.com Team"` on research articles.

| Author | Credentials | Appropriate For |
|--------|-------------|----------------|
| `Sarah Chen, Licensed Esthetician` | Licensed esthetician with skincare expertise | Benefits, Safety, Tools, How-To, Learn articles |
| `James Liu, Licensed Acupuncturist & TCM Practitioner` | TCM practitioner with cupping expertise | Research, Learn (history), Oils, Comparisons articles |

---

## File Naming & URLs

- **Section files:** `src/content/sections/{section}.md` — slug matches filename stem
- **Article files:** `src/content/articles/{section}/{kebab-case-slug}.md`
- **About pages:** `src/content/articles/about/{slug}.md` (e.g., `mission.md`, `contact.md`)
- **URL output:** `/{section}/{slug}/` with trailing slash (configured via `trailingSlash: 'always'`)
- **Article ID:** `{section}/{slug}` — derived from path relative to `articles/`

Example:
```
File: src/content/articles/benefits/lymphatic-drainage.md
ID:   benefits/lymphatic-drainage
URL:  https://www.facial-cupping.com/benefits/lymphatic-drainage/
```

---

## Content Standards

### Write for a real person

This site's readers fall into two types. Write for them specifically:

1. **Evaluators (62%)** — "What is facial cupping?", "Does it really work?", "Is it safe?", "Facial cupping vs gua sha?"
   - Give them clear comparisons, decision criteria, and verdict boxes
   - Address safety concerns and evidence gaps transparently
   - Include before/after expectations where relevant

2. **Learners (28%)** — "How do I do facial cupping?", "What techniques work best?"
   - Structure from foundation to advanced
   - Use correct anatomical terminology but explain each term
   - Include step-by-step guidance where applicable

### Demonstrate E-E-A-T in every paragraph

**Experience:** Include specific, concrete details. Instead of "facial cupping has many benefits for the skin", write "After 4-6 weeks of consistent facial cupping (3-5 sessions per week), most users report a visible reduction in morning puffiness and a more defined jawline."

**Expertise:** Use correct terminology (lymphatic drainage, silicone vs glass cups, suction pressure, petechiae, gua sha, microcurrent) but explain each term the first time it appears. Cite licensed esthetician or TCM practitioner perspective when relevant.

**Authoritativeness:** Cite authoritative sources where applicable (PubMed studies on cupping therapy, dermatology journals, licensed esthetician guidelines). For research articles, link to actual DOI/PubMed entries.

**Trustworthiness:** Distinguish fact from anecdote. Include health/medical disclaimers where appropriate ("This content is for informational purposes only and is not medical advice. Consult a licensed healthcare provider before starting any new skincare routine."). Never promise specific outcomes. Be transparent about what is not known — the research on facial cupping is limited compared to body cupping.

### Writing mechanics

- Clear, direct sentences (15-20 words average)
- Paragraphs 2-4 sentences
- Active voice. Address the reader ("you")
- Scannable with descriptive headings framed as questions where possible
- Bullet/numbered lists for comparison, steps, features, contraindications
- No generic phrasing, no repetitive structure across pages

### Readability (from seo-content)

| Metric | Target |
|--------|--------|
| Flesch Reading Ease | 60-70 (plain English) |
| Sentence length | 15-20 words average |
| Paragraph length | 2-4 sentences |

### SEO

- Primary keyword in H1, first 100 words, and at least one H2
- Semantic variations naturally throughout
- 1-3% keyword density (natural, not forced)
- No keyword stuffing

### Internal linking

- 3-5 internal links per 1000 words
- Descriptive anchor text (not "click here")
- Link to related pages within the site (e.g., a benefits article should link to how-to for technique, or safety for precautions)
- Ensure every page has at least one incoming and one outgoing link

### Word count minimums

| Type | Minimum |
|------|---------|
| Pillar page / flagship article | 1,500 |
| Guide | 800 |
| Comparison | 1,200 |
| How-to | 800 |
| Section hub page | 300-500 |
| Homepage | 500 |

These are topical coverage floors, not targets.

### Freshness (from seo-content)

- Content >12 months without update → flagged as stale
- For blog posts: include `updated` date in frontmatter if revised
- For GEO/AI visibility: content <3 months old is 3x more likely to be cited by AI

### GEO / AI Search Standards (from seo-geo)

AI crawlers (Google AI Overviews, ChatGPT, Perplexity) cite content differently than traditional search. Apply these rules:

| Rule | Standard |
|------|----------|
| **Answer block length** | 134-167 words per self-contained answer |
| **Direct answer position** | Core answer must appear within first 40-60 words of body |
| **Question-based H2s** | "What is X?", "How does X work?", "Is X safe?" |
| **Definition density** | Include explicit "X is..." or "X refers to..." early |
| **Specific stats** | Use real numbers, not approximations |
| **Multi-modal** | Astro `<Picture>` or `<Image>` component for embedded images |
| **Tables & lists** | Markdown tables for comparison data |
| **Structure** | H1 → H2 → H3 hierarchy, never skip levels |

### Blog-specific rules

For future `/blog/` articles:
- More timely introduction (can reference trends, common questions)
- Include a "Related Articles" section at the bottom
- Link back to the relevant pillar page
- Conversational but still authoritative
- Still must pass all E-E-A-T checks

---

## Quality Gate: Call seo-content before delivery

After writing the content, you must run it through `C:\Users\nec10\.agents\skills\seo-content\SKILL.md` as a post-write audit:

1. **Load the seo-content skill** — Read `C:\Users\nec10\.agents\skills\seo-content\SKILL.md` in full
2. **Audit your own output** — Apply seo-content's E-E-A-T framework, Content Quality Score, and AI Citation Readiness assessment to the content you just wrote
3. **Append the audit result** below your content in this format:

```markdown
---
## Content Quality Score: XX/100

### E-E-A-T Breakdown
| Factor | Score | Evidence |
|--------|-------|----------|
| Experience | XX/25 | First-hand details, specificity |
| Expertise | XX/25 | Terminology accuracy, depth |
| Authoritativeness | XX/25 | External citations, sources |
| Trustworthiness | XX/25 | Disclaimer, transparency |

### AI Citation Readiness: XX/100

### SEO Checklist
- [ ] Primary keyword in H1 + first 100 words
- [ ] 3-5 internal links per 1000 words
- [ ] Semantic variations present
- [ ] Word count meets page type minimum
```

4. If any E-E-A-T factor scores below 15/25 or AI Citation Readiness below 60/100, revise the content and re-audit until all pass. Do not deliver content that fails the audit.

---

## What NOT to do

- Do NOT generate code, HTML, JSX, or Astro components
- Do NOT generate images, image prompts, or media
- Do NOT make up statistics, citations, or facts
- Do NOT write meta descriptions, title tags, or structured data (separate concerns)
- Do NOT recommend specific medical treatments or dosages
- Do NOT leave placeholder text or incomplete sections
- Do NOT use the generic "FacialCupping.com Team" author for research articles
- Do NOT set `status: "draft"` unless explicitly instructed to keep content unpublished
