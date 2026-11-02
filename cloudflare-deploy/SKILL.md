---
name: cloudflare-deploy
description: >
  Cloudflare Pages 部署技能。输入一个 GitHub 仓库 URL 即可完成部署，
  覆盖代码拉取、配置自动修复、本地构建、推送、API 创建 Git 连接项目、
  触发部署、验证全流程。支持多 Cloudflare 账号档案（部署前必须询问
  目标账号，凭证见 .env）。覆盖常见坑点：构建命令、API Token 权限、
  GitHub 推送代理、sitemap 验证、合并冲突处理。
  部署通道按账号自动分叉：旧账号走原生 Git 集成；新账号因 GitHub App
  已被旧账号认领（报 8000011）改走 Direct Upload + GitHub Actions。
---

# Cloudflare Pages 部署技能

## 核心配置（多账号档案）

凭证按「账号档案 profile」存放，全部在同目录 `.env`（已加入 .gitignore，严禁提交）。

| profile | Cloudflare 账号 | 变量前缀 | 部署通道 |
|---------|----------------|---------|---------|
| `jiusongvip` | jiusongvip@gmail.com（旧） | `CF_JIUSONGVIP_*` | `git`（原生 Git 集成） |
| `jiusongok` | jiusongok@hotmail.com（新） | `CF_JIUSONGOK_*` | `direct`（Direct Upload + Actions） |

新增账号 = 在 `.env` 追加三行（同时补进 `CF_PROFILES`）：

```bash
CF_PROFILE_{PROFILE}_LABEL=<账号邮箱>
CF_{PROFILE}_API_TOKEN=cfat_xxx
CF_{PROFILE}_ACCOUNT_ID=xxxxxxxx
CF_PROFILE_{PROFILE}_CHANNEL=git        # git | direct，决定 Step 5 走哪条通道
```

> `CHANNEL` 缺省时的回退规则：profile 名（大写）为 `JIUSONGOK` → `direct`，其余 → `git`。
> **键名必须全大写**：加载脚本用 `$PROFILE.ToUpper()` 拼接变量名，写成 `CF_jiusongok_API_TOKEN` 会静默读不到（表现为 token 为空、403）。

**Token 必需权限（4 项，缺一不可）：**

| 权限 | 级别 | 用途 |
|------|------|------|
| Cloudflare Pages Read + Edit | Account | 建项目 / 触发部署 / 查日志 / 绑域名 |
| DNS Read + Edit | Zone | 自动创建 CNAME |
| Zone Read | Zone | `GET /zones?name=` 查 zone id |
| Dynamic URL Redirects Read + Edit | Zone | 裸域名 301 → www |

> 建 token 时 **Account Resources 与 Zone Resources 都必须设值**，否则对应权限空转；`Client IP Address Filtering` 必须留空（走代理会全局 403）。

### 加载账号档案（每次会话先执行一次）

```powershell
$ENV_FILE = "d:\workspaces\website\website-skill\cloudflare-deploy\.env"
$PROFILE  = "jiusongok"   # 用户选定的 profile（见 Step 0a）

Get-Content $ENV_FILE | ForEach-Object {
  if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.+)$') { Set-Item "env:$($matches[1])" $matches[2].Trim() }
}
$p = $PROFILE.ToUpper()
$env:CLOUDFLARE_API_TOKEN  = [Environment]::GetEnvironmentVariable("CF_${p}_API_TOKEN")
$env:CLOUDFLARE_ACCOUNT_ID = [Environment]::GetEnvironmentVariable("CF_${p}_ACCOUNT_ID")

"账号：$([Environment]::GetEnvironmentVariable("CF_PROFILE_${p}_LABEL")) / $env:CLOUDFLARE_ACCOUNT_ID"

# 只读校验，期望 True；False 或 403 = token 与 Account ID 跨账号混用
(Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts/$env:CLOUDFLARE_ACCOUNT_ID/pages/projects?per_page=1" -Headers @{Authorization="Bearer $env:CLOUDFLARE_API_TOKEN"}).success

# 通道判定：git = 原生 Git 集成；direct = Direct Upload + GitHub Actions
$env:CF_CHANNEL = [Environment]::GetEnvironmentVariable("CF_PROFILE_${p}_CHANNEL")
if (-not $env:CF_CHANNEL) { $env:CF_CHANNEL = if ($p -eq 'JIUSONGOK') { 'direct' } else { 'git' } }
"通道：$env:CF_CHANNEL"
```

### 两条部署通道（决定 Step 5 走哪条）

| 通道 | 适用账号 | 建项目方式 | push 后谁构建 |
|------|---------|-----------|--------------|
| `git` | `jiusongvip`（GitHub App 被它认领） | `POST /pages/projects` **带 `source`** | Cloudflare（webhook） |
| `direct` | `jiusongok`（该账号的 GitHub App 属于 `jiusongok-bot`，`jiusongvip` 仓库报 8000011） | `POST /pages/projects` **不带 `source`** | GitHub Actions（`wrangler pages deploy`） |

> **不要试图给 `direct` 账号补 GitHub App 授权** —— 一份 installation 只能被一个 Cloudflare 账号认领。实测 Configure 里点 Save、无痕窗口重授权、`+ Add account`、切 `All repositories` 全都绕不过 `8000011`，详见附录第 2 条。
>
> 实测补充：`jiusongok` 账号已有自己的 installation，归属 GitHub 账号 **`jiusongok-bot`**（`solar-fan-hat`、`astro-facialcupping` 就是它名下的 git 集成项目）。所以若仓库能建在 `jiusongok-bot` 名下，可直接走 `git` 通道；只要仓库在 `jiusongvip` 名下，就只能走 `direct`。

---

## 一键部署流程（输入：仓库 URL + 目标 Cloudflare 账号）

**输入示例：** `https://github.com/{USER}/{REPO}` 或本地项目目录

**执行前确认：**
- 项目名 = 仓库名（如 `best-of-chengdu`）
- 本地工作区根目录：`d:\workspaces\website\{REPO}`
- **部署到哪个 Cloudflare 账号**（必须由用户选定，见下）

### Step 0: 选择账号 + 获取代码

#### 0a. 选择 Cloudflare 账号（必做，禁止默认）

**禁止使用任何“默认”账号，也禁止猜测。** 每次部署前向用户提问，选项从 `.env` 的 `CF_PROFILES` 实际读取。

提问必须带**邮箱**（邮箱才是用户判断部署位置的真实标识，缩写仅作内部键名）：

```
这次部署到哪个 Cloudflare 账号？
1) jiusongvip — jiusongvip@gmail.com（Account …592be，git 通道：原生 Git 集成）
2) jiusongok  — jiusongok@hotmail.com（Account …d9c9，direct 通道：Direct Upload + Actions）
```

用户选定后执行「核心配置 → 加载账号档案」，再确认只读校验返回 `True`。

> 不同账号的 token / account_id **不可混用**，混用表现为 `success=false`、403 或 `Authentication error`。
> 若该账号是首次部署，先完成「附录：新 Cloudflare 账号首次接入」，否则 Step 5 的 API 一定失败。
> 后续每个 API 调用回显时都带上账号标识（如 `jiusongok`），避免串号。

#### 0b. 获取代码

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

### Step 5: 创建项目（按 `CF_CHANNEL` 分叉）

| 通道 | 走哪节 | 前提 |
|------|--------|------|
| `git` | **5A** | 该 CF 账号已持有 GitHub App installation |
| `direct` | **5B** | 不需要 GitHub App，只需 Pages:Edit 权限 |

#### 5A. Git 集成项目（`git` 通道）

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

> **核心优势：** 一次 API 调用同时完成项目创建 + Git 连接 + 构建配置，无需手动到 Dashboard。前提是 **Cloudflare Pages GitHub App 已被当前账号认领**。
> 若报 `8000011`（installation 已被别的账号占用）或 repository / installation 相关错误：**不要重试、不要卸载重装**，直接改走 5B。

**项目已存在时：** API 会报错（如 409/1101）。此时应改为**查询项目状态**（见 API 速查），确认 Git 连接和构建配置无误后直接进入 Step 6 触发重新部署。

#### 5B. Direct Upload 项目 + GitHub Actions（`direct` 通道）

> 适用：GitHub App 已被别的 CF 账号认领，用 5A 必定报 `8000011`。此通道完全不碰 GitHub App。

**第 1 步：建 Direct Upload 项目（请求体不带 `source`）**

```powershell
$body = @{ name = "{PROJECT_NAME}"; production_branch = "{BRANCH}" } | ConvertTo-Json

$r = Invoke-RestMethod `
  -Uri "https://api.cloudflare.com/client/v4/accounts/$env:CLOUDFLARE_ACCOUNT_ID/pages/projects" `
  -Method POST `
  -Headers @{Authorization="Bearer $env:CLOUDFLARE_API_TOKEN"} `
  -ContentType "application/json" `
  -Body $body

"$($r.result.name) | $($r.result.subdomain) | source=[$($r.result.source.type)]"
# source 为空 = Direct Upload；若显示 github 说明误传了 source
```

**第 2 步：仓库里写入 `.github/workflows/deploy.yml`**

```yaml
name: Deploy to Cloudflare Pages

on:
  push:
    branches: [{BRANCH}]
  workflow_dispatch:

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm run build
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          command: pages deploy dist --project-name={PROJECT_NAME} --branch={BRANCH}
```

> 纯静态项目（无构建步骤）删掉 `setup-node` / `npm` 三行，并把 `pages deploy dist` 改为 `pages deploy .`。
> 仓库里已有 workflow 时只改 `--project-name`，不要重复建文件。

**第 3 步：写入两条 Secrets（二选一）**

| 方式 | 操作 |
|------|------|
| **推荐：让用户手动加** | 仓库 `Settings → Secrets and variables → Actions → New repository secret`：`CF_API_TOKEN`（`CF_{PROFILE}_API_TOKEN`）、`CF_ACCOUNT_ID`（`CF_{PROFILE}_ACCOUNT_ID`） |
| 有 `Secrets: Read and write` 的 fine-grained PAT | 拉 public-key → libsodium sealed box 加密 → `PUT /repos/{USER}/{REPO}/actions/secrets/{NAME}`；明文只走环境变量，不落盘、不回显 |

> 写入后 `GET /repos/{USER}/{REPO}/actions/secrets` 应返回 `total_count=2`。
> 此处的 GitHub token 用完必须提醒用户 revoke。

### Step 6: 触发首次部署

API 创建项目后，需要一次 `git push` 启动首次构建。两条通道都靠 push，但**干活的一方不同**：

| 通道 | 谁构建 | 失败时第一嫌疑 |
|------|--------|----------------|
| `git` | Cloudflare 拉代码 + 构建 | webhook 未触发 / build command 写错 |
| `direct` | GitHub Actions 构建 → `wrangler pages deploy` | 仓库缺 Secrets / Actions 构建失败 |

```bash
cd {PROJECT_DIR}
git commit --allow-empty -m "chore: trigger deployment"
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin {BRANCH}
```

部署完成后等待约 30 秒（大型项目更久），访问 `https://{PROJECT_NAME}.pages.dev`。

> **`direct` 通道兜底**：Actions 还没配好时，先本地构建 + 直传把站跑起来（不依赖 Actions）：
> ```bash
> npx --yes wrangler@latest pages deploy dist --project-name={PROJECT_NAME} --branch={BRANCH}
> ```
> 需要 `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` 已由「加载账号档案」注入。

### Step 7: 验证部署

```powershell
# 检查部署状态（预期 latest_stage.status = success）
# 若 Step 5 走的是 5B，先补：$env:AID = $env:CLOUDFLARE_ACCOUNT_ID; $env:TOKEN = $env:CLOUDFLARE_API_TOKEN
$resp = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts/$env:AID/pages/projects/{PROJECT_NAME}/deployments?per_page=1" -Method GET -Headers @{Authorization="Bearer $env:TOKEN"}
$resp.result[0].latest_stage | Select-Object name,status

# 验证 sitemap（若返回 522 属缓存延迟，等 10 秒重试即可）
curl -sI https://{PROJECT_NAME}.pages.dev/sitemap-index.xml | Select-String "HTTP"
```

> **`direct` 通道额外核对（两条都成立才算真生效，不能只看页面能打开）：**
> 1. `GET /repos/{USER}/{REPO}/actions/runs?per_page=1` → `conclusion=success`；
> 2. `deployments?per_page=1` 最新一条 `created_on` 晚于本次 push，且 `environment=production`。
> 若页面能打开但两条不成立，说明看到的是旧部署（缓存/别名未切换）。

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

> 域名所在的 zone 必须属于**当前账号**，否则绑定直接失败（新账号常见问题，见附录第 3 条）。

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

- **Google Analytics**：提醒用户提供 GA 代码（gtag.js，ID 格式 `G-XXXXXXXXXX`），添加到布局文件（如 `Layout.astro`）的 `<head>` 中：

  ```html
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
  <script is:inline>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  </script>
  ```

  > 注意：
  > - 内联 gtag 脚本需加 `is:inline`，避免 Astro 打包处理
  > - `embed`/iframe 类 noindex 页面通常不加 GA（避免重复统计嵌入流量）
  > - 添加后需重新构建 + 推送（复用 Step 3/4），并验证线上已含 GA ID

- **Google Search Console**：提交 `https://example.com/sitemap-index.xml`，首次"无法抓取"正常，等 5-10 分钟

---

## 附录：新 Cloudflare 账号首次接入

新账号（如 `jiusongok`）第一次部署前按下表准备；**第 2 项仅 `git` 通道需要**，`direct` 通道直接跳过。

1. **建 Token** —— 4 项权限 + `Account Resources` + `Zone Resources` 都设值（见「核心配置」）。
2. **授权 GitHub App —— 仅 `git` 通道需要**
   - `git` 通道（旧账号）：GitHub App 已授权。修授权只改 **Configure → Repository access**，**绝不要卸载重装**（重装会产生新 installation，旧账号已绑定的项目全部失联）。
   - `direct` 通道（新账号）：**不需要也无法授权**。一份 installation 在同一时间只能被一个 Cloudflare 账号认领，新账号引用会报 `8000011 There is an internal issue with your Cloudflare Pages Git installation`。
   - 已实测无效的 4 种绕法：Configure 里不改直接点 Save、无痕窗口先登出 GitHub 再授权、`+ Add account`、切到 `All repositories`（该项只控制仓库范围，不改变归属）。
   - 硬结论：既要在第二个 CF 账号部署、又要保留原生 Git 集成 → 只能换/加一个 GitHub 账号；否则一律走 `direct` 通道。
3. **确认 zone** —— `GET /zones` 若返回 0 条，说明该账号还没有域名：只能先跑 `xxx.pages.dev`，自定义域名必须先把域名迁入该账号。
4. **回报账号** —— 部署小结里写明 profile + Account ID 后 4 位。

> 过渡期两账号并行：push 只触发「已绑定该仓库」的项目，不同仓库互不影响；若两个账号绑了同一个仓库，才会出现双份构建。

---

## 常见坑点速查

| 问题 | 原因 | 解决 |
|------|------|------|
| push 报 `non-fast-forward` | 远程有新提交，本地没拉 | `git pull origin {BRANCH} --rebase` 后再 push |
| pull 产生 `both modified` 冲突 | 双方都改了同一文件（常见 astro.config.mjs） | 保留更完整版本 → `git add` → `git commit --no-edit` → 重新构建 |
| `astro: not found` | build 脚本用裸 `astro build` | 改为 `npx astro build` |
| 缺少 `sitemap-index.xml` | 项目没装 @astrojs/sitemap | `npm install @astrojs/sitemap` + 添加到 integrations |
| API 返回 8000006 | Token 权限不足 | Token 需 `Pages:Edit` 权限 |
| 只读校验 `success=false` / 403 | token 与 Account ID 来自不同账号（跨 profile 混用） | 确认二者取自同一 profile，重新加载账号档案 |
| `GET /zones` 返回 0 条 | 该账号还没添加任何域名 | 属正常，Zone 三项权限暂时空转，先跑 `pages.dev` |
| 绑域名报 zone 不存在 / 域名不在列表 | 域名 zone 在别的 Cloudflare 账号下 | 先把域名迁入该账号，否则无法绑自定义域名 |
| `CLOUDFLARE_API_TOKEN` 不生效 | PowerShell 环境变量语法 | 用 `$env:CLOUDFLARE_API_TOKEN = "..."` |
| GitHub 操作超时 | github.com:443 被墙 | 用系统代理前缀 `git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897`（ghfast.top 已失效） |
| push 报 `refspec main does not match` | 实际分支是 `master` | 先 `git branch -a` 确认，不要假设 |
| push 报 `workflow scope` 错误 | git 凭据无 workflow 权限 + 仓库有 `.github/workflows/` | GitHub 网页端新建该文件，或换带 workflow 权限的凭据 |
| API 建项目报 `8000011` | 该 CF 账号未持有 GitHub App installation（一份安装只能被一个账号认领） | 改走 `direct` 通道建 Direct Upload 项目，**不要卸载重装** |
| 项目列表显示「无 Git 连接」、push 后不构建 | Direct Upload 项目与仓库无任何关联 | 必须配 Actions workflow；否则只能手动 `wrangler pages deploy` |
| Direct Upload 项目想改回 Git 集成 | 官方限制：项目类型创建后不可切换 | 删除项目，重建为 Git 集成项目 |
| Actions 报 `Input required and not supplied: apiToken` | 仓库缺 `CF_API_TOKEN` / `CF_ACCOUNT_ID` | 补 Secret 后 Re-run |
| Actions 报 403 / `Authentication error` | Secret 里的 token 与 Account ID 不是同一账号 | 重新写入同一 profile 的两个值 |
| 写 Secret 报 403 `Resource not accessible by personal access token` | fine-grained PAT 缺 `Repository permissions → Secrets: Read and write` | token 设置里补该项（注意：`Secret scanning push protection bypass requests` 不是它） |
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
| `{PROFILE}` | 用户选定（Step 0a） | `jiusongok` |
| `{CHANNEL}` | `.env` 的 `CF_PROFILE_{PROFILE}_CHANNEL` | `git` / `direct` |
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

# 创建 Direct Upload 项目（direct 通道：请求体**不带 source**）
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$AID/pages/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"PROJECT_NAME","production_branch":"main"}'

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
