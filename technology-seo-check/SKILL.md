---
name: site-seo-check
description: >-
  通用线上技术SEO审计技能，适配所有网站。curl线上页面审计基础信号(title长度/desc长度/H1唯一/H2≥2/H3不跳级/alt/OG社交标签/robots.txt/sitemap)、性能检查(CWV/PageSpeed Insights)、文本重复、分页title、canonical尾斜杠、www重定向、内页抽样、内部链接尾斜杠。用户提供域名。触发词：SEO检查、网站SEO、seo check、技术SEO。
version: 1.5.0
metadata:
  hermes:
    tags: [seo, tech-seo, keyword-density, daily-check]
    related_skills: [seo-content-iterative]
---

# 线上技术 SEO 审计

## 触发条件

用户说 "SEO检查"、"每日SEO"、"seo check"、"检查SEO"、"技术SEO审计" 时调用本 skill。

## 核心原则

**直接检查线上 https://{用户提供的域名}，不依赖本地 build。** 所有检查通过 curl 抓取线上页面 HTML 进行。

## 检查流程

### Step 0：声明变量

```bash
BASE="https://www.{用户提供的域名}"
```

> **域名与 URL 规范（重要）：**
> 1. 所有站点统一使用带 `www` 前缀的正式域名；裸域名 `https://{域名}` 必须 301 跳转到 `https://www.{域名}`。因此 BASE 一律使用 www 域名。
> 2. 所有 URL 末尾带 `/`（尾斜杠），Astro 配置 `trailingSlash: "always"`；**首页根域名例外**——首页 canonical 与 sitemap 首页均为 `https://www.{域名}`（不带尾斜杠），内页为 `https://www.{域名}/xxx/`（带尾斜杠）。

所有后续 curl 命令基于此 BASE URL。命令中的具体路径（如 /{list}、/{section}、/locale-path 等）需根据目标网站实际结构调整。

### Step 1：首页 SEO 基础信号

检查首页（`/`）的关键 SEO 信号是否达标。

**检查项：**

| 检查项 | 阈值 | 修复方式 |
|--------|------|----------|
| `<h1>` 唯一性 | 有且仅有 1 个 h1 | 多余 h1 降级为 h2/h3；缺失时补可见或 `sr-only` h1 |
| `<title>` 长度 | 40-60 字符 | 扩展 i18n `page.home.seoTitle` |
| `<meta description>` 长度 | 140-160 字符 | 扩展 i18n `page.home.seoDescription` |
| `<h2>` 数量 | ≥ 2 个 | 长文按内容主题分区补 h2 小标题 |
| `<h3>` 数量 | ≥ 1 个且不跳级 | h3 必须出现在 h2 之后；长文页 h3 可多于 h2 |
| OG / Social tags | og:title / og:description / og:image / twitter:card 必须存在 | 在全局 Head 组件统一注入 |
| `/sitemap.xml` 可访问 | 必须返回 200 或 301 | `public/sitemap.xml` → sitemap-index |
| `<img>` alt 属性 | 所有 img 必须有 alt | 逐一补齐 |

**检查命令：**

```bash
# H1 内容（使用 -z 参数使 . 匹配换行符，解决跨行 H1 匹配问题）
curl -sL "$BASE/" | grep -oPz '(?s)<h1[^>]*>.*?</h1>' | head -3
# 期望：展示至少 1 个 h1 文本

# H1 唯一性（统计开标签数量，期望恰好 1 个）
curl -sL "$BASE/" | grep -oP '<h1(?=[ >])' | wc -l
# 期望：1（若 > 1 需合并或降级多余 H1）

# Title 长度
curl -sL "$BASE/" | grep -oP '<title>\K[^<]+' | wc -c
# 期望：40-60

# Description 长度
curl -sL "$BASE/" | grep -oP '<meta name="description" content="\K[^"]+' | wc -c
# 期望：140-160

# sitemap.xml
curl -sLo /dev/null -w "%{http_code}" "$BASE/sitemap.xml"
echo ""
curl -sLo /dev/null -w "%{http_code}" "$BASE/sitemap-index.xml"
echo ""
# 期望：均 200

# 图片 alt 缺失
curl -sL "$BASE/" | grep -oP '<img\s[^>]*>' | grep -v 'alt=' | wc -l
# 期望：0

# H2 数量（内容分区标题，反映页面结构层级）
curl -sL "$BASE/" | grep -oP '<h2(?=[ >])' | wc -l
# 期望：≥ 2（若为 0 或 1，需补充内容分区小标题）

# H3 数量（H2 下的子分区）
curl -sL "$BASE/" | grep -oP '<h3(?=[ >])' | wc -l
# 期望：≥ 1 且不跳级（若 H3 > 0 则必须先有 H2；长文内容页 H3 可多于 H2，工具/落地页可为 0）

# OG / Social meta tags（社交分享富媒体展示，属性顺序无关）
curl -sL "$BASE/" | grep -oP '<meta[^>]*property="og:(title|description|image)"' | wc -l
# 期望：≥ 3（og:title / og:description / og:image，另建议 og:url / og:type / og:site_name）
curl -sL "$BASE/" | grep -oP '<meta[^>]*name="twitter:(card|title|description|image)"' | wc -l
# 期望：≥ 1（twitter:card 必须存在；twitter:title/description/image 建议齐备）
```

同样检查 {locale} 首页：

```bash
curl -sL "$BASE/{locale}/" | grep -oPz '(?s)<h1[^>]*>.*?</h1>' | head -3
curl -sL "$BASE/{locale}/" | grep -oP '<h1(?=[ >])' | wc -l
curl -sL "$BASE/{locale}/" | grep -oP '<title>\K[^<]+' | wc -c
curl -sL "$BASE/{locale}/" | grep -oP '<meta name="description" content="\K[^"]+' | wc -c
curl -sL "$BASE/{locale}/" | grep -oP '<h2(?=[ >])' | wc -l
curl -sL "$BASE/{locale}/" | grep -oP '<h3(?=[ >])' | wc -l
curl -sL "$BASE/{locale}/" | grep -oP '<meta[^>]*property="og:(title|description|image)"' | wc -l
curl -sL "$BASE/{locale}/" | grep -oP '<img\s[^>]*>' | grep -v 'alt=' | wc -l
```

### Step 2：文本重复检查

通过 curl 抓取线上页面，统计关键文本在 HTML 源码中的出现次数。

**已知需要检查的模式：**

| 关键词 | 预期次数 | 来源 | 修复方式 |
|--------|----------|------|----------|
| {lang-label} / 繁體中文 | 1 | LanguageSwitcher 触发器 | 已用 `data-label` + CSS `content: attr()` 解决下拉重复 |
| English | 1 | 同上（en locale 启用后） | 同上 |
| {toggle-text} / {toggle-text} | 每页 ≤ 总 review 数（正常） | HospitalDetailPage review toggle | 已用 CSS `content: attr()` 替代 HTML 文本节点 |
| 找醫院 / 找醫生 / 找服務 | 2（桌面nav + 汉堡菜单） | 正常，搜索引擎通过 `<nav>` 语义降权 |
| 咨询顾问 | 2（桌面 + 移动端菜单） | 同 nav 文本，可接受 |

**检查命令：**

```bash
# 首页语言标签
curl -sL "$BASE/" | grep -o '{lang-label}' | wc -l
curl -sL "$BASE/{locale}/" | grep -o '繁體中文' | wc -l
# 期望结果：各 1

# 回顾切换文本（取有 review 的医院页面抽样）
PAGE="{example-page}"
curl -sL "$BASE/{list-page}/$HOSPITAL/" | grep -o '{toggle-text}' | wc -l
curl -sL "$BASE/{list-page}/$HOSPITAL/" | grep -o '{toggle-text}' | wc -l
# 期望结果：0（已迁移到 CSS content）
```

### Step 3：分页 title 检查

检查所有列表页分页的 `<title>` 是否包含页码。

**检查页面类型：**

| 路由 | 第2页 title 格式 |
|------|-------------------|
| /{list}/2/ | `{titleBase} - 第2页 - {brand}` |
| `/{list}/{filter}/2/ | 同模式` |
| /{list}/2/ | 同模式 |
| /{list}/{filter}/2/ | 同模式 |
| /{section}/2/ | 同模式 |
| /{section}/{category}/2/ | `{categoryLabel} - Page 2 - {brand}` |

**检查命令：**

```bash
# 抽样检查分页 title
curl -sL "$BASE/{list-page}/{filter}/2/" | grep -oP '<title>\K[^<]+'
curl -sL "$BASE/{list-page}/2/" | grep -oP '<title>\K[^<]+'
curl -sL "$BASE/{section}/2/" | grep -oP '<title>\K[^<]+'
curl -sL "$BASE/{list-page}/{filter}/" | grep -oP '<title>\K[^<]+'

# 验证模式：
# 第2页 title 需含 "第2页"
# 第1页 title 不含 "第1页"
```

### Step 4：分类页 title/description 差异化

检查 `{section}/{category}/` 页面的 title/description 是否与 `/{section}/` 不同。

**检查命令：**

```bash
for CAT in {cat-1} {cat-2} {cat-3} {cat-4}; do
  echo "=== $CAT ==="
  curl -sL "$BASE/{section}/$CAT/" | grep -oP '<title>\K[^<]+'
  curl -sL "$BASE/{section}/$CAT/" | grep -oP '<meta name="description" content="\K[^"]+'
done

# 同时检查 {locale} 对应页面
for CAT in {cat-1} {cat-2} {cat-3} {cat-4}; do
  echo "=== {locale} $CAT ==="
  curl -sL "\$BASE/\{locale\}/\{section\}/\$CAT/" | grep -oP '<title>...'
done
```

**期望：** 每个分类的 title 和 description 各不相同。

### Step 5：CSS content 渲染模式检查

验证使用 `CSS content: attr(data-xxx)` 渲染的文本在实际页面中正常显示（不依赖 JS）。

**检查点位：**

| 文件 | 选择器 | 验证 |
|------|--------|------|
| `LanguageSwitcher.astro` | `.lang-current::after` | 下拉当前语言高亮文本 |
| `HospitalDetailPage.astro` | `.review-toggle::after` | {toggle-text}/{toggle-text} |

**验证方式：** 检查线上 HTML 源码中是否存在 `.lang-current` 和 `.review-toggle` 的 data 属性用法，确认文本不在 HTML 文本节点中。

### Step 6：汇总报告

按以下格式输出检查结果：

```
## 技术 SEO 检查报告 — {日期}

**线上域名：** https://{用户提供的域名}

**首页基础信号：**
- H1 唯一性：{} 个 (预期 1) ✅/❌
- Title 长度：{} chars (预期 40-60) ✅/❌
- Description 长度：{} chars (预期 140-160) ✅/❌
- H2 数量：{} 个 (预期 ≥ 2) ✅/❌
- H3 数量：{} 个 (预期 ≥ 1 且不跳级) ✅/❌
- OG/Social tags：og:{} / twitter:{} ✅/❌
- robots.txt：{} ✅/❌
- sitemap.xml：{} ✅/❌
- 图片 alt 缺失：{} 个 (预期 0) ✅/❌

**Sitemap 完整性：**
- 无尾斜杠 URL：{} 个 (预期 1，仅首页)
- 双 locale 前缀 URL：{} 个 (预期 0)
- 子文件可达性：{} / 6 个 200 ✅/❌

**Canonical / hreflang 一致性：**
- {primary-locale} 首页 + 关键页：逐页列出
- {locale} 首页 + 关键页：{} / 7 ✅/❌
- Canonical 无尾斜杠：{} 个页面无尾斜杠 (预期 0，首页根域名除外) ✅/❌

**重定向链路（统一跳转到 www）：**
- http://example.com → {} ({301|302}) ✅/❌
- http://www.example.com → {} ({301|302|502|连接失败}) ✅/❌
- https://example.com → {} ({301|302}) ✅/❌  （裸域必须 301 → https://www.example.com）
- https://www.example.com → {} ({200}) ✅/❌  （最终目标，应直接 200）

**内页抽样：**
- 抽样页面 1：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌
- 抽样页面 2：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌
- 抽样页面 3：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌

**内部链接尾斜杠：**
- 首页不带尾斜杠的内部链接数：{} (预期 0) ✅/❌

**文本重复：**
- {lang-label}：{} 次 (预期 1)
- 繁體中文：{} 次 (预期 1)
- {toggle-text}：{} 次 (预期 0，已用 CSS content)
- {toggle-text}：{} 次 (预期 0，已用 CSS content)

**分页 title：**
- /{list-page}/{filter}/2/：{} ✅/❌
- /{list}/2/：{} ✅/❌
- /{section}/2/：{} ✅/❌

**分类页差异化：**
- ivf-education：{} ✅/❌
- overseas-guide：{} ✅/❌
- trying-to-conceive：{} ✅/❌
- cost-guide：{} ✅/❌

**404 遗留确认：**
- 无尾斜杠 → 301/308 重定向：{} ✅/❌
- 双 {locale} 前缀 → 404：{} ✅/❌

**性能（移动端 PSI）：**
- Performance Score：{} / 100 ✅/❌ (≥ 90)
- LCP：{} s ✅/❌ (≤ 2.5)
- FCP：{} s (≤ 1.8)
- TBT：{} ms (≤ 200)
- CLS：{} ✅/❌ (≤ 0.10)
- TTFB：{} s (≤ 0.8)
- 字段数据 CrUX：{} (fast / average / slow)

**修复建议：** {如有问题列出}
```

## 修复策略参考

### 文本节点 → CSS content 迁移模式

适用于：文本在 HTML 源码中重复出现，但视觉上需要保留。

```astro
<!-- Before：文本在 HTML 中 -->
<span>{lang-label}</span>

<!-- After：文本在 data-attr 中，CSS content 渲染 -->
<span class="lang-current" data-label="{lang-label}"></span>
<style>
  .lang-current::after { content: attr(data-label); }
</style>
```

### details/summary 切换文本

```astro
<!-- Before -->
<span class="group-open:hidden">展开</span>
<span class="hidden group-open:inline">{toggle-text}</span>

<!-- After -->
<span class="review-toggle" data-expand="展开" data-collapse="{toggle-text}"></span>
<style>
  details:not([open]) .review-toggle::after { content: attr(data-expand); }
  details[open] .review-toggle::after { content: attr(data-collapse); }
</style>
```

### 分页 title 修复模式

```astro
// Before：不区分分页
const title = baseTitle;

// After：分页感知
const title = page.currentPage > 1
  ? `${baseTitle} - 第${page.currentPage}页 - ${brand}`
  : `${baseTitle} - ${brand}`;
```

## 注意事项

- 不要为了降低关键词次数而删除必要的导航文本，搜索引擎通过 `<nav>` 等语义标签会自动降权
- `CSS content` 文本对 screen reader 的兼容性不一致，重要的无障碍文本应保留在 HTML 中
- data-* 属性值可能被某些 SEO 工具计入（如 aitdk），如果发现仍然被计数，改用 JS 动态 `createElement` 方案

### URL 与域名统一规范（2026-08 起）

1. **所有 URL 末尾带 `/`**：Astro 配置 `trailingSlash: "always"` + 默认 `build.format: "directory"`。内部链接 `<a href>`、canonical、sitemap 内页均带尾斜杠。
2. **首页根域名例外**：首页 canonical 与 sitemap 首页均为 `https://www.{域名}`（不带尾斜杠），内页为 `https://www.{域名}/xxx/`。canonical 实现：`Astro.url.pathname === "/"` 时对 canonical 去掉尾斜杠；sitemap 首页需构建后处理（见第 9 条）。
3. **所有域名统一带 www**：`site` 设为 `https://www.{域名}`，代码内所有 URL（schema/JSON-LD/robots/llms.txt 等）统一为 www。邮箱 `hello@{域名}` 不加 www。
4. **裸域名 301 跳 www**：Cloudflare 用「从根重定向到 WWW」模板（请求 URL `https://{域名}/*`，目标 `https://www.{域名}/${1}`，状态码 301，开启保留查询字符串）。必须确认裸域名 DNS 记录为橙色云朵（已代理）状态。
5. **不要用 `build.format: "file"`**：会生成 `.html` 物理文件（虽 Cloudflare clean URL 会隐藏 .html，但不符规范），应保持默认 `directory`。
6. **不要混用 `directory` + `never`**：Cloudflare Pages 对「无尾斜杠目录」请求默认 308 加斜杠，导致 `<a href="/xxx">` 点击后 URL 变成 `/xxx/`，a href 与实际 URL 不一致。
7. **不要在 `_redirects` 加尾斜杠 301 规则**：与 Cloudflare Pages 目录 308 行为冲突，形成 301↔308 死循环。`trailingSlash` 已由 Astro 内置处理。
8. **内部链接改尾斜杠要扫三种形式**：`<a href="/xxx">`（双引号）、`<a href='/xxx'>`（单引号）、`{ href: "/xxx" }`（JS 对象/数据数组），以及组件里动态拼接的 `/xxx/${slug}`。
9. **sitemap 首页去尾斜杠需构建后处理**：@astrojs/sitemap 的 `serialize` 钩子无法去掉根路径尾斜杠（底层 `new URL(url).toString()` 会强制加回 `/`）。需新增 `scripts/fix-sitemap-home.mjs`，在 build 脚本末尾追加 `&& node scripts/fix-sitemap-home.mjs`，把 `<loc>https://www.xxx.com/</loc>` 替换为 `<loc>https://www.xxx.com</loc>`。
### 新增检查项：线上特有信号

```bash
# robots.txt（可访问性：应返回 200）
curl -sLo /dev/null -w "%{http_code}" "$BASE/robots.txt"
echo ""
# 期望：200

# robots.txt 内容：放行规则 + sitemap 引用
curl -sL "$BASE/robots.txt" | head -20
# 期望：User-agent: * 与 Allow: /（不误拦全站）；无 Disallow: /
curl -sL "$BASE/robots.txt" | grep -oP 'Sitemap:\s*\K\S+'
# 期望：输出 sitemap URL（www 域名），与线上实际 sitemap 一致

# sitemap
curl -sL "$BASE/sitemap-index.xml" | head -20

# 响应状态码（首页、医院页、文章页）
curl -sLo /dev/null -w "%{http_code}" "$BASE/"
curl -sLo /dev/null -w "%{http_code}" "$BASE/{list-page}/{example-hospital-page}/"
curl -sLo /dev/null -w "%{http_code}" "$BASE/{section}/"
```

### Step 7：Sitemap 完整性检查

验证 sitemap 中的 URL 尾斜杠规范（内页均带尾斜杠、仅首页根域名不带尾斜杠）、无双 locale 前缀。双 locale 前缀是已知曾导致 GSC 报错的问题。

**问题背景：**

| GSC 问题类型 | 根因 | 修复 | GSC 消退 |
|-------------|------|------|----------|
| "备用网页（有适当的规范标记）" | canonical 无 `/` 但 hreflang 自引用有 `/`（或反之），Google 拆成两个 URL | `trailingSlash: 'always'`（内页带 `/`，首页根域名除外） | 部署后重新抓取 |
| "已发现 — 尚未编入索引" | 分页链接如 `/{list}/10` 无 `/`，与 canonical 不一致 | `trailingSlash: 'always'` | 部署后重新抓取 |
| "未找到 (404)" | `/{example-double-prefix-url}` 等双 locale 前缀 — 历史构建 bug，当前构建不产出 | 确认当前不产出，历史 404 自然消退 | 部署后 GSC 验证修复 |
| "未找到 (404)" | `/{list}/xxx` 无尾斜杠导致 404 | `trailingSlash: 'always'` | 部署后重新抓取 |
| "网页会自动重定向" | `http://` / `example.com` 跳转到 `https://www.{用户提供的域名}` — 正常裸域跳 www 行为 | 确认是 301 非 302 | 无需修复 |

**检查命令：**

```bash
# === 尾部斜杠检查 ===
# 抽取 sitemap 前 50 个 URL，统计不以 "/" 结尾的数量（内页全带尾斜杠，仅首页根域名不带）
curl -sL "$BASE/{sitemap-name}.xml" | grep -oP '<loc>\K[^<]+' | head -50 | grep -v '/$' | wc -l
# 期望：1（仅首页 https://www.{域名} 不带尾斜杠）

# === 双 locale 前缀检查 ===
# 全量扫描 sitemap，检查是否有 {locale}/{locale}/ 或 /en/en/ 模式
curl -sL "$BASE/{sitemap-name}.xml" | grep -oP '<loc>\K[^<]+' | grep -E '/({locale}|en)/({locale}|en)/' | wc -l
curl -sL "$BASE/{sitemap-name}.xml" | grep -oP '<loc>\K[^<]+' | grep -E '/({locale}|en)/({locale}|en)/' | wc -l
curl -sL "$BASE/{sitemap-name}.xml" | grep -oP '<loc>\K[^<]+' | grep -E '/({locale}|en)/({locale}|en)/' | wc -l
# 期望：全部 0

# === Sitemap 子文件可访问性 ===
for SITEMAP in {sitemap-name} {sitemap-name} {sitemap-name} {sitemap-name} {sitemap-name} {sitemap-name}; do
  STATUS=$(curl -sLo /dev/null -w "%{http_code}" "$BASE/${SITEMAP}.xml")
  echo "${SITEMAP}.xml → $STATUS"
done
# 期望：全部 200
```

### Step 8：Canonical 与 hreflang 自引用一致性

Google 会对 canonical 和 hreflang 自引用不一致的页面视为"备用网页"。必须确保同一页面的 `<link rel="canonical">` 和 `<link rel="alternate" hreflang="...">` 指向完全相同的 URL。

**Canonical 尾斜杠一致性检查（新增）：**

canonical URL 必须与页面实际访问 URL 完全一致（包括尾斜杠）。对于 `trailingSlash: 'always'` 的 Astro 项目：内页 canonical 带尾斜杠（`https://www.{域名}/xxx/`），首页根域名 canonical 不带尾斜杠（`https://www.{域名}`）。常见问题：`new URL('/', site).href` 对根路径返回带 `/` 的 URL，需对首页单独去掉尾斜杠。

**检查命令：**

```bash
# 抽样检查首页和关键子页面
for PAGE in "" {及网站关键页面路径}; do
  echo "=== $BASE$PAGE ==="
  CANONICAL=$(curl -sL "$BASE$PAGE" | grep -oP '<link rel="canonical" href="\K[^"]+')
  HREFLANG_SELF=$(curl -sL "$BASE$PAGE" | grep -oP '<link rel="alternate" hreflang="{primary-locale}" href="\K[^"]+')
  echo "  canonical: $CANONICAL"
  echo "  hreflang {primary-locale}: $HREFLANG_SELF"
  
  # 检查 canonical 尾斜杠（always：内页应有尾斜杠，首页根域名应无尾斜杠）
  if [[ "$PAGE" == "" && "$CANONICAL" == */ ]]; then
    echo "  ❌ 首页 canonical 不应有尾斜杠"
  elif [[ "$PAGE" != "" && "$CANONICAL" != */ ]]; then
    echo "  ❌ 内页 canonical 应有尾斜杠"
  else
    echo "  ✅ canonical 尾斜杠正确"
  fi
  
  if [ "$CANONICAL" = "$HREFLANG_SELF" ]; then
    echo "  ✅ canonical 与 hreflang 一致"
  else
    echo "  ❌ canonical 与 hreflang 不一致！"
  fi
done

# {locale} 版本
for PAGE in "" {及网站关键页面路径}; do
  echo "=== $BASE/{locale}$PAGE ==="
  CANONICAL=$(curl -sL "$BASE/{locale}$PAGE" | grep -oP '<link rel="canonical" href="\K[^"]+')
  HREFLANG_SELF=$(curl -sL "$BASE/{locale}$PAGE" | grep -oP '<link rel="alternate" hreflang="{locale}" href="\K[^"]+')
  echo "  canonical: $CANONICAL"
  echo "  hreflang {locale}: $HREFLANG_SELF"
  
  # 检查 canonical 尾斜杠（always：内页应有尾斜杠，首页根域名应无尾斜杠）
  if [[ "$PAGE" == "" && "$CANONICAL" == */ ]]; then
    echo "  ❌ 首页 canonical 不应有尾斜杠"
  elif [[ "$PAGE" != "" && "$CANONICAL" != */ ]]; then
    echo "  ❌ 内页 canonical 应有尾斜杠"
  else
    echo "  ✅ canonical 尾斜杠正确"
  fi
  
  if [ "$CANONICAL" = "$HREFLANG_SELF" ]; then
    echo "  ✅ canonical 与 hreflang 一致"
  else
    echo "  ❌ canonical 与 hreflang 不一致！"
  fi
done
```

### Step 9：重定向链路检查

验证 HTTP → HTTPS 与「裸域 → www」的 301 重定向正确，且为重定向直链（非多次跳转）。**规范：所有站点以 `https://www.{域名}` 为最终正式域名，裸域一律 301 跳转到 www。**

**已知正常模式：**
- `http://example.com` → 301 → `https://www.{用户提供的域名}`（理想：一跳直达，非两跳 `http://example.com` → `https://example.com` → `https://www.{用户提供的域名}`）
- `http://www.example.com` → 301 → `https://www.{用户提供的域名}`
- `https://example.com` → 301 → `https://www.{用户提供的域名}`（裸域必须 301 跳 www）
- `https://www.example.com` → 200（最终目标，直接返回内容，不再跳转）

**裸域跳 www 检查：**

`https://example.com` 必须 301 跳转到 `https://www.example.com`。若裸域直接返回 200 或未跳转到 www，说明未配置裸域 301。需在 Cloudflare 为裸域名配置 301 重定向到 www（并确保 www 子域已添加 A/AAAA 或 CNAME 记录）。

"网页会自动重定向"出现在 GSC 是正常现象，不需修复。但必须确认是 301（非 302），否则不传递 SEO 权重。

**检查命令：**

```bash
# 检查重定向目标
echo "=== http://example.com ==="
curl -sI -L -o /dev/null -w "HTTP %{http_code} → %{url_effective}\n" http://example.com/

echo "=== http://www.example.com ==="
curl -sI -L -o /dev/null -w "HTTP %{http_code} → %{url_effective}\n" http://www.example.com/

echo "=== https://www.example.com ==="
curl -sI -L -o /dev/null -w "HTTP %{http_code} → %{url_effective}\n" https://www.example.com/

echo "=== https://example.com ==="
curl -sI -L -o /dev/null -w "HTTP %{http_code} → %{url_effective}\n" https://example.com/

# 确认是 301 非 302
echo "=== http://example.com → 详细响应头 ==="
curl -sI http://example.com/ | head -5

echo "=== https://www.example.com → 详细响应头 ==="
curl -sI https://www.example.com/ | head -5

# 期望：
# - 所有重定向为 301（非 302）
# - 最终目标均为 https://www.{用户提供的域名}/
# - 裸域 https://example.com 必须 301 → https://www.example.com（不能直接 200）
# - https://www.example.com 必须直接 200（不能 502 或连接失败）
# - http://example.com 建议一跳直达，不接受两跳重定向链
```

### Step 10：内页抽样检查（新增）

从 sitemap 中抽取 2-3 个内页，检查 title/description/H1/canonical 是否达标。首页检查无法覆盖所有页面问题（如 About 页 title 过短）。

**检查命令：**

```bash
# 从 sitemap 抽取内页 URL
INNER_PAGES=$(curl -sL "$BASE/sitemap-index.xml" | grep -oP '<loc>\K[^<]+' | head -3)

for PAGE_URL in $INNER_PAGES; do
  echo "=== $PAGE_URL ==="
  HTML=$(curl -sL "$PAGE_URL")
  
  # Title
  TITLE=$(echo "$HTML" | grep -oP '<title>\K[^<]+')
  TITLE_LEN=${#TITLE}
  echo "  title: $TITLE (len=$TITLE_LEN)"
  if [ $TITLE_LEN -lt 40 ] || [ $TITLE_LEN -gt 65 ]; then
    echo "  ❌ title 长度不达标（40-65 字符）"
  else
    echo "  ✅ title 长度达标"
  fi
  
  # Description
  DESC=$(echo "$HTML" | grep -oP '<meta name="description" content="\K[^"]+')
  DESC_LEN=${#DESC}
  echo "  desc len: $DESC_LEN"
  if [ $DESC_LEN -lt 140 ] || [ $DESC_LEN -gt 160 ]; then
    echo "  ❌ description 长度不达标（140-160 字符）"
  else
    echo "  ✅ description 长度达标"
  fi
  
  # H1（唯一性：恰好 1 个）
  H1_COUNT=$(echo "$HTML" | grep -oP '<h1(?=[ >])' | wc -l)
  echo "  h1 count: $H1_COUNT"
  if [ $H1_COUNT -eq 0 ]; then
    echo "  ❌ 缺少 H1"
  elif [ $H1_COUNT -gt 1 ]; then
    echo "  ❌ 存在多个 H1（应仅 1 个，多余的降级为 H2/H3）"
  else
    echo "  ✅ H1 唯一"
  fi
  
  # Canonical 尾斜杠（always：内页应有尾斜杠）
  CANONICAL=$(echo "$HTML" | grep -oP '<link rel="canonical" href="\K[^"]+')
  if [[ "$CANONICAL" == */ ]]; then
    echo "  ✅ canonical 有尾斜杠：$CANONICAL"
  else
    echo "  ❌ canonical 无尾斜杠：$CANONICAL"
  fi
done
```

### Step 11：内部链接尾斜杠检查（新增）

检查页面内 `<a href>` 链接是否带尾斜杠。对于 `trailingSlash: 'always'` 的 Astro 项目，内部链接必须带尾斜杠（首页根路径 `/` 与锚点 `#` 除外）。

**检查命令：**

```bash
# 检查首页内部链接（always 模式：内部链接必须带尾斜杠，锚点 # 除外）
echo "=== 首页不带尾斜杠的内部链接 ==="
curl -sL "$BASE/" | grep -oP 'href="\K[^"]+' | grep -E '^/' | grep -v '/$' | grep -v '#' | head -10
# 期望：无输出（内部链接均带尾斜杠）

# 统计不带尾斜杠的内部链接数量
NO_SLASH_COUNT=$(curl -sL "$BASE/" | grep -oP 'href="\K[^"]+' | grep -E '^/' | grep -v '/$' | grep -v '#' | wc -l)
echo "不带尾斜杠的内部链接数：$NO_SLASH_COUNT"
# 期望：0
```

### Step 12：404 已知遗留 URL 确认

对 GSC 中报告过的已知 404 模式进行抽样确认。

**已知 404 模式：**

| 模式 | 示例 | 来源 |
|------|------|------|
| 双 locale 前缀 | `/{example-double-prefix-url}` | 历史构建 bug（sitemap 中无此 URL） |
| 无尾斜杠单页面 | `/{list}/{example-page}` | `trailingSlash: 'never'` 旧构建 |

```bash
# 部署 trailingSlash: 'always' 后，不带 / 的旧 URL 应返回 301/308 → 带 / 的新 URL
echo "=== 无尾斜杠 → 重定向验证 ==="
curl -sI "$BASE/about" | head -3
curl -sI "$BASE/contact" | head -3
curl -sI "$BASE/{list-page}/10" | head -3

# 双 locale 前缀仍应为 404（不会产出）
echo "=== 双 {locale} prefix → 404 确认 ==="
curl -sLo /dev/null -w "%{http_code}" "$BASE/{example-double-prefix-url}"
echo ""
curl -sLo /dev/null -w "%{http_code}" "$BASE/{example-double-prefix-url}"
echo ""
```

### Step 13：尾斜杠重定向循环检测（_redirects 冲突）

**问题背景：** 若在 `public/_redirects` 中手动添加 `/xxx/ → /xxx` 的尾斜杠 301 规则，会与 Cloudflare Pages 对「无尾斜杠目录」的默认 308 重定向互相冲突，形成 301 ↔ 308 死循环，报「重定向次数过多」。无论 `trailingSlash` 配置是 `never` 还是 `always`，都**不应**在 `_redirects` 中手动添加尾斜杠 301 规则。

**根因链：**
1. `/xxx/`（带斜杠）→ `_redirects` 规则 301 → `/xxx`（不带斜杠）
2. `/xxx`（不带斜杠，对应 dist/xxx/index.html 目录）→ Cloudflare Pages 默认 308 → `/xxx/`（带斜杠）
3. 回到第 1 步，无限循环。

**正确做法：** `trailingSlash` 已由 Astro 内置处理尾斜杠，**不应在 `_redirects` 中添加任何 `/xxx/ → /xxx` 尾斜杠 301 规则**；若已有，删除 `public/_redirects` 中的全部尾斜杠 301 规则即可。

**检查命令：**

```bash
# 对抽样页面分别请求「带斜杠」与「不带斜杠」URL，检测是否构成 301↔308 死循环
for P in "" "about" "contact" "{关键内页路径}"; do
  WITH_SLASH="$BASE/$P/"
  WITHOUT_SLASH="$BASE/$P"
  echo "=== /$P ==="
  echo -n "  带斜杠    $WITH_SLASH   → "
  curl -sI -o /dev/null -w "HTTP %{http_code} → %{redirect_url}\n" "$WITH_SLASH"
  echo -n "  不带斜杠  $WITHOUT_SLASH → "
  curl -sI -o /dev/null -w "HTTP %{http_code} → %{redirect_url}\n" "$WITHOUT_SLASH"
done

# 期望（trailingSlash: 'always'）：
# - 带斜杠 URL 直接 200
# - 不带斜杠 URL 最多一次 308/301 → 带斜杠（Cloudflare Pages 目录默认行为）
# - ❌ 绝不允许：带斜杠 301→不带斜杠，同时不带斜杠 308→带斜杠（这是死循环，页面会「重定向次数过多」）
# - 若命中死循环：删除 public/_redirects 中所有尾斜杠 301 规则后重新构建部署
```

### Step 14：内容结构层级与 Social Meta 检查（新增）

验证全站页面的标题层级结构（H1 唯一、H2 ≥ 2、H3 不跳级）与社交分享标签（OG / Twitter Card）是否齐备。**规则：单页面只能有 1 个 H1，但可有多个 H2/H3；H3 必须出现在 H2 之后（不得跳级）；OG 与 Twitter Card 需在 Head 中全局注入。**

**检查命令（首页 + 抽样内页循环）：**

```bash
# 循环抽样关键页面（将 {sample-pages} 替换为实际路径列表，如 "" "about" "blog" 等）
for P in {sample-pages}; do
  HTML=$(curl -sL "$BASE/$P/")
  H1=$(echo "$HTML" | grep -oP '<h1(?=[ >])' | wc -l)
  H2=$(echo "$HTML" | grep -oP '<h2(?=[ >])' | wc -l)
  H3=$(echo "$HTML" | grep -oP '<h3(?=[ >])' | wc -l)
  OG=$(echo "$HTML" | grep -oP '<meta[^>]*property="og:(title|description|image)"' | wc -l)
  TW=$(echo "$HTML" | grep -oP '<meta[^>]*name="twitter:(card|title|description|image)"' | wc -l)
  echo "=== /$P/  H1=$H1  H2=$H2  H3=$H3  OG=$OG  twitter=$TW ==="
  [ "$H1" -eq 1 ] && echo "  ✅ H1 唯一（1 个）" || echo "  ❌ H1 数量应为 1，当前 $H1"
  [ "$H2" -ge 2 ] && echo "  ✅ H2 ≥ 2（$H2 个）" || echo "  ❌ H2 应 ≥ 2，当前 $H2"
  if [ "$H3" -ge 1 ] && [ "$H2" -eq 0 ]; then
    echo "  ❌ H3 跳级：存在 $H3 个 h3 但无 h2"
  elif [ "$H3" -ge 1 ]; then
    echo "  ✅ H3 存在（$H3 个，嵌套于 h2 之下）"
  else
    echo "  ⚠️ H3 = 0（纯工具/落地页可接受，内容页需补充）"
  fi
  [ "$OG" -ge 3 ] && echo "  ✅ OG tags 齐备（$OG 项）" || echo "  ❌ og:title / og:description / og:image 需齐备，当前 $OG"
  [ "$TW" -ge 1 ] && echo "  ✅ Twitter Card 存在（$TW 项）" || echo "  ❌ twitter:card 缺失"
done
```

**期望阈值汇总：**

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| H1 | 恰好 1 个 | 唯一主题；多于 1 个需合并或降级为 H2/H3 |
| H2 | ≥ 2 个 | 内容分区，反映页面结构化程度（参考规范：每页至少 2 个 H2） |
| H3 | ≥ 1 个（内容页） | 长文子分区；纯工具页可为 0，但不得在 H2 之前出现 |
| OG tags | ≥ 3 项 | og:title / og:description / og:image（另建议 og:url / og:type / og:site_name） |
| Twitter Card | ≥ 1 项 | twitter:card 必须存在（twitter:title / description / image 建议齐备） |

**修复方式：**

1. **标题层级：** 保留唯一 H1，超出的标题按内容层级降级为 H2/H3；若源码中首个 H2 之前出现 H3，调整分区层级（大段落拆出 H2，再在 H2 下细分 H3）。
2. **OG/Social：** 在全局 `<Head>` 或公共 Layout 统一注入，各页面通过 frontmatter 传入 title/description/image；og:image 建议 1200×630 的 PNG/JPG 并稳定可访问（与 canonical 同域）。
3. **示例（Astro）：**

```astro
<meta property="og:title" content={title} />
<meta property="og:description" content={description} />
<meta property="og:image" content={image} />
<meta name="twitter:card" content="summary_large_image" />
```

### Step 15：性能检查（Lighthouse / PageSpeed Insights）（新增）

性能（Core Web Vitals + PageSpeed Insights）是 Google「页面体验」排名信号，检查时**以移动端为主**（可另跑 desktop 对比）。**统一使用 PageSpeed Insights API（必须携带 API Key）**；不使用本地 Lighthouse / 本地构建审计。

#### 15.1 指标体系与达标阈值

| 指标 | 全称 | 良好 ✅ | 需改进 ⚠️ | 差 ❌ | 说明 |
|------|------|--------|----------|------|------|
| Perf Score | Lighthouse Performance Score | ≥ 90 | 50–89 | ≤ 49 | 综合得分（移动端权重） |
| LCP | Largest Contentful Paint | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s | 最大内容绘制，**CWV 核心** |
| INP | Interaction to Next Paint | ≤ 200 ms | 200–500 ms | > 500 ms | 交互延迟，CWV 之一（2024 起替代 FID） |
| CLS | Cumulative Layout Shift | ≤ 0.10 | 0.10–0.25 | > 0.25 | 布局偏移，**CWV 核心** |
| FCP | First Contentful Paint | ≤ 1.8 s | 1.8–3.0 s | > 3.0 s | 首次内容绘制 |
| TBT | Total Blocking Time | ≤ 200 ms | 200–600 ms | > 600 ms | 主线程总阻塞时间（移动端权重高） |
| SI | Speed Index | ≤ 3.4 s | 3.4–5.8 s | > 5.8 s | 视觉呈现速度 |
| TTFB | Time To First Byte | ≤ 0.8 s | 0.8–1.8 s | > 1.8 s | 服务器响应（辅助信号，非评分项） |

**字段数据（CrUX 真实用户）分档：** `fast`（三项核心指标均 good）→ `average` → `slow`。Lighthouse/PSI 页面同时给出「实验室」与「字段」两组数据，实验室不达标可修复，字段不达标说明线上真实体验差。

#### 15.2 PageSpeed Insights API（唯一方式，需可访问 pagespeedonline.googleapis.com）

对齐官方接口：[Method: pagespeedapi.runpagespeed](https://developers.google.com/speed/docs/insights/rest/v5/pagespeedapi/runpagespeed?hl=zh-cn)。

**HTTP 请求（GET，请求正文必须为空）：**

```
GET https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed
```

**查询参数（对齐文档）：**

| 参数 | 是否必需 | 取值 | 说明 |
|------|----------|------|------|
| `url` | 必需 | 目标 URL | 要抓取并分析的网址 |
| `strategy` | 可选 | `MOBILE` / `DESKTOP` | 设备策略；文档默认 `DESKTOP`，性能检查需显式传 `MOBILE` |
| `category` | 可选 | `PERFORMANCE` / `SEO` / `ACCESSIBILITY` / `BEST_PRACTICES` | 可重复传多个；不传仅跑效果类 |
| `locale` | 可选 | 如 `zh-CN` | 本地化结果语言区域 |
| `utm_campaign` / `utm_source` | 可选 | string | 分析广告系列来源/名称 |
| `captchaToken` | 可选 | string | 通过人机识别时传递的令牌 |

```bash
# 文档对齐写法：pagespeedonline.googleapis.com 入口 + 大写枚举 + locale + API Key
# 访问 Google 需经本地代理（curl 自动读 HTTPS_PROXY，亦可显式 --proxy）
curl -s --max-time 120 --proxy "${HTTPS_PROXY:-http://127.0.0.1:7897}" "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed?url=${BASE}&strategy=MOBILE&category=PERFORMANCE&category=SEO&locale=zh-CN&key=${GOOGLE_PSI_API_KEY}" -o psi-mobile.json
# desktop 对照：strategy=DESKTOP

# === API Key 配置（重要）===
# 匿名调用每日额度为 0（实测返回 429 RESOURCE_EXHAUSTED, quota_limit_value="0"），必须携带 API Key。
# 1) 获取：Google Cloud Console 启用「PageSpeed Insights API」并创建 API Key（凭据页）：
#    https://console.cloud.google.com/apis/api/pagespeedonline.googleapis.com
# 2) 存入本地环境变量（切勿将 Key 明文写入本 skill 或代码仓库）：
#    export GOOGLE_PSI_API_KEY="<你的Key>"     # macOS/Linux
#    $env:GOOGLE_PSI_API_KEY="<你的Key>"       # Windows PowerShell
#    或使用本技能目录下的 .env：technology-seo-check/.env（已被 .gitignore 忽略，勿提交）
#    使用前加载（bash）：set -a; source technology-seo-check/.env; set +a
# 3) 鉴权替代：对照文档「授权范围」，亦支持 OAuth 范围 openid
```

**网络代理（重要）：** 本机访问 `pagespeedonline.googleapis.com` 必须经本地代理（`http://127.0.0.1:7897`，即环境变量 `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY`）。**不走代理会连接超时（`socket hang up`），勿误判为「额度耗尽」**。`curl` 会自动读取 `HTTPS_PROXY`、也可显式 `--proxy`；而 Node `https.get` **默认不走代理**（需显式配 proxy agent，或改用 `curl` / PowerShell `Invoke-WebRequest`）。

**API Key 获取与额度：**

| 项 | 说明 |
|----|------|
| 获取方式 | Cloud Console 启用 PageSpeed Insights API → 创建 API Key（凭据页） |
| 匿名额度 | **0 次/天**（必须带 Key，否则 429） |
| 默认免费额度 | 约 **25,000 次/天/项目**（精确值在 Console「配额」页查） |
| 重置时间 | **太平洋时间午夜**（PST/PDT） |
| 单次消耗 | 1 个 strategy = 1 unit；mobile+desktop 各跑一次 = 2 units；多 category 不额外计费 |
| 超额处理 | 返回 429 RESOURCE_EXHAUSTED，用指数退避重试（1s→2s→4s…），勿立即重发 |
| 安全 | Key 属敏感凭证，仅存本地 .env / 环境变量，**禁止提交仓库或写入本文件** |

#### 15.3 解析结果并汇总

```bash
node -e "
const raw=require('./psi-mobile.json');
const r=raw.lighthouseResult||raw;
const v=(id)=>r.audits[id]?.displayValue||'n/a';
const c=r.categories.performance;
const lab={score:Math.round(c.score*100),
  LCP:v('largest-contentful-paint'),FCP:v('first-contentful-paint'),
  TBT:v('total-blocking-time'),CLS:v('cumulative-layout-shift'),
  SI:v('speed-index'),TTFB:v('server-response-time'),
  INP:r.audits['interaction-to-next-paint']?v('interaction-to-next-paint'):'n/a(实验室)'};
console.log(JSON.stringify(lab,null,2));
console.log('CrUX 字段数据:', raw.loadingExperience?.overall_category ?? '无');
"
# PSI 的实验室数据在 lighthouseResult.*，字段数据在 loadingExperience
```

**关键审计项（audit id）与常见修复：**

| 审计项 | 常见根因 | 修复方式 |
|--------|----------|----------|
| LCP 元素加载慢 | hero 图未优化/未预加载、TTFB 慢、关键资源阻塞 | 图片转 webp/avif 并压缩；LCP 图加 `fetchpriority="high"` + `<link rel="preload" as="image">`；非视口图 `loading="lazy"`；关键 CSS 内联/提前 |
| CLS | 图片/iframe/字体无占位、顶部动态插入 | 媒体元素固定宽高或 `aspect-ratio` 占位；字体 `font-display: swap`；预留广告/横幅空间 |
| TBT / INP 高 | 大 JS bundle、长任务、组件过度水合 | 代码分割按需加载；Astro 静态优先、减少水合；第三方脚本 defer/延迟；长任务拆分 |
| TTFB 慢 | 回源慢、无缓存、未压缩 | Cloudflare 页面缓存；`_headers` 配 Cache-Control；开启 Brotli 压缩 |
| 图片未优化 | 体积大/格式老 | 批量转 webp 压缩；尺寸与展示一致；子集化字体 |

**缓存头示例（Astro `public/_headers`）：**

```
/assets/*
  Cache-Control: public, max-age=31536000, immutable
/og/*.png
  Cache-Control: public, max-age=86400
```
