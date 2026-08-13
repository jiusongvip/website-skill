#!/usr/bin/env python3
"""
GSC 每日站点效果统计脚本
- 自动发现所有已授权的 GSC 站点
- 拉取 Search Analytics：按日期汇总 + 热门查询词 + 热门页面 + 设备/国家分布
- 输出单个 Excel 文件（多工作表：近1天 / 近7天 / 近30天 + 明细）

用法:
    python gsc_daily.py            # 完整运行，输出 xlsx
    python gsc_daily.py --test     # 仅测试连接 + 拉站点列表
"""

import os
import sys
import time
from datetime import datetime, timedelta

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── 路径配置 ────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, "service_account.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "gsc_reports")

# ── 代理配置 ────────────────────────────────────────────
PROXY = os.environ.get("HTTPS_PROXY", os.environ.get("HTTP_PROXY", "http://127.0.0.1:7897"))

# ── GSC API ─────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"

# 三个时间窗口
WINDOWS = [("近1天", 1), ("近7天", 7), ("近30天", 30)]

# 重试配置
MAX_RETRIES = 4          # 最多重试次数（含首次）
RETRY_BACKOFF = [1, 2, 4]  # 每次重试前的等待秒数（指数退避）


class GSCClient:
    """使用 httpx + Service Account 访问 GSC API"""

    def __init__(self):
        self._creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

    def _get_client(self) -> httpx.Client:
        self._creds.refresh(Request())
        return httpx.Client(
            proxy=PROXY,
            headers={"Authorization": f"Bearer {self._creds.token}"},
            timeout=30.0,
        )

    def _query(self, site_url: str, start: str, end: str,
               dimensions: list, row_limit: int = 1000) -> list:
        """带重试的查询"""
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                client = self._get_client()
                resp = client.post(
                    f"{GSC_API_BASE}/sites/{site_url}/searchAnalytics/query",
                    json={
                        "startDate": start,
                        "endDate": end,
                        "dimensions": dimensions,
                        "rowLimit": row_limit,
                        "aggregationType": "byProperty" if dimensions == ["date"] else "auto",
                    },
                )
                resp.raise_for_status()
                return resp.json().get("rows", [])
            except Exception as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    time.sleep(wait)
        raise last_err

    def list_sites(self) -> list[dict]:
        """带重试的站点列表"""
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                client = self._get_client()
                resp = client.get(f"{GSC_API_BASE}/sites")
                resp.raise_for_status()
                return [
                    {"url": e.get("siteUrl", ""), "permission": e.get("permissionLevel", "unknown")}
                    for e in resp.json().get("siteEntry", [])
                ]
            except Exception as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    time.sleep(wait)
        raise last_err

    def daily_rows(self, site_url: str, days: int = 30) -> list:
        """拉取近 N 天按日期维度的原始行（一次调用覆盖所有时间窗口）"""
        end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")
        return self._query(site_url, start, end, ["date"])

    def top_queries(self, site_url: str, start: str, end: str, n: int = 10) -> list:
        return self._query(site_url, start, end, ["query"], n)

    def top_pages(self, site_url: str, start: str, end: str, n: int = 10) -> list:
        return self._query(site_url, start, end, ["page"], n)

    def device_breakdown(self, site_url: str, start: str, end: str) -> list:
        return self._query(site_url, start, end, ["device"])

    def country_breakdown(self, site_url: str, start: str, end: str) -> list:
        return self._query(site_url, start, end, ["country"])


# ── 计算工具 ─────────────────────────────────────────────

def short_name(url: str) -> str:
    return url.replace("sc-domain:", "").replace("https://", "").rstrip("/")


def calc_metrics(rows: list) -> dict:
    clicks = sum(r.get("clicks", 0) for r in rows)
    imps = sum(r.get("impressions", 0) for r in rows)
    ctr = (clicks / imps * 100) if imps > 0 else 0
    pos = (sum(r.get("position", 0) * r.get("impressions", 0) for r in rows) / imps) if imps > 0 else 0
    return {
        "clicks": clicks, "impressions": imps,
        "ctr_pct": round(ctr, 2), "avg_position": round(pos, 1),
        "daily_rows": len(rows),
    }


def filter_rows_by_days(rows: list, days: int) -> list:
    """从按日期维度的 rows 中，筛选最近 days 天的数据"""
    cutoff = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")
    return [r for r in rows if r.get("keys", [""])[0] >= cutoff]


# ── Excel 输出 ───────────────────────────────────────────

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)


def write_summary_sheet(wb, sheet_name: str, stats: list, days: int):
    """写一个时间窗口的汇总 sheet"""
    ws = wb.create_sheet(sheet_name)
    end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days + 3)).strftime("%Y-%m-%d")

    # 标题
    ws.cell(row=1, column=1, value=f"GSC 站点效果汇总 · {sheet_name}（{start} → {end}）").font = TITLE_FONT
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)

    # 表头
    headers = ["站点", "点击", "展示", "CTR%", "平均排名", "数据天数", "状态"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=3, column=i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center")

    # 数据（按点击降序）
    sorted_stats = sorted(stats, key=lambda x: x["clicks"], reverse=True)
    for r, s in enumerate(sorted_stats, 4):
        ws.cell(row=r, column=1, value=short_name(s["site_url"]))
        ws.cell(row=r, column=2, value=s["clicks"])
        ws.cell(row=r, column=3, value=s["impressions"])
        ws.cell(row=r, column=4, value=s["ctr_pct"])
        ws.cell(row=r, column=5, value=s["avg_position"])
        ws.cell(row=r, column=6, value=s.get("daily_rows", 0))
        ws.cell(row=r, column=7, value=s.get("status", "OK"))

    # 汇总行
    total_row = len(sorted_stats) + 4
    total_clicks = sum(s["clicks"] for s in sorted_stats)
    total_imps = sum(s["impressions"] for s in sorted_stats)
    ws.cell(row=total_row, column=1, value="合计").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=total_clicks).font = Font(bold=True)
    ws.cell(row=total_row, column=3, value=total_imps).font = Font(bold=True)

    # 列宽
    ws.column_dimensions["A"].width = 42
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 12

    # 冻结首行
    ws.freeze_panes = "A4"


def write_detail_sheet(wb, sheet_name: str, stats: list):
    """写明细 sheet（查询词 / 页面 / 设备 / 国家）"""
    ws = wb.create_sheet(sheet_name)
    headers = ["站点", "类型", "标签", "点击", "展示", "CTR%", "平均排名"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center")

    row = 2
    for s in stats:
        site = short_name(s["site_url"])
        # 查询词
        for q in s.get("top_queries", []):
            c = q.get("clicks", 0)
            i = q.get("impressions", 0)
            ws.cell(row=row, column=1, value=site)
            ws.cell(row=row, column=2, value="查询词")
            ws.cell(row=row, column=3, value=q.get("keys", [""])[0])
            ws.cell(row=row, column=4, value=c)
            ws.cell(row=row, column=5, value=i)
            ws.cell(row=row, column=6, value=round(c / i * 100, 1) if i > 0 else 0)
            ws.cell(row=row, column=7, value=round(q.get("position", 0), 1))
            row += 1
        # 页面
        for p in s.get("top_pages", []):
            c = p.get("clicks", 0)
            i = p.get("impressions", 0)
            ws.cell(row=row, column=1, value=site)
            ws.cell(row=row, column=2, value="页面")
            ws.cell(row=row, column=3, value=p.get("keys", [""])[0])
            ws.cell(row=row, column=4, value=c)
            ws.cell(row=row, column=5, value=i)
            ws.cell(row=row, column=6, value=round(c / i * 100, 1) if i > 0 else 0)
            ws.cell(row=row, column=7, value=round(p.get("position", 0), 1))
            row += 1
        # 设备
        for d in s.get("devices", []):
            c = d.get("clicks", 0)
            i = d.get("impressions", 0)
            ws.cell(row=row, column=1, value=site)
            ws.cell(row=row, column=2, value="设备")
            ws.cell(row=row, column=3, value=d.get("keys", [""])[0])
            ws.cell(row=row, column=4, value=c)
            ws.cell(row=row, column=5, value=i)
            ws.cell(row=row, column=6, value=round(c / i * 100, 1) if i > 0 else 0)
            ws.cell(row=row, column=7, value=round(d.get("position", 0), 1))
            row += 1
        # 国家
        for co in s.get("countries", []):
            c = co.get("clicks", 0)
            i = co.get("impressions", 0)
            ws.cell(row=row, column=1, value=site)
            ws.cell(row=row, column=2, value="国家")
            ws.cell(row=row, column=3, value=co.get("keys", [""])[0])
            ws.cell(row=row, column=4, value=c)
            ws.cell(row=row, column=5, value=i)
            ws.cell(row=row, column=6, value=round(c / i * 100, 1) if i > 0 else 0)
            ws.cell(row=row, column=7, value=round(co.get("position", 0), 1))
            row += 1

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 60
    for col in "DEFG":
        ws.column_dimensions[col].width = 12
    ws.freeze_panes = "A2"


# ── 主流程 ──────────────────────────────────────────────

def main():
    # 连接
    print("=" * 70)
    print(f"GSC 站点效果统计 | 运行: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🔗 代理: {PROXY}")
    print("=" * 70)

    gsc = GSCClient()

    print("\n📋 拉取站点列表 ...")
    try:
        sites = gsc.list_sites()
    except Exception as e:
        print(f"❌ 失败: {e}")
        return
    if not sites:
        print("⚠️ 没有站点！")
        return
    print(f"✅ 发现 {len(sites)} 个站点\n")

    if "--test" in sys.argv:
        for i, s in enumerate(sites):
            print(f"  [{i+1}] {s['url']}")
        print("\n✅ 连接测试通过！")
        return

    # 逐站拉取 30 天按日期数据（一次调用覆盖三个窗口）
    stats = []
    for i, site_ in enumerate(sites):
        url = site_["url"]
        print(f"[{i+1}/{len(sites)}] {short_name(url):<48}", end=" ", flush=True)
        try:
            # 30 天按日期数据
            daily = gsc.daily_rows(url, days=30)
            m30 = calc_metrics(daily)
            m7 = calc_metrics(filter_rows_by_days(daily, 7))
            m1 = calc_metrics(filter_rows_by_days(daily, 1))

            # 明细（7 天窗口）
            end7 = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            start7 = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

            result = {
                "site_url": url,
                "m1": m1, "m7": m7, "m30": m30,
                "clicks": m7["clicks"],            # 排序用 7 天点击
                "impressions": m7["impressions"],
                "ctr_pct": m7["ctr_pct"],
                "avg_position": m7["avg_position"],
                "daily_rows": m7["daily_rows"],
                "status": "OK",
                "top_queries": gsc.top_queries(url, start7, end7),
                "top_pages": gsc.top_pages(url, start7, end7),
                "devices": gsc.device_breakdown(url, start7, end7),
                "countries": gsc.country_breakdown(url, start7, end7),
            }
            stats.append(result)
            print(f"✅ 1天:{m1['clicks']}点击 | 7天:{m7['clicks']}点击 | 30天:{m30['clicks']}点击")
        except Exception as e:
            err = str(e)[:60]
            print(f"⚠️ {err}")
            stats.append({
                "site_url": url, "m1": {"clicks": 0, "impressions": 0, "ctr_pct": 0, "avg_position": 0, "daily_rows": 0},
                "m7": {"clicks": 0, "impressions": 0, "ctr_pct": 0, "avg_position": 0, "daily_rows": 0},
                "m30": {"clicks": 0, "impressions": 0, "ctr_pct": 0, "avg_position": 0, "daily_rows": 0},
                "clicks": 0, "impressions": 0, "ctr_pct": 0, "avg_position": 0, "daily_rows": 0,
                "status": f"ERROR: {err}",
                "top_queries": [], "top_pages": [], "devices": [], "countries": [],
            })

    # 生成 Excel
    wb = Workbook()
    wb.remove(wb.active)  # 删除默认 sheet

    for label, days in WINDOWS:
        # 构造该窗口的 stats 视图
        window_stats = []
        for s in stats:
            key = "m1" if days == 1 else ("m7" if days == 7 else "m30")
            window_stats.append({
                "site_url": s["site_url"],
                "clicks": s[key]["clicks"],
                "impressions": s[key]["impressions"],
                "ctr_pct": s[key]["ctr_pct"],
                "avg_position": s[key]["avg_position"],
                "daily_rows": s[key].get("daily_rows", 0),
                "status": s["status"],
            })
        write_summary_sheet(wb, label, window_stats, days)

    write_detail_sheet(wb, "明细-近7天", stats)

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"gsc_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    wb.save(filepath)

    print(f"\n{'='*70}")
    total_clicks_7d = sum(s["clicks"] for s in stats)
    print(f"🏁 {len(stats)} 站点 · 近7天总点击: {total_clicks_7d}")
    print(f"📄 报告已保存: {filepath}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
