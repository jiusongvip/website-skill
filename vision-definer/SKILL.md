---
name: vision-definer
description: >
  Vision Definer — the starting point of the content-site pipeline.
  Before touching keywords or writing code, this skill defines the site's
  foundation: who it serves, what problem it solves, why it's worth using,
  content boundaries, and site columns.
  Use this BEFORE seo-site-analyzer when starting a new content site.
  The output (vision.md) feeds directly into seo-site-analyzer and
  seo-pipeline-orchestrator as the strategic north star.
  Trigger this whenever a user says "I want to build a site about X",
  "help me plan a website for Y", or provides a broad topic without
  a clear content strategy.
---

# Vision Definer

## Why this skill exists

Most content sites fail not because of bad SEO or bad code, but because
nobody defined the core question first:

> **Who is this for, what problem does it solve, and why would someone use it?**

This skill forces that clarity before any keyword research or development.
It's Phase 0 of the seo-pipeline-orchestrator flow.

---

## Input

### Required

- **Topic / keyword** — what the site is about (e.g. "Tesla owner guide")

### Optional (if user provides)

- Target audience description
- Existing content or competitors they admire
- Monetization goal (affiliate, ads, lead gen, ecommerce)
- Design preference / vibe

---

## Pipeline

### Step 1: Ask (or Infer)

If the user already told you the answers, skip to Step 2.
If not, ask **at most 3 questions** to fill the gaps:

1. *"这个网站帮谁做的？谁会来搜、来看？"*
   → e.g. "Tesla 新车车主，刚提车不知道怎么选充电桩、保养、配件"

2. *"你觉得用户最想在这上面解决什么问题？"*
   → e.g. "选充电桩/保养对比/配件推荐，但不想看软文"

3. *"和其他同类网站比，你的优势是什么？"*
   → e.g. "独立客观，不是广告站，真实车主视角"

### Step 2: Define Site Foundation

Based on answers, produce one clear paragraph for each:

#### Target User
Who exactly will visit this site? Demographics, pain points, search behavior.
Be specific: not "Tesla owners" but "new Tesla Model Y owners in US, first EV,
confused about charging options, skeptical of paid reviews."

#### Core Value Proposition
One sentence: what does this site give the user that nothing else does?

#### Why Worth Using
Concrete differentiation: "No affiliate bias", "Real owner data", "Updated weekly"

#### Content Boundaries
Explicitly list what's IN scope and what's OUT of scope.
- In: charging comparison, maintenance schedule, accessories reviews
- Out: car sales, financing, insurance (unless core)

### Step 3: Define Content Columns

List 4-8 content sections that map to user needs:

| Column | User Need | Example Articles |
|--------|-----------|-----------------|
| Charging | "Which charger should I buy?" | Home charger guide, charging speed comparison |
| Maintenance | "How do I take care of this?" | Tire rotation schedule, brake maintenance |
| Accessories | "What should I buy for my car?" | Floor mats, screen protector, roof rack |

### Step 4: First 5 Pages

List the first 5 pages to build, in priority order.
These become the P0 pages in the PRD.

---

## Output: `data/vision.md`

Save to `data/vision.md` within the keyword folder.

Single markdown file:

```markdown
# Site Vision: {keyword}

## Target User
[detailed description]

## Core Value Proposition
[one sentence]

## Why Worth Using
[differentiation]

## Content Boundaries
**In scope:** ...
**Out of scope:** ...

## Content Columns
1. {Column 1} — {need}
2. {Column 2} — {need}
...

## First 5 Pages
1. {page title} — {why first}
2. {page title}
...

## Design Direction
[inferred or provided: e.g. "editorial calm, warm neutrals"]
```

---

## What NOT to do

- Do NOT skip this step even if the user says "just build it"
- Do NOT do keyword research here — that's seo-site-analyzer's job
- Do NOT write code, design specs, or PRDs
- Do NOT output more than one page — keep vision.md concise
- Do NOT invent target users — if the user is unsure, state what you inferred
