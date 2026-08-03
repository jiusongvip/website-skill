---
name: api-image-generator
description: >
  API Image Generator — 调用速创API（api.wuyinkeji.com）的 GPT-Image-2
  图片生成接口批量生图。覆盖完整流程：提交生图任务（异步）、轮询结果查询接口、
  下载成图并转换为 WebP（质量80%）。When a site needs custom AI-generated
  images (hero / article / product / OG) instead of stock photos, use this skill.
  Trigger words: AI生图、GPT-Image-2、生成图片、生图、generate image.
---

# API Image Generator（GPT-Image-2 生图）

## Why this skill exists

建站过程中经常需要主题配图。此前通过 browser-use 在 Unsplash 等图库搜索，
存在版权、匹配度、风格不一致等问题。本 skill 使用速创API 提供的
**GPT-Image-2**（OpenAI 新一代图像生成模型）直接按提示词生图，
风格统一、无版权风险、可精确控制构图。

费用：0.1 元/张（10 点/张）。

> 生图脚本见 [`scripts/gen_batch.py`](./scripts/gen_batch.py)（单图与批量均支持）。

---

## 配置文件（Config）

所有可变配置统一放在 [`config.json`](./config.json)，脚本与调用方一律从此文件读取，
避免在多处硬编码 Key 与接口地址。核心字段：

```json
{
  "api_key": "ToamgJxkycib1LO7YoyZ5yusAQ",
  "endpoints": {
    "generate": "https://api.wuyinkeji.com/api/async/image_gpt",
    "detail": "https://api.wuyinkeji.com/api/async/detail"
  },
  "prompt": {
    "base": "A photorealistic editorial photograph of {subject}, ...",
    "style": "vibrant natural colors, clean background",
    "negative": "no text, no watermark, no logo"
  },
  "size": { "default": "1:1", "by_use": { "hero": "16:9", "card": "1:1" } },
  "poll": { "interval_seconds": 5, "max_attempts": 120 },
  "image_processing": { "format": "webp", "quality": 80 }
}
```

**prompt / size 是核心可变配置**：批量生图时只需替换 `{subject}` 主题词，
风格基底（style/lighting/composition/negative）与尺寸映射统一从配置读取，
保证成图风格一致。完整字段见 config.json（含计费、尺寸选项、状态码映射等）。

- **Key 轮换**：只需修改 `config.json` 的 `api_key` 字段
- **安全升级**：支持环境变量 `WUYIN_API_KEY` 覆盖配置文件（脚本优先读环境变量）

## API 凭证与鉴权

- 平台：速创API（https://api.wuyinkeji.com）
- 文档：生图接口 doc/53，结果查询 doc/47
- 鉴权方式（文档支持两种，均附上双保险）：
  - 请求头 `Authorization: {api_key}`
  - URL 查询参数 `?key={api_key}`

---

## 接口一：提交生图任务（异步）

| 项 | 值 |
|----|----|
| URL | `https://api.wuyinkeji.com/api/async/image_gpt` |
| Method | POST |
| Content-Type | application/json |

### 请求参数

| 名称 | 必填 | 类型 | 说明 |
|------|------|------|------|
| prompt | 是 | string | 提示词（英文效果最佳，见"提示词写作指南"） |
| size | 否 | string | 图像比例，默认 `auto`。可选：`auto`、`1:1`、`3:2`、`2:3`、`16:9`、`9:16`、`4:3`、`3:4`、`21:9`、`9:21`、`1:3`、`3:1`、`2:1`、`1:2` |
| urls | 否 | array | 参考图片 URL 列表，支持多张（图生图 / 风格迁移） |

### 返回结构

```json
{
  "code": 200,
  "msg": "成功",
  "data": { "id": "image_4d39239e-776a-4cbd-a8eb-e2d9b4816829", "count": 10 },
  "exec_time": 0.29,
  "ip": "119.6.176.239"
}
```

- `data.id`：生图任务 ID（后续查询结果用）
- `data.count`：本次扣费点数

---

## 接口二：查询生成结果

| 项 | 值 |
|----|----|
| URL | `https://api.wuyinkeji.com/api/async/detail` |
| Method | GET |
| 参数 | `id`（必填，生图任务 ID） |

### 返回结构

```json
{
  "code": 200,
  "msg": "成功",
  "data": {
    "status": 2,
    "message": ""
  },
  "exec_time": 0.12,
  "user_ip": "119.6.176.239"
}
```

### 状态码说明

| status | 含义 | 处理 |
|--------|------|------|
| 0 | 初始化 | 继续轮询 |
| 1 | 进行中 | 继续轮询 |
| 2 | 成功 | `data` 中包含成图 URL（通常为 `data.url` / `data.image` 等字段），下载图片 |
| 3 | 失败 | 读取 `data.message` 排查失败原因 |

---

## 工作流程 Pipeline

### Step 1: 明确需求，构建提示词（读取 config.json）

- **prompt 模板**：使用 `config.json` 中 `prompt.base` 模板（含 `{subject}` 占位符），
  调用时只需替换主题词，风格 / 光线 / 负面词由配置统一控制，保证批量生图风格一致
- **size 选择**：按用途从 `config.json` 的 `size.by_use` 映射取值：
  - `hero` / `og` → `16:9`
  - `article` → `3:2`
  - `card` / 默认 → `1:1`
  - `portrait` / `poster` → `9:16` / `2:3`
- 需保持与已有图片风格一致时，传入 `urls` 参考图

### Step 2: 提交生图任务

POST 到生图接口，携带 prompt / size / urls，从响应中取 `data.id`。

### Step 3: 轮询查询结果

- 每 5~10 秒查询一次 `https://api.wuyinkeji.com/api/async/detail?id={id}`
- `status == 2`：任务成功，拿到成图 URL
- `status == 3`：任务失败，读 `data.message`
- 最长轮询 10 分钟，超时仍未成功则向用户报告

### Step 4: 下载并处理图片

- 下载成图到项目图片目录（如 `public/`、`src/assets/`）
- 文件名：`kebab-case-descriptive.webp`（小写、连字符、描述性）
- 用 sharp / cwebp 转换为 **WebP、质量 80%**（与站内其他图片规范一致）
- 页面中使用时必须设置 `alt` 描述与 `width`/`height`（防 CLS）

---

## 批量模式（Batch Mode）

站点批量配图（如为多篇文章同时生成 hero 图）时，使用脚本
[`scripts/gen_batch.py`](./scripts/gen_batch.py) 一次完成「批量提交 → 批量轮询 → 批量下载」：

```bash
# 方式一：| 分隔主题
python scripts/gen_batch.py --subjects "a red apple|a blue whale|a green forest"

# 方式二：主题文件（每行一个）
python scripts/gen_batch.py --subjects-file subjects.txt

# 指定尺寸与输出目录，仅下载原图不转 WebP
python scripts/gen_batch.py --subjects "a red apple" --size 16:9 --out ./images --no-webp
```

- 并发参数（提交/轮询线程数、默认输出目录）在 config.json 的 `batch` 段配置
- 批量任务共用同一 prompt 模板，风格天然一致；每张图按主题词 kebab-case 命名
- 所有任务完成后统一统计成功/失败；失败任务打印原因并置退出码 1
- 依赖：`requests`（必须）、`Pillow`（转 WebP，`--no-webp` 时不需要）

---

## 提示词写作指南

1. **英文提示词**效果显著优于中文
2. 结构：主体 + 场景/环境 + 风格 + 光线 + 构图 + 画质关键词
3. 网站配图常用风格词：`photorealistic`、`editorial photography`、
   `soft natural light`、`minimalist composition`、`warm tones`、`high detail, 8k`
4. 避免画面出现多余元素：prompt 中写明 `no text, no watermark, no logo`
5. 需要文字出现在图中（如标题横幅）：GPT-Image-2 支持文字渲染，
   把文字内容明确写入 prompt 并说明字体/位置

示例：

```
A photorealistic editorial photo of a wooden massage table with fresh
eucalyptus leaves and white towels in a bright spa room, soft natural
light, minimalist composition, warm tones, high detail, no text, no watermark
```

---

## 错误处理

| 现象 | 排查 |
|------|------|
| HTTP 401 / 认证失败 | Authorization header 或 key 参数错误 / Key 失效 |
| code != 200 | 按 `msg` 字段处理（余额不足、参数错误等） |
| status == 3 | 读取 `data.message`，调整 prompt 后重试 |
| 轮询超时 | 检查任务是否因余额 / 内容安全被拒，必要时重新提交 |

---

## What NOT to do

- 不要提交任务后不轮询 —— 结果不会自动推送，必须轮询 `detail` 接口
- 不要逐张串行“提交 → 轮询 → 提交下一张”（效率极低）；批量场景一律用 `scripts/gen_batch.py` 并发提交与轮询
- 不要用中文长句 prompt（改用英文）
- 不要把生成图以 PNG/JPEG 大文件直接塞进站点，需转 WebP（质量 80%）
- 不要修改 API Key，除非用户明确要求轮换
- 不要生成涉及品牌商标、真人肖像、敏感内容的图片（合规风险）
