---
name: performance-check
description: >-
  站点性能专项检查技能（Core Web Vitals + Lighthouse）。对给定 URL 跑 PageSpeed Insights API（方式 A，需 API Key）或本地 Chrome Lighthouse（方式 B），输出 Performance/SEO 得分、LCP/INP/CLS/FCP/TBT/SI/TTFB、CrUX 字段数据与优化机会清单，并对照阈值判定。适用于每次性能优化后单独复测。触发词：性能检查、测试性能、性能测试、跑性能、复测性能、performance check、PageSpeed、Lighthouse。
version: 1.0.1
metadata:
  hermes:
    tags: [performance, core-web-vitals, lighthouse, pagespeed, daily-check]
    related_skills: [technology-seo-check]
---

# 站点性能专项检查

## 触发条件

用户说 "性能检查"、"测试性能"、"性能测试"、"跑个性能"、"复测性能"、"performance check"，或提供 URL 要求测性能时调用本 skill。**只做性能，不做 title/canonical/sitemap 等技术 SEO 检查**（那些走 `technology-seo-check`）。

## 核心原则

- **默认移动端**（可另跑 desktop 对照）。
- **优先方式 A（PSI API，Google 真实环境）**；若 Google 不可达或需要无依赖复测，用**方式 B（本地 Chrome Lighthouse）**。线上域名不可解析时，方式 B 可审计本地 `dist`。
- 结果必须对照阈值给出 ✅/⚠️/❌ 判定，并列出优化机会。

## 输入

- **目标 URL**：线上 `https://...`，或本地 `http://127.0.0.1:4173/`（配合 `dist`）。

## 准备：加载 API Key（仅方式 A 需要）

API Key 存于**本技能目录**的 `.env`（`performance-check/.env`，与 `technology-seo-check` 相互独立、互不依赖；已被 `.gitignore` 的 `*.env` 忽略，勿提交）。调用前先加载到环境变量 `GOOGLE_PSI_API_KEY`：

```bash
# 在技能目录下（bash / WSL / Git Bash）
set -a; source .env; set +a
```

```powershell
# Windows PowerShell
Get-Content .env | Where-Object { $_ -match '^GOOGLE_PSI_API_KEY=' } | ForEach-Object { $env:GOOGLE_PSI_API_KEY = $_.Split('=',2)[1] }
```

> 匿名调用每日额度为 **0**（实测返回 429 `RESOURCE_EXHAUSTED`），**必须携带 API Key**。

## 方式 A：PageSpeed Insights API

```bash
BASE="https://www.example.com"   # 换成目标 URL
curl -s --max-time 150 "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed?url=${BASE}&strategy=MOBILE&category=PERFORMANCE&category=SEO&locale=zh-CN&key=${GOOGLE_PSI_API_KEY}" -o psi-mobile.json -w "HTTP:%{http_code} SIZE:%{size_download}\n"
# desktop 对照：strategy=DESKTOP
```

- 请求：`GET`，正文为空；入口 `pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed`（[官方文档](https://developers.google.com/speed/docs/insights/rest/v5/pagespeedapi/runpagespeed?hl=zh-cn)）。
- 关键参数：`url`（必需）、`strategy`（`MOBILE`/`DESKTOP`，默认 DESKTOP）、`category`（可重复）、`locale`、`key`。
- 额度：默认约 **25,000 次/天/项目**（PST 午夜重置）；单 strategy=1 unit，mobile+desktop 各一次=2 units；多 category 不额外计费；超额 429 用指数退避重试。
- 期望返回 `HTTP:200`；返回 `429` 说明未带 Key 或额度耗尽。

## 方式 B：本地 Chrome Lighthouse（无 Google 依赖）

```bash
# 审计线上 URL（自动探测本机 Chrome）
npx -y lighthouse "$BASE" --only-categories=performance,seo --form-factor=mobile \
  --output=json --output-path=./lh-mobile.json --quiet --chrome-flags="--headless=new --no-sandbox"

# 线上不可达 / 域名未解析 → 审计本地 dist：
#   cd <站点目录> && npm run build
#   npx -y serve dist        # 或 python -m http.server 4173 -d dist
npx -y lighthouse "http://127.0.0.1:4173/" --only-categories=performance,seo --form-factor=mobile \
  --output=json --output-path=./lh-mobile.json --quiet --chrome-flags="--headless=new --no-sandbox"

# desktop 对照：--form-factor=desktop --screenEmulation.mobile=false
```

## 解析结果

对本技能自带的解析脚本运行（同时兼容 PSI 与 Lighthouse 两种 JSON）：

```bash
node scripts/report.js psi-mobile.json     # 或 lh-mobile.json
```

脚本输出：各项指标、LCP 分解、优化机会（opportunity）、体积类建议（`*-insight`）。PSI JSON 的实验室数据在 `lighthouseResult.*`，字段数据在 `loadingExperience`。

## 达标阈值（移动端）

| 指标 | 全称 | 良好 ✅ | 需改进 ⚠️ | 差 ❌ | 说明 |
|------|------|--------|----------|------|------|
| Performance | Lighthouse 综合分 | ≥ 90 | 50–89 | ≤ 49 | 移动端权重 |
| LCP | Largest Contentful Paint | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s | CWV 核心 |
| INP | Interaction to Next Paint | ≤ 200 ms | 200–500 ms | > 500 ms | CWV（替代 FID） |
| CLS | Cumulative Layout Shift | ≤ 0.10 | 0.10–0.25 | > 0.25 | CWV 核心 |
| FCP | First Contentful Paint | ≤ 1.8 s | 1.8–3.0 s | > 3.0 s | 首屏内容 |
| TBT | Total Blocking Time | ≤ 200 ms | 200–600 ms | > 600 ms | 移动端权重高 |
| SI | Speed Index | ≤ 3.4 s | 3.4–5.8 s | > 5.8 s | 视觉呈现速度 |
| TTFB | Time To First Byte | ≤ 0.8 s | 0.8–1.8 s | > 1.8 s | 辅助信号（非评分项） |

**字段数据（CrUX 真实用户）：** `fast`（三项核心均 good）→ `average` → `slow`。无字段数据说明该站/源站样本不足，以实验室数据为准。

## 报告模板

```
## 性能报告 — {日期}（{MOBILE|DESKTOP}）

**URL：** {url}

| 指标 | 结果 | 阈值 | 判定 |
|------|------|------|------|
| Performance | {} / 100 | ≥ 90 | ✅/⚠️/❌ |
| LCP | {} s | ≤ 2.5 | ✅/⚠️/❌ |
| INP | {} ms | ≤ 200 | ✅/⚠️/❌ |
| CLS | {} | ≤ 0.10 | ✅/⚠️/❌ |
| FCP | {} s | ≤ 1.8 | ✅/⚠️/❌ |
| TBT | {} ms | ≤ 200 | ✅/⚠️/❌ |
| SI | {} s | ≤ 3.4 | ✅/⚠️/❌ |
| TTFB | {} sf | ≤ 0.8 | ✅/⚠️/❌ |
| CrUX 字段 | {fast/average/slow/无} | — | — |

**优化机会（按影响排序）：** {列出节省 ms/KiB 的项}
**结论与建议：** {1-3 条}
```

## 优化对照（audit → 根因 → 修复）

| 问题 | 常见根因 | 修复方式 |
|------|----------|----------|
| LCP 慢 | hero 图未优化/未预加载、TTFB 慢、关键资源阻塞 | 图片转 webp/avif 并压缩；LCP 图加 `fetchpriority="high"` + `<link rel="preload" as="image">`；非视口图 `loading="lazy"`；关键 CSS 内联/提前 |
| CLS 高 | 图片/iframe/字体无占位、顶部动态插入 | 媒体元素固定宽高或 `aspect-ratio` 占位；字体 `font-display: swap`；预留广告/横幅空间 |
| TBT / INP 高 | 大 JS bundle、长任务、组件过度水合 | 代码分割按需加载；Astro 静态优先、减少水合；第三方脚本 defer/延迟；长任务拆分 |
| TTFB 慢 | 回源慢、无缓存、未压缩 | Cloudflare 页面缓存；`_headers` 配 Cache-Control；开启 Brotli 压缩 |
| 图片未优化（image-delivery） | 体积大/格式老/尺寸过大 | 批量转 webp/avif；尺寸与展示一致；子集化字体 |

缓存头示例（Astro `public/_headers`）：

```
/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

## 注意事项

- 同一站点不同环境下（本地 vs Google）分数会有差异，属正常；**看趋势与失分项，而非绝对分**。
- LCP 的"观察值分解"与最终展示值可能因节流不同而差异较大，以展示值判定、以分解定位瓶颈。
- CrUX 无数据是正常（流量不足），不要当作错误。
- 结果 JSON 与解析脚本输出可留存对比；临时文件用完可清理。
