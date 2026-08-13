---
name: gsc-daily-report
description: 自动运行 GSC 站点效果统计脚本，拉取所有已授权 Google Search Console 站点的搜索数据（点击、展示、CTR、排名、热门查询词、热门页面、设备、国家分布），生成多工作表 Excel 报告。当用户说"获取站点GSC"、"拉取GSC数据"、"GSC报告"、"站点效果统计"、"获取GSC"、"查GSC"等时使用。
---

# GSC 站点效果统计

## 触发条件

用户要求获取 GSC / 搜索控制台数据、站点效果统计、SEO 表现数据时，直接运行本地脚本拉取，无需让用户手动操作。

## 脚本位置

脚本 `gsc_daily.py` 位于本 skill 目录的 `scripts/` 子目录。运行时先进入本 SKILL.md 所在目录（skill 根目录），再用相对路径执行。

## 运行方式

> Windows PowerShell 下先设置 UTF-8 编码（否则中文/emoji 乱码），再执行脚本：

### 1. 测试连接（拉站点列表，约 10 秒）

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python scripts/gsc_daily.py --test
```

### 2. 完整拉取（生成 Excel 报告，约 3-4 分钟）

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python scripts/gsc_daily.py
```

> 完整运行耗时随站点数线性增长（每站约 5 次 API 调用，含重试约 10 秒/站），用后台方式运行并轮询输出，或设置较长 timeout。

## 输出

报告输出目录由脚本内 `DATA_DIR` 配置（环境变量 `GSC_DATA_DIR` 可覆盖），默认为本 skill 目录下的 `gsc_reports/`，文件名 `gsc_report_YYYYMMDD_HHMM.xlsx`，包含 4 个工作表：

| 工作表 | 内容 |
|--------|------|
| 近1天 | 昨日汇总（按点击降序 + 合计行） |
| 近7天 | 近一周汇总 |
| 近30天 | 近一月汇总 |
| 明细-近7天 | 查询词 / 页面 / 设备 / 国家 |

## 运行后如何汇报

脚本控制台已打印完整汇总。向用户汇报：

1. 站点总数、近 7 天总点击 / 总展示
2. 点击排名前 5 的站点（点击 / 展示 / CTR / 均位）
3. 报告文件路径（Markdown 链接）
4. 如有 ERROR 状态的站点，提示重跑可补上（脚本内置重试机制）

## 站点数量是动态的（重要）

脚本通过 GSC API 的 `sites.list()` **自动发现所有已授权站点**，没有硬编码站点清单。用户新增站点时：

1. 只需在 GSC 后台把服务账号邮箱 `jiusongvip@jiusong-505309.iam.gserviceaccount.com` 加到新站点的「用户和权限」里
2. 下次运行脚本自动纳入，**无需修改脚本或 skill**
3. 汇报时以脚本实际输出的站点总数为准，不要假设固定数量

## 注意事项

- 依赖 Python 3.12+，包：httpx、google-auth、openpyxl
- 代理默认 `127.0.0.1:7897`；换电脑需设环境变量 `HTTPS_PROXY` 或改脚本内 `PROXY`
- 凭证 `service_account.json` 在本 skill 目录下，已在 `.gitignore` 中，勿提交
- 换电脑后脚本随 git 克隆自动就位，只需重下凭证到本 skill 目录或设 `GSC_DATA_DIR` 指向新位置
