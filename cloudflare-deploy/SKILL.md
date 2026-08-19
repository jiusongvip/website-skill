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
# Cloudflare API Token（需 Pages:Edit + Zone DNS:Edit + Zone Dynamic URL Redirects:Edit 三项权限）
# 凭证保存在同目录 .env 文件（已加入 .gitignore，严禁提交）
# 使用前加载：Get-Content .env | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] } }
CLOUDFLARE_API_TOKEN=<见 .env>

# Account ID
CLOUDFLARE_ACCOUNT_ID=<见 .env>
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
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 clone https://github.com/{USER}/{REPO}.git
```

> 用系统代理 `127.0.0.1:7897` clone（github.com:443 被墙；`ghfast.top` 已失效，不再使用）。

### Step 1: 拉取最新代码（避免冲突）

**必须先拉取再修改，否则极易产生非 fast-forward 拒绝或合并冲突。**

```bash
cd {PROJECT_DIR}
git status                      # 若有未提交改动，先 stash
git stash                       # 仅当有本地改动时
git branch -a                   # 确认分支名（master / main，不要假设！）
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 pull origin {BRANCH} --rebase
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
| `astro.config.mjs` 的 `site` 字段 | 填最终域名 `https://www.{域名}`（统一带 www 前缀） |
| `astro.config.mjs` 的 `trailingSlash` | 设为 `"always"`（内页带尾斜杠，首页根域名例外） |
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
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin {BRANCH}
```

> 若 push 报 `non-fast-forward`：说明远程有新提交，回到 Step 1 重新 pull --rebase。

### Step 5: API 创建 Git 连接项目（一步到位）

```powershell
$env:TOKEN = $env:CLOUDFLARE_API_TOKEN
$env:AID = $env:CLOUDFLARE_ACCOUNT_ID

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
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin {BRANCH}
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

> ⚠️ **审计已改用 `technology-seo-check` skill（v1.2.0），URL 规范与旧版有重大区别：**
>
> | 规范项 | 旧规范 | 新规范（technology-seo-check） |
> |--------|--------|-------------------------------|
> | 正式域名 | 裸域名 `https://{域名}` | 带 www `https://www.{域名}` |
> | trailingSlash | `never`（不带尾斜杠） | `always`（内页带尾斜杠） |
> | 首页根域名 | 不带尾斜杠 | 不带尾斜杠（例外规则） |
> | 裸域名 | 直接 200 | 必须 301 跳转到 www |
> | sitemap 首页 | 不带尾斜杠 | 不带尾斜杠（需 `fix-sitemap-home.mjs` 构建后处理） |
>
> 完整 13 步审计流程见 `website-skill/technology-seo-check/SKILL.md`。下方 8a-8d 仅作部署后 pages.dev 快速可达性验证。

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

### Step 9: 绑定自定义域名 + 裸域名跳 www + 替换硬编码域名

部署完成后，依次完成域名绑定、裸域名跳转、硬编码替换三步。

#### 9a. API 绑定自定义域名（自动创建 CNAME）

Token 需同时具备 `Pages:Edit` + `Zone DNS:Edit` 权限，绑定时 Cloudflare 会自动创建 CNAME 记录指向 `{PROJECT_NAME}.pages.dev`。

```powershell
$env:TOKEN = $env:CLOUDFLARE_API_TOKEN
$env:AID = $env:CLOUDFLARE_ACCOUNT_ID

# 同时绑定裸域名 + www 子域
foreach ($d in @("example.com", "www.example.com")) {
  $body = @{ name = $d } | ConvertTo-Json
  $r = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts/$env:AID/pages/projects/{PROJECT_NAME}/domains" `
    -Method POST -Headers @{Authorization="Bearer $env:TOKEN"} -ContentType "application/json" -Body $body
  "绑定 $d → success=$($r.success)"
}
```

> 若返回 `already added`（code 8000018），说明该域名已绑定过，跳过即可。

#### 9b. 裸域名 301 跳转 www（Dynamic URL Redirects）

Token 需 `Zone → Dynamic URL Redirects → Edit` 权限。通过 Rulesets API 在 `http_request_dynamic_redirect` 阶段创建/更新重定向规则。

```powershell
# 获取 zone id
$zid = (Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones?name=example.com" `
  -Headers @{Authorization="Bearer $env:TOKEN"}).result[0].id

# 先读取现有规则（避免覆盖已有的规则）
$existing = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$zid/rulesets/phases/http_request_dynamic_redirect/entrypoint" `
  -Headers @{Authorization="Bearer $env:TOKEN"}

$rule = @{
  expression = 'http.host eq "example.com"'
  description = "Redirect root to WWW"
  action = "redirect"
  action_parameters = @{
    from_value = @{
      status_code = 301
      target_url = @{ expression = 'concat("https://www.example.com", http.request.uri.path)' }
      preserve_query_string = $true
    }
  }
}

$rules = @($rule)
if ($existing.result.rules) { $rules += $existing.result.rules }

$body = @{
  name = "Redirect rules ruleset"
  kind = "zone"
  phase = "http_request_dynamic_redirect"
  rules = $rules
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$zid/rulesets/phases/http_request_dynamic_redirect/entrypoint" `
  -Method PUT -Headers @{Authorization="Bearer $env:TOKEN"} -ContentType "application/json" -Body $body
```

> 若该 zone 已在 Dashboard 配置过「Redirect from root to WWW」模板，无需重复创建。

#### 9c. 替换硬编码域名

用户最终域名（如 `chinese-tea.com` → `chin-tea.com`，或裸域名 → `www.` 前缀）确定后，代码中硬编码的旧域名必须全量替换，否则 canonical、og:url、schema、邮箱会指向旧域名。

```powershell
cd {PROJECT_DIR}

# 1. 找出所有硬编码旧域名（含 .txt/.xml 等易遗漏文件）
Get-ChildItem -Recurse -Include *.astro,*.ts,*.tsx,*.mjs,*.json,*.md,*.txt,*.xml -Path src,public |
  Where-Object { $_.FullName -notmatch 'node_modules' } |
  ForEach-Object { if (Select-String -Path $_.FullName -Pattern 'OLD\.com' -Quiet) { Write-Host $_.FullName } }

# 2. 批量替换
$files = Get-ChildItem -Recurse -Include *.astro,*.ts,*.tsx,*.mjs,*.json,*.md |
  Where-Object { $_.FullName -notmatch 'node_modules|dist|\.git' }
foreach ($f in $files) {
  $c = Get-Content $f.FullName -Raw
  if ($c -match 'OLD\.com') { ($c -replace 'OLD\.com', 'NEW.com') | Set-Content $f.FullName -NoNewline }
}

# 3. 重新构建 + 推送（复用 Step 3/4）
```

> 注意：
> - `-Include` 通配符**不会匹配 `[slug].astro` 这类含方括号文件名**，需用 `Get-Content -LiteralPath` 逐个处理。
> - `robots.txt` / `llms.txt` / `opensearch.xml` 的 `Sitemap` 行也要一并替换。

### Step 10: 通知用户完成后续操作

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
| GitHub 操作超时 | github.com:443 被墙 | 用系统代理前缀 `git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897`（ghfast.top 已失效） |
| push 报 `refspec main does not match` | 实际分支是 `master` | 先 `git branch -a` 确认，不要假设 |
| push 报 `workflow scope` 错误 | Token 无 workflow 权限 + 仓库有 `.github/workflows/` | 删除 workflow 文件或换 token |
| API 创建项目成功但无部署 | webhook 未触发 | 执行 `git commit --allow-empty` + push 触发首次构建 |
| API 创建项目报项目已存在 | 项目之前创建过 | 改为查询项目状态，直接 push 触发重新部署 |
| sitemap 返回 522 | 部署后缓存未就绪 | 等 10 秒重试，正常现象 |
| 绑定域名报 `CNAME not set` / `Authentication error` | Token 缺 Zone DNS:Edit 权限 | Token 加 `Zone → DNS → Edit`，Zone Resources 选「所有域名」 |
| 重定向规则创建报权限错误 | Token 缺 Dynamic URL Redirects 权限 | Token 加 `Zone → Dynamic URL Redirects → Edit` |
| 绑定域名报 `already added`（8000018） | 域名已绑定过 | 跳过，无需处理 |
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
