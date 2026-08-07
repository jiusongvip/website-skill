---
name: site-seo-check
description: >-
  通用线上技术SEO审计技能，适配所有网站。curl线上页面审计基础信号(title/desc/H1/alt)、sitemap、文本重复、分页title、canonical尾斜杠、www重定向、内页抽样、内部链接尾斜杠。用户提供域名。触发词：SEO检查、网站SEO、seo check、技术SEO。
version: 1.2.0
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
BASE="https://{用户提供的域名}"
```

所有后续 curl 命令基于此 BASE URL。命令中的具体路径（如 /{list}、/{section}、/locale-path 等）需根据目标网站实际结构调整。

### Step 1：首页 SEO 基础信号

检查首页（`/`）的关键 SEO 信号是否达标。

**检查项：**

| 检查项 | 阈值 | 修复方式 |
|--------|------|----------|
| `<h1>` 存在 | 必须有至少 1 个 h1 | `sr-only` 或可见 h1 |
| `<title>` 长度 | 40-60 字符 | 扩展 i18n `page.home.seoTitle` |
| `<meta description>` 长度 | 140-160 字符 | 扩展 i18n `page.home.seoDescription` |
| `/sitemap.xml` 可访问 | 必须返回 200 或 301 | `public/sitemap.xml` → sitemap-index |
| `<img>` alt 属性 | 所有 img 必须有 alt | 逐一补齐 |

**检查命令：**

```bash
# H1（使用 -z 参数使 . 匹配换行符，解决跨行 H1 匹配问题）
curl -sL "$BASE/" | grep -oPz '(?s)<h1[^>]*>.*?</h1>' | head -3
# 期望：至少 1 个 h1

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
```

同样检查 {locale} 首页：

```bash
curl -sL "$BASE/{locale}/" | grep -oPz '(?s)<h1[^>]*>.*?</h1>' | head -3
curl -sL "$BASE/{locale}/" | grep -oP '<title>\K[^<]+' | wc -c
curl -sL "$BASE/{locale}/" | grep -oP '<meta name="description" content="\K[^"]+' | wc -c
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
- H1：{} ✅/❌
- Title 长度：{} chars (预期 40-60) ✅/❌
- Description 长度：{} chars (预期 140-160) ✅/❌
- sitemap.xml：{} ✅/❌
- 图片 alt 缺失：{} 个 (预期 0) ✅/❌

**Sitemap 完整性：**
- 尾部斜杠 URL：{} 个 (预期 0)
- 双 locale 前缀 URL：{} 个 (预期 0)
- 子文件可达性：{} / 6 个 200 ✅/❌

**Canonical / hreflang 一致性：**
- {primary-locale} 首页 + 关键页：逐页列出
- {locale} 首页 + 关键页：{} / 7 ✅/❌
- Canonical 尾斜杠：{} 个页面有尾斜杠 (预期 0) ✅/❌

**重定向链路：**
- http://example.com → {} ({301|302}) ✅/❌
- http://www.example.com → {} ({301|302|502|连接失败}) ✅/❌
- https://www.example.com → {} ({301|302|502|连接失败}) ✅/❌
- https://example.com → {} ({301|302}) ✅/❌

**内页抽样：**
- 抽样页面 1：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌
- 抽样页面 2：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌
- 抽样页面 3：title {} chars ✅/❌, desc {} chars ✅/❌, H1 ✅/❌, canonical ✅/❌

**内部链接尾斜杠：**
- 首页带尾斜杠的内部链接数：{} (预期 0) ✅/❌

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
- 尾斜杠 → 301 重定向：{} ✅/❌
- 双 {locale} 前缀 → 404：{} ✅/❌

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
### 新增检查项：线上特有信号

```bash
# robots.txt
curl -sL "$BASE/robots.txt"

# sitemap
curl -sL "$BASE/sitemap-index.xml" | head -20

# 响应状态码（首页、医院页、文章页）
curl -sLo /dev/null -w "%{http_code}" "$BASE/"
curl -sLo /dev/null -w "%{http_code}" "$BASE/{list-page}/{example-hospital-page}/"
curl -sLo /dev/null -w "%{http_code}" "$BASE/{section}/"
```

### Step 7：Sitemap 完整性检查

验证 sitemap 中的 URL 无尾部斜杠、无双 locale 前缀。这两个是已知曾导致 GSC 报错的问题。

**问题背景：**

| GSC 问题类型 | 根因 | 修复 | GSC 消退 |
|-------------|------|------|----------|
| "备用网页（有适当的规范标记）" | canonical 有 `/` 但 hreflang 自引用无 `/`，Google 拆成两个 URL | `trailingSlash: 'never'` | 部署后重新抓取 |
| "已发现 — 尚未编入索引" | 分页链接如 `/{list}/10/` 带 `/`，Google 抓到但未索引 | `trailingSlash: 'never'` | 部署后重新抓取 |
| "未找到 (404)" | `/{example-double-prefix-url}` 等双 locale 前缀 — 历史构建 bug，当前构建不产出 | 确认当前不产出，历史 404 自然消退 | 部署后 GSC 验证修复 |
| "未找到 (404)" | `/{list}/xxx/` 尾部斜杠导致 404 | `trailingSlash: 'never'` | 部署后重新抓取 |
| "网页会自动重定向" | `http://` / `example.com` 跳转到 `https://{用户提供的域名}` — 正常 Nginx 行为 | 确认是 301 非 302 | 无需修复 |

**检查命令：**

```bash
# === 尾部斜杠检查 ===
# 抽取 sitemap 前 50 个 URL，检索是否以 "/" 结尾
curl -sL "$BASE/{sitemap-name}.xml" | grep -oP '<loc>\K[^<]+' | head -50 | grep '/$' | wc -l
# 期望：0

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

canonical URL 必须与页面实际访问 URL 完全一致（包括尾斜杠）。对于 `trailingSlash: 'never'` 的 Astro 项目，canonical 不应有尾斜杠。常见问题：`new URL('/', site).href` 对根路径返回带 `/` 的 URL，导致首页 canonical 与实际 URL 不一致。

**检查命令：**

```bash
# 抽样检查首页和关键子页面
for PAGE in "" {及网站关键页面路径}; do
  echo "=== $BASE$PAGE ==="
  CANONICAL=$(curl -sL "$BASE$PAGE" | grep -oP '<link rel="canonical" href="\K[^"]+')
  HREFLANG_SELF=$(curl -sL "$BASE$PAGE" | grep -oP '<link rel="alternate" hreflang="{primary-locale}" href="\K[^"]+')
  echo "  canonical: $CANONICAL"
  echo "  hreflang {primary-locale}: $HREFLANG_SELF"
  
  # 检查 canonical 尾斜杠
  if [[ "$CANONICAL" == */ ]]; then
    echo "  ❌ canonical 有尾斜杠！"
  else
    echo "  ✅ canonical 无尾斜杠"
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
  
  # 检查 canonical 尾斜杠
  if [[ "$CANONICAL" == */ ]]; then
    echo "  ❌ canonical 有尾斜杠！"
  else
    echo "  ✅ canonical 无尾斜杠"
  fi
  
  if [ "$CANONICAL" = "$HREFLANG_SELF" ]; then
    echo "  ✅ canonical 与 hreflang 一致"
  else
    echo "  ❌ canonical 与 hreflang 不一致！"
  fi
done
```

### Step 9：重定向链路检查

验证 HTTP → HTTPS 和 www → 裸域 的 301 重定向正确，且为重定向直链（非多次跳转）。

**已知正常模式：**
- `http://example.com` → 301 → `https://{用户提供的域名}`（理想：一跳直达，非两跳 `http://example.com` → `https://example.com` → `https://{用户提供的域名}`）
- `http://www.example.com` → 301 → `https://{用户提供的域名}`
- `https://www.example.com` → 301 → `https://{用户提供的域名}`
- `https://example.com` → 301 → `https://{用户提供的域名}`

**www 子域可达性检查（新增）：**

如果 www 子域返回 502 或无法访问，说明 Cloudflare Pages 未配置 www 自定义域。必须在 Cloudflare Pages 自定义域设置中添加 www 子域，Cloudflare 会自动处理 DNS、SSL 和 301 重定向。

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
# - 最终目标均为 https://{用户提供的域名}/
# - www 子域必须可达（返回 301 或 200），不能是 502 或连接失败
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
  
  # H1
  H1_COUNT=$(echo "$HTML" | grep -oPz '(?s)<h1[^>]*>.*?</h1>' | wc -l)
  echo "  h1 count: $H1_COUNT"
  if [ $H1_COUNT -eq 0 ]; then
    echo "  ❌ 缺少 H1"
  else
    echo "  ✅ H1 存在"
  fi
  
  # Canonical 尾斜杠
  CANONICAL=$(echo "$HTML" | grep -oP '<link rel="canonical" href="\K[^"]+')
  if [[ "$CANONICAL" == */ ]]; then
    echo "  ❌ canonical 有尾斜杠：$CANONICAL"
  else
    echo "  ✅ canonical 无尾斜杠：$CANONICAL"
  fi
done
```

### Step 11：内部链接尾斜杠检查（新增）

检查页面内 `<a href>` 链接是否带尾斜杠。对于 `trailingSlash: 'never'` 的 Astro 项目，内部链接不应有尾斜杠。

**检查命令：**

```bash
# 检查首页内部链接
echo "=== 首页内部链接尾斜杠检查 ==="
curl -sL "$BASE/" | grep -oP 'href="\K[^"]+' | grep -E '^/' | grep '/$' | head -10
# 期望：无输出（内部链接无尾斜杠）

# 统计带尾斜杠的内部链接数量
TRAILING_SLASH_COUNT=$(curl -sL "$BASE/" | grep -oP 'href="\K[^"]+' | grep -E '^/' | grep '/$' | wc -l)
echo "带尾斜杠的内部链接数：$TRAILING_SLASH_COUNT"
# 期望：0
```

### Step 12：404 已知遗留 URL 确认

对 GSC 中报告过的已知 404 模式进行抽样确认。

**已知 404 模式：**

| 模式 | 示例 | 来源 |
|------|------|------|
| 双 locale 前缀 | `/{example-double-prefix-url}` | 历史构建 bug（sitemap 中无此 URL） |
| 尾斜杠单页面 | `/{list}/{example-page}/` | `trailingSlash: 'always'` 旧构建 |

```bash
# 部署 trailingSlash: 'never' 后，带 / 的旧 URL 应返回 301 → 新 URL
echo "=== 尾斜杠 → 301 重定向验证 ==="
curl -sI "$BASE/about/" | head -3
curl -sI "$BASE/contact/" | head -3
curl -sI "$BASE/{list-page}/10/" | head -3

# 双 locale 前缀仍应为 404（不会产出）
echo "=== 双 {locale} prefix → 404 确认 ==="
curl -sLo /dev/null -w "%{http_code}" "$BASE/{example-double-prefix-url}"
echo ""
curl -sLo /dev/null -w "%{http_code}" "$BASE/{example-double-prefix-url}"
echo ""
```
