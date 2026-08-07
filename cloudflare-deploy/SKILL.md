---
name: cloudflare-deploy
description: >
  Cloudflare Pages 部署技能。输入一个 GitHub 仓库 URL 即可完成部署，
  覆盖代码拉取、配置自动修复、本地构建、推送、API 创建 Git 连接项目、
  触发部署、验证全流程。覆盖常见坑点：构建命令、API Token 权限、
  GitHub 推送代理、sitemap 验证、合并冲突处理。
---

# Cloudflare Pages 部署技能

## 核心配置

```bash
# Cloudflare API Token（Pages:Edit 权限）
CLOUDFLARE_API_TOKEN=YOUR_CLOUDFLARE_API_TOKEN

# Account ID
CLOUDFLARE_ACCOUNT_ID=13a7eab517e3e621f07a73165ee592be
```

---

## 一键部署流程（输入：仓库 URL）

**输入示例：** `https://github.com/{USER}/{REPO}` 或本地项目目录

**执行前确认：**
- 项目名 = 仓库名（如 `best-of-chengdu`）
- 本地工作区根目录：`d:\workspaces\website\{REPO}`

### Step 0: 获取代码

两种入口二选一：

**A. 已有本地目录** → 跳过本步，进入 Step 1

**B. 只有仓库 URL** → clone 到本地：

```bash
cd d:\workspaces\website
git clone https://ghfast.top/https://github.com/{USER}/{REPO}.git
```

> 必须用 `ghfast.top` 代理 clone（github.com:443 被墙）。clone 后立即把 remote 恢复为原始 URL。

### Step 1: 拉取最新代码（避免冲突）

**必须先拉取再修改，否则极易产生非 fast-forward 拒绝或合并冲突。**

```bash
cd {PROJECT_DIR}
git status                      # 若有未提交改动，先 stash
git stash                       # 仅当有本地改动时
git branch -a                   # 确认分支名（master / main，不要假设！）
git remote set-url origin https://ghfast.top/https://github.com/{USER}/{REPO}.git
git pull origin {BRANCH} --rebase
git remote set-url origin https://github.com/{USER}/{REPO}.git
git stash pop                   # 恢复本地改动（仅当之前 stash 了）
```

**冲突处理：**
- 拉取后 `git status` 若显示 `both modified` 文件，说明有冲突
- 查看冲突文件 → 保留更完整的版本（通常远程改动更新）
- `git add {冲突文件}` → `git commit --no-edit` 完成合并
- 注意：解决冲突后**必须重新构建验证**，因为配置文件可能已变化

### Step 2: 自动检查并修复项目配置

**每个项目逐项检查（发现问题立即修复）：**

| 检查项 | 修复方式 |
|--------|----------|
| `package.json` build 脚本是否含 `astro check && astro build` 或裸 `astro build` | 改为 `"build": "npx astro build"` |
| `astro.config.mjs` 是否有 sitemap 集成 | 无则 `npm install @astrojs/sitemap` + 添加 `import sitemap from "@astrojs/sitemap"` + `integrations: [...sitemap()]` |
| `package.json` 是否缺 `@astrojs/sitemap` 依赖 | `npm install @astrojs/sitemap` |
| `astro.config.mjs` 的 `site` 字段 | 确认填了最终域名（如 `https://example.com`） |
| 分支名 | `git branch` 确认是 `master` 还是 `main`，后续 API 调用和 push 都用它 |

> **经验：** 几乎所有旧项目 build 脚本都是 `astro build`，必须改成 `npx astro build`，否则 Cloudflare 构建环境报 `astro: not found`。约半数项目缺 sitemap，需补装。

### Step 3: 本地构建验证

```bash
cd {PROJECT_DIR}
npx astro build 2>&1 | Select-Object -Last 8
```

**成功标志：**
- 输出 `sitemap-index.xml created at dist`
- 输出 `[build] Complete!` 和页面数量
- 构建时间过长（>2 分钟）属正常，Cloudflare 默认超时 20 分钟

**验证 dist：**
```bash
dir dist\sitemap*
# 预期：sitemap-index.xml + sitemap-0.xml
```

### Step 4: 推送代码到 GitHub

```bash
cd {PROJECT_DIR}
git add -A
git commit -m "fix: use npx astro build and add sitemap integration"   # 有改动才 commit
git remote set-url origin https://ghfast.top/https://github.com/{USER}/{REPO}.git
git push origin {BRANCH}
git remote set-url origin https://github.com/{USER}/{REPO}.git   # 恢复原始 URL
```

> 若 push 报 `non-fast-forward`：说明远程有新提交，回到 Step 1 重新 pull --rebase。

### Step 5: API 创建 Git 连接项目（一步到位）

```powershell
$env:TOKEN="YOUR_CLOUDFLARE_API_TOKEN"
$env:AID="13a7eab517e3e621f07a73165ee592be"

$body = @{
  name = "{PROJECT_NAME}"
  production_branch = "{BRANCH}"
  build_config = @{
    build_command = "npm run build"
    destination_dir = "dist"
    root_dir = ""
  }
  source = @{
    type = "github"
    config = @{
      owner = "{GITHUB_USER}"
      repo_name = "{REPO_NAME}"
      production_branch = "{BRANCH}"
      deployments_enabled = $true
    }
  }
} | ConvertTo-Json -Depth 4

$resp = Invoke-RestMethod `
  -Uri "https://api.cloudflare.com/client/v4/accounts/$env:AID/pages/projects" `
  -Method POST `
  -Headers @{Authorization="Bearer $env:TOKEN"} `
  -ContentType "application/json" `
  -Body $body

"$($resp.result.name) | $($resp.result.subdomain)"
```

> **核心优势：** 一次 API 调用同时完成项目创建 + Git 连接 + 构建配置，无需手动到 Dashboard。前提是 Cloudflare Pages GitHub App 已在账号上授权（通常首次使用 Pages 时已授权）。

**项目已存在时：** API 会报错（如 409/1101）。此时应改为**查询项目状态**（见 API 速查），确认 Git 连接和构建配置无误后直接进入 Step 6 触发重新部署。

### Step 6: 触发首次部署

API 创建项目后，需要一次 `git push` 触发 webhook 启动首次构建：

```bash
cd {PROJECT_DIR}
git commit --allow-empty -m "chore: trigger Cloudflare Pages deployment"
git remote set-url origin https://ghfast.top/https://github.com/{USER}/{REPO}.git
git push origin {BRANCH}
git remote set-url origin https://github.com/{USER}/{REPO}.git
```

部署完成后等待约 30 秒（大型项目更久），访问 `https://{PROJECT_NAME}.pages.dev`。

### Step 7: 验证部署

```powershell
# 检查部署状态（预期 latest_stage.status = success）
$resp = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts/$env:AID/pages/projects/{PROJECT_NAME}/deployments?per_page=1" -Method GET -Headers @{Authorization="Bearer $env:TOKEN"}
$resp.result[0].latest_stage | Select-Object name,status

# 验证 sitemap（若返回 522 属缓存延迟，等 10 秒重试即可）
curl -sI https://{PROJECT_NAME}.pages.dev/sitemap-index.xml | Select-String "HTTP"
```

### Step 8: 线上技术 SEO 审计

部署成功后，对线上页面做基础 SEO 信号检查。以下命令基于 `https://{PROJECT_NAME}.pages.dev`（或自定义域名）。

#### 8a. 首页基础信号

```powershell
# H1 检查
curl -sL "https://{PROJECT_NAME}.pages.dev/" | Select-String -Pattern '<h1[ >]' -AllMatches | ForEach-Object { $_.Matches.Count }
# 期望：>= 1

# Title 长度
$title = curl -sL "https://{PROJECT_NAME}.pages.dev/" | Select-String '<title>([^<]+)</title>' | ForEach-Object { $_.Matches.Groups[1].Value }
$title.Length
# 期望：40-65

# Meta description 长度
$desc = curl -sL "https://{PROJECT_NAME}.pages.dev/" | Select-String '<meta name="description" content="([^"]+)"' | ForEach-Object { $_.Matches.Groups[1].Value }
if ($desc) { "desc length: $($desc.Length)" } else { "❌ 缺少 meta description" }
# 期望：140-160

# 图片 alt 缺失
(curl -sL "https://{PROJECT_NAME}.pages.dev/" | Select-String '<img ' -AllMatches).Matches | Where-Object { $_.Value -notmatch 'alt=' } | Measure-Object | Select-Object -ExpandProperty Count
# 期望：0
```

#### 8b. robots.txt & sitemap

```powershell
# robots.txt
curl -s "https://{PROJECT_NAME}.pages.dev/robots.txt"
# 期望：包含 Sitemap 行，Allow: /

# sitemap 可访问
curl -sI "https://{PROJECT_NAME}.pages.dev/sitemap-index.xml" | Select-String "HTTP"
curl -sI "https://{PROJECT_NAME}.pages.dev/sitemap-0.xml" | Select-String "HTTP"
# 期望：均 200
```

#### 8c. 内页抽样

从项目页面中抽 2-3 个关键内页检查 title/desc/H1：

```powershell
@("/about", "/faq") | ForEach-Object {
  $url = "https://{PROJECT_NAME}.pages.dev$_"
  Write-Host "=== $url ==="
  $html = curl -sL $url
  # Title
  $t = [regex]::Match($html, '<title>([^<]+)</title>').Groups[1].Value
  Write-Host "  title: $t ($($t.Length) chars)"
  # H1 count
  $h1 = ([regex]::Matches($html, '<h1[ >]')).Count
  Write-Host "  h1: $h1"
}
```

#### 8d. 汇总报告

检查完成后输出简洁报告：

```
## 技术 SEO 审计 — {PROJECT_NAME}

**线上 URL：** https://{PROJECT_NAME}.pages.dev

| 检查项 | 结果 |
|--------|------|
| 首页 H1 | {} 个 ✅/❌ |
| 首页 Title 长度 | {} chars (40-65) ✅/❌ |
| 首页 Description | {} chars (140-160) ✅/❌ |
| 首页 img alt 缺失 | {} 个 (0) ✅/❌ |
| robots.txt | ✅/❌ |
| sitemap-index.xml | {} ✅/❌ |
| 内页 title/H1 | ✅/❌ |
```

### Step 9: 通知用户完成后续操作

- **绑定自定义域名**：https://dash.cloudflare.com/{ACCOUNT_ID}/pages/view/{PROJECT_NAME} → 自定义域 → 添加 `example.com`（域名需已在 Cloudflare DNS）
- **Google Search Console**：提交 `https://example.com/sitemap-index.xml`，首次"无法抓取"正常，等 5-10 分钟

---

## 常见坑点速查

| 问题 | 原因 | 解决 |
|------|------|------|
| push 报 `non-fast-forward` | 远程有新提交，本地没拉 | `git pull origin {BRANCH} --rebase` 后再 push |
| pull 产生 `both modified` 冲突 | 双方都改了同一文件（常见 astro.config.mjs） | 保留更完整版本 → `git add` → `git commit --no-edit` → 重新构建 |
| `astro: not found` | build 脚本用裸 `astro build` | 改为 `npx astro build` |
| 缺少 `sitemap-index.xml` | 项目没装 @astrojs/sitemap | `npm install @astrojs/sitemap` + 添加到 integrations |
| API 返回 8000006 | Token 权限不足 | Token 需 `Pages:Edit` 权限 |
| `CLOUDFLARE_API_TOKEN` 不生效 | PowerShell 环境变量语法 | 用 `$env:CLOUDFLARE_API_TOKEN = "..."` |
| GitHub 操作超时 | github.com:443 被墙 | 全部 git 命令走 `ghfast.top` 代理 |
| push 报 `refspec main does not match` | 实际分支是 `master` | 先 `git branch -a` 确认，不要假设 |
| push 报 `workflow scope` 错误 | Token 无 workflow 权限 + 仓库有 `.github/workflows/` | 删除 workflow 文件或换 token |
| API 创建项目成功但无部署 | webhook 未触发 | 执行 `git commit --allow-empty` + push 触发首次构建 |
| API 创建项目报项目已存在 | 项目之前创建过 | 改为查询项目状态，直接 push 触发重新部署 |
| sitemap 返回 522 | 部署后缓存未就绪 | 等 10 秒重试，正常现象 |
| 自定义域名绑定失败 | 需要 OAuth 授权 | 用户必须在浏览器操作（API Token 无 DNS 权限时 CNAME 也不会自动建） |
| sitemap 显示"无法抓取" | Google 还没处理 | 正常现象，等几分钟刷新 |

---

## 一键部署参数速查

| 参数 | 来源 | 示例 |
|------|------|------|
| `{USER}` | 仓库 URL | `jiusongvip` |
| `{REPO}` | 仓库 URL | `best-of-chengdu` |
| `{PROJECT_NAME}` | = 仓库名 | `best-of-chengdu` |
| `{BRANCH}` | `git branch -a` 确认 | `master` 或 `main` |
| `{PROJECT_DIR}` | `d:\workspaces\website\{REPO}` | `d:\workspaces\website\best-of-chengdu` |

---

## API 速查

```bash
# 创建 Git 连接项目（推荐方式）
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PROJECT_NAME",
    "production_branch": "master",
    "build_config": {
      "build_command": "npm run build",
      "destination_dir": "dist"
    },
    "source": {
      "type": "github",
      "config": {
        "owner": "GITHUB_USER",
        "repo_name": "REPO_NAME",
        "production_branch": "master",
        "deployments_enabled": true
      }
    }
  }'

# 查看项目信息（含 source 是否 github 连接）
curl -s "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects/$NAME" \
  -H "Authorization: Bearer $TOKEN"

# 查看最近部署
curl -s "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects/$NAME/deployments?per_page=3" \
  -H "Authorization: Bearer $TOKEN"

# 查看部署日志
curl -s "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects/$NAME/deployments/$DEPLOY_ID/history/logs" \
  -H "Authorization: Bearer $TOKEN"

# 更新项目构建配置（项目已存在时用 PUT）
curl -s -X PATCH "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects/$NAME" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"build_config":{"build_command":"npm run build","destination_dir":"dist"}}'

# 删除项目
curl -s -X DELETE "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects/$NAME" \
  -H "Authorization: Bearer $TOKEN"

# 查看域名列表
curl -s "https://api.cloudflare.com/client/v4/zones?name=$DOMAIN" \
  -H "Authorization: Bearer $TOKEN"
```
