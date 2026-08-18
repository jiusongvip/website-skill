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

import json
import os
import re
import sys
import time
import concurrent.futures
from datetime import datetime, timedelta

# 强制 UTF-8 输出，避免 Windows GBK 控制台下 emoji 崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── 路径配置 ────────────────────────────────────────────
# 数据目录（凭证 + 报告）：环境变量 GSC_DATA_DIR 优先，默认为 skill 根目录（脚本上一级）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.environ.get("GSC_DATA_DIR", SKILL_ROOT)
SERVICE_ACCOUNT_FILE = os.path.join(DATA_DIR, "service_account.json")
OUTPUT_DIR = os.path.join(DATA_DIR, "gsc_reports")
META_CACHE_FILE = os.path.join(DATA_DIR, "site_meta.json")  # 站点上线时间+简介缓存

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


def build_daily_series(rows: list, start: str, end: str) -> list:
    """把按日期维度的 rows 补齐为 start→end 的连续日期序列，缺失日期补 0"""
    by_date = {r.get("keys", [""])[0]: r for r in rows}
    start_d = datetime.strptime(start, "%Y-%m-%d")
    end_d = datetime.strptime(end, "%Y-%m-%d")
    series = []
    d = start_d
    while d <= end_d:
        ds = d.strftime("%Y-%m-%d")
        r = by_date.get(ds, {})
        series.append({
            "date": ds,
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
        })
        d += timedelta(days=1)
    return series


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


# ── HTML 输出 ───────────────────────────────────────────

# Cloudflare API 配置（自动获取各站点上线时间，环境变量可覆盖）
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GSC 站点效果 · 近7天趋势</title>
<script src="https://www.gstatic.com/charts/loader.js"></script>
<style>
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", Roboto, "Microsoft YaHei", "PingFang SC", Arial, sans-serif; background: #f8f9fa; color: #202124; }
header { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 20px 24px; }
.header-top { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 6px; }
header h1 { margin: 0; font-size: 20px; font-weight: 500; }
header .meta { color: #5f6368; font-size: 13px; }
.download-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #1a73e8; color: #fff; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 500; white-space: nowrap; }
.download-btn:hover { background: #1765cc; }
.layout { display: flex; align-items: flex-start; }
.sidebar { width: 264px; flex-shrink: 0; position: sticky; top: 0; height: 100vh; overflow-y: auto; background: #fff; border-right: 1px solid #e0e0e0; }
.sidebar-title { padding: 16px 16px 8px; font-size: 13px; color: #5f6368; font-weight: 600; }
.sidebar a { display: block; padding: 8px 16px; font-size: 14px; line-height: 1.4; color: #202124; text-decoration: none; border-left: 3px solid transparent; word-break: break-all; cursor: pointer; }
.sidebar a:hover { background: #f1f3f4; }
.sidebar a.active { background: #e8f0fe; border-left-color: #4285F4; color: #1a73e8; }
main { flex: 1; min-width: 0; padding: 24px 32px; max-width: 1280px; }
.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 24px; overflow: hidden; scroll-margin-top: 20px; }
.card-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid #f1f3f4; }
.card-head h2 { margin: 0 0 4px; font-size: 18px; font-weight: 500; }
.card-head .url { color: #5f6368; font-size: 13px; word-break: break-all; }
.url a { color: #1a73e8; text-decoration: none; }
.url a:hover { text-decoration: underline; }
.url .launch { color: #9aa0a6; }
.intro { color: #5f6368; font-size: 13px; line-height: 1.5; margin-top: 4px; }
.metrics { display: flex; gap: 20px; flex-wrap: wrap; }
.metric { text-align: center; min-width: 52px; }
.metric b { display: block; font-size: 20px; font-weight: 500; }
.metric span { font-size: 12px; color: #5f6368; }
.chart { width: 100%; height: 320px; }
.empty { padding: 48px 20px; text-align: center; color: #5f6368; font-size: 14px; }
.badge-error { color: #d93025; font-weight: 600; }
.alert { margin: 16px 24px 0; padding: 16px 20px; background: #fdecea; border: 1px solid #f5c6c3; border-radius: 8px; color: #b3261e; font-size: 14px; line-height: 1.7; }
.alert h2 { margin: 0 0 8px; font-size: 16px; }
.alert p { margin: 4px 0; }
.alert code { background: #fff; padding: 2px 6px; border-radius: 4px; font-size: 12px; word-break: break-all; }
.menu-btn { display: none; background: #f1f3f4; border: 1px solid #dadce0; border-radius: 6px; font-size: 14px; cursor: pointer; color: #202124; padding: 7px 12px; align-items: center; gap: 6px; }
.title-wrap { display: flex; align-items: center; gap: 12px; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 150; opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }
@media (max-width: 768px) {
  header { position: sticky; top: 0; z-index: 100; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .header-top { flex-direction: column; align-items: stretch; gap: 8px; margin-bottom: 4px; }
  header h1 { font-size: 18px; }
  .menu-btn { display: inline-flex; }
  .download-btn { justify-content: center; font-size: 13px; padding: 8px 12px; }
  header .meta { font-size: 12px; line-height: 1.5; }
  .layout { display: block; }
  .sidebar { position: fixed; top: 0; left: 0; height: 100vh; width: 272px; z-index: 200; transform: translateX(-100%); transition: transform 0.25s ease; box-shadow: 2px 0 12px rgba(0,0,0,0.18); }
  .sidebar.open { transform: translateX(0); }
  .mask.show { opacity: 1; pointer-events: auto; }
  main { padding: 16px 12px; }
  .card { margin-bottom: 16px; border-radius: 6px; scroll-margin-top: 150px; }
  .card-head { flex-direction: column; align-items: flex-start; gap: 8px; padding: 12px 14px; }
  .card-head h2 { font-size: 16px; }
  .metrics { gap: 12px; width: 100%; }
  .metric { min-width: 0; flex: 1; }
  .metric b { font-size: 17px; }
  .metric span { font-size: 11px; }
  .intro { font-size: 12px; }
  .chart { height: 260px; }
  .alert { margin: 12px 12px 0; padding: 12px 14px; font-size: 13px; }
}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <div class="title-wrap">
      <button class="menu-btn" id="menu-btn" type="button" aria-label="站点列表">☰ 站点</button>
      <h1>GSC 站点效果 · 近7天趋势</h1>
    </div>
    <a class="download-btn" href="__XLSX_FILE__" download>下载详细表格数据</a>
  </div>
  <div class="meta">生成时间：__GENERATED_AT__ · 共 __SITE_COUNT__ 个站点 · 折线图展示每个站点近 7 天按日的展示（左轴，紫色）与点击（右轴，蓝色）</div>
</header>
<div class="mask" id="mask"></div>
__BANNER__
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-title">站点列表（__SITE_COUNT__）</div>
    <nav id="site-nav"></nav>
  </aside>
  <main id="charts"></main>
</div>
<script>
const SITES = __SITES_JSON__;
google.charts.load('current', {packages: ['corechart']});
google.charts.setOnLoadCallback(drawAll);

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
  });
}

function drawAll() {
  const container = document.getElementById('charts');
  const nav = document.getElementById('site-nav');
  const sidebar = document.getElementById('sidebar');
  const mask = document.getElementById('mask');
  const links = [];
  SITES.forEach(function (site, idx) {
    const id = 'site-' + idx;

    const link = document.createElement('a');
    link.textContent = site.name;
    link.dataset.idx = String(idx);
    link.addEventListener('click', function () {
      const el = document.getElementById(id);
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (sidebar) { sidebar.classList.remove('open'); }
      if (mask) { mask.classList.remove('show'); }
    });
    nav.appendChild(link);
    links.push(link);

    const m = site.m7 || {};
    const err = site.status && site.status.indexOf('ERROR') === 0;
    const badge = err ? ' <span class="badge-error">' + escapeHtml(site.status) + '</span>' : '';
    const siteLink = site.link || ('https://' + site.name);
    const launch = site.launch_date ? ' · 上线 ' + escapeHtml(site.launch_date) : '';
    const intro = site.intro ? '<div class="intro">' + escapeHtml(site.intro) + '</div>' : '';
    const card = document.createElement('div');
    card.className = 'card';
    card.id = id;
    card.innerHTML =
      '<div class="card-head">' +
        '<div>' +
          '<h2>' + escapeHtml(site.name) + '</h2>' +
          '<div class="url"><a href="' + escapeHtml(siteLink) + '" target="_blank" rel="noopener">' + escapeHtml(site.url || site.name) + '</a>' + launch + badge + '</div>' +
          intro +
        '</div>' +
        '<div class="metrics">' +
          '<div class="metric"><b>' + m.clicks + '</b><span>点击</span></div>' +
          '<div class="metric"><b>' + m.impressions + '</b><span>展示</span></div>' +
          '<div class="metric"><b>' + m.ctr_pct + '%</b><span>CTR</span></div>' +
          '<div class="metric"><b>' + m.avg_position + '</b><span>均位</span></div>' +
        '</div>' +
      '</div>' +
      '<div class="chart" id="chart-' + idx + '"></div>';
    container.appendChild(card);

    if (!site.daily || site.daily.length === 0) {
      document.getElementById('chart-' + idx).outerHTML = '<div class="empty">该站点近 7 天暂无数据</div>';
      return;
    }
    drawSiteChart('chart-' + idx, site);
  });

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const idx = entry.target.id.replace('site-', '');
        links.forEach(function (l) { l.classList.toggle('active', l.dataset.idx === idx); });
      }
    });
  }, { rootMargin: '-25% 0px -65% 0px', threshold: 0 });
  document.querySelectorAll('.card').forEach(function (c) { observer.observe(c); });
}

function drawSiteChart(id, site) {
  const isMobile = window.innerWidth <= 768;
  const data = new google.visualization.DataTable();
  data.addColumn('string', '日期');
  data.addColumn('number', '展示');
  data.addColumn('number', '点击次数');
  site.daily.forEach(function (d) {
    const label = isMobile ? d.date.split('/').slice(1).join('/') : d.date;
    data.addRow([label, d.impressions, d.clicks]);
  });
  const options = {
    seriesType: 'line',
    series: {
      0: { targetAxisIndex: 0, color: '#5E35B1', lineWidth: 2, pointSize: 3 },
      1: { targetAxisIndex: 1, color: '#4285F4', lineWidth: 2, pointSize: 3 }
    },
    vAxes: {
      0: { format: '0', gridlines: { color: '#e0e0e0' } },
      1: { format: '0', gridlines: { color: 'transparent' } }
    },
    hAxis: { textStyle: { fontSize: isMobile ? 11 : 12 } },
    legend: { position: 'top', textStyle: { fontSize: isMobile ? 12 : 13 } },
    chartArea: isMobile
      ? { left: 44, right: 44, top: 34, bottom: 36, width: '84%', height: '64%' }
      : { left: 70, right: 70, top: 40, bottom: 40, width: '82%', height: '70%' },
    interpolateNulls: true
  };
  const chart = new google.visualization.ComboChart(document.getElementById(id));
  chart.draw(data, options);
}

// 移动端侧边栏抽屉开关
(function () {
  const menuBtn = document.getElementById('menu-btn');
  const sidebar = document.getElementById('sidebar');
  const mask = document.getElementById('mask');
  if (menuBtn && sidebar && mask) {
    menuBtn.addEventListener('click', function () {
      sidebar.classList.add('open');
      mask.classList.add('show');
    });
    mask.addEventListener('click', function () {
      sidebar.classList.remove('open');
      mask.classList.remove('show');
    });
  }
})();
</script>
</body>
</html>
"""


def build_sites_data(stats: list) -> list:
    """把 stats 转换为前端渲染用的 sites_data 列表"""
    sites_data = []
    for s in sorted(stats, key=lambda x: x.get("clicks", 0), reverse=True):
        m7 = s.get("m7", {})
        daily = []
        for r in s.get("daily7", []):
            y, m, d = r["date"].split("-")
            daily.append({
                "date": f"{int(y)}/{int(m)}/{int(d)}",
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
            })
        clean = short_name(s["site_url"])
        sites_data.append({
            "name": clean,
            "url": clean,
            "link": "https://" + clean,
            "launch_date": s.get("launch_date", ""),
            "intro": s.get("intro", ""),
            "status": s.get("status", "OK"),
            "m7": {
                "clicks": m7.get("clicks", 0),
                "impressions": m7.get("impressions", 0),
                "ctr_pct": m7.get("ctr_pct", 0),
                "avg_position": m7.get("avg_position", 0),
            },
            "daily": daily,
        })
    return sites_data


def render_html(sites_data: list, filepath: str, xlsx_filename: str, banner_html: str = ""):
    """渲染 HTML 模板并写文件"""
    sites_json = json.dumps(sites_data, ensure_ascii=False).replace("</", "<\\/")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = (HTML_TEMPLATE
            .replace("__SITES_JSON__", sites_json)
            .replace("__GENERATED_AT__", generated_at)
            .replace("__SITE_COUNT__", str(len(sites_data)))
            .replace("__XLSX_FILE__", xlsx_filename)
            .replace("__BANNER__", banner_html))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def write_html(stats: list, filepath: str, xlsx_filename: str = ""):
    """生成单页 HTML：每个站点一张近 7 天折线图（展示 + 点击，双 Y 轴）"""
    sites_data = build_sites_data(stats)
    render_html(sites_data, filepath, xlsx_filename)

    # 缓存最后一次成功的数据，供订阅到期时展示
    try:
        cache_file = os.path.join(OUTPUT_DIR, "last_sites.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(sites_data, f, ensure_ascii=False)
    except Exception:
        pass


def write_error_html(error_msg: str):
    """代理/订阅失效时，生成带提示横幅的页面（保留最后一次成功数据）"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    index_html = os.path.join(OUTPUT_DIR, "index.html")

    # 读取最后一次成功的站点数据
    sites_data = []
    cache_file = os.path.join(OUTPUT_DIR, "last_sites.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                sites_data = json.load(f)
        except Exception:
            sites_data = []

    err = error_msg[:300]
    banner = (
        '<div class="alert">'
        '<h2>⚠️ 数据更新失败：代理订阅可能已到期</h2>'
        '<p><b>原因：</b>无法连接 Google Search Console 数据源（Google API），'
        '通常是服务器上的代理订阅已到期或节点失效。</p>'
        f'<p><b>错误详情：</b><code>{err}</code></p>'
        '<p><b>解决方法：</b>请更换代理订阅链接，或续订当前订阅；恢复后数据将自动更新。</p>'
        '<p>下方展示的是最后一次成功更新的数据。</p>'
        '</div>'
    )

    render_html(sites_data, index_html, "report.xlsx", banner_html=banner)
    print(f"⚠️ 已生成订阅到期提示页: {index_html}")


def load_meta_cache() -> dict:
    """加载站点元信息缓存（域名 -> {launch_date, intro}）"""
    try:
        if os.path.exists(META_CACHE_FILE):
            with open(META_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_meta_cache(cache: dict):
    """保存站点元信息缓存"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(META_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fetch_cf_launch_dates() -> dict:
    """从 Cloudflare Pages API 获取各站点上线时间（域名 -> 日期）"""
    dates = {}
    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        print("⚠️ 未配置 Cloudflare 凭证，跳过上线时间获取")
        return dates
    try:
        page = 1
        while True:
            url = (f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}"
                   f"/pages/projects?page={page}")
            resp = httpx.get(url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                             timeout=30, trust_env=False)
            data = resp.json()
            if not data.get("success"):
                print(f"⚠️ Cloudflare API 失败: {data.get('errors')}")
                break
            for p in data.get("result", []):
                created = (p.get("created_on") or "")[:10]
                for d in p.get("domains", []):
                    if d.endswith(".pages.dev") or not created:
                        continue
                    dates[d] = created
            total_pages = data.get("result_info", {}).get("total_pages", 1)
            if page >= total_pages or not data.get("result"):
                break
            page += 1
    except Exception as e:
        print(f"⚠️ 获取上线时间失败: {e}")
    return dates


def translate_to_zh(text: str) -> str:
    """把英文翻译成中文（Google Translate 免费接口，需走代理）"""
    if not text:
        return ""
    try:
        resp = httpx.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text},
            timeout=10,
        )
        data = resp.json()
        parts = [seg[0] for seg in data[0] if seg and seg[0]]
        return "".join(parts).strip()
    except Exception:
        return ""  # 翻译失败返回空，调用方保留旧值


def fetch_site_intro_raw(domain: str) -> str:
    """抓取网站首页 meta description（fallback title），返回英文原文"""
    try:
        resp = httpx.get(
            f"https://{domain}",
            timeout=10,
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"},
        )
        text = resp.text
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', text, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', text, re.I)
        if m and m.group(1).strip():
            return m.group(1).strip()
        t = re.search(r'<title[^>]*>([^<]+)</title>', text, re.I)
        if t and t.group(1).strip():
            return t.group(1).strip()
        return ""
    except Exception:
        return ""


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
        # 代理订阅可能已到期，生成提示页（保留最后一次成功数据）
        write_error_html(str(e))
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

    # 站点元信息：上线时间缺失才获取；简介抓原文对比，有变化才翻译更新
    domains = [short_name(s["url"]) for s in sites]
    meta_cache = load_meta_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    # 每天抓取所有站点首页原文（低成本 HTTP GET，仅对比用）
    print("\n🌐 抓取站点首页简介原文 ...")
    raw_intros = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        fm = {ex.submit(fetch_site_intro_raw, d): d for d in domains}
        for fut in concurrent.futures.as_completed(fm):
            d = fm[fut]
            try:
                raw_intros[d] = fut.result()
            except Exception:
                raw_intros[d] = ""

    # 上线时间：缺失才调 Cloudflare API
    missing_launch = [d for d in domains if not meta_cache.get(d, {}).get("launch_date")]
    launch_dates = fetch_cf_launch_dates() if missing_launch else {}

    # 简介：原文有变化才翻译更新
    changed = 0
    for d in domains:
        meta = meta_cache.setdefault(d, {})
        raw = raw_intros.get(d, "")
        if raw and raw != meta.get("intro_raw", ""):
            zh = translate_to_zh(raw)
            if zh:  # 翻译成功才更新；失败保留旧值，下次再试
                meta["intro_raw"] = raw
                meta["intro"] = zh
                meta["intro_fetched_at"] = today
                changed += 1
        if d in launch_dates and not meta.get("launch_date"):
            meta["launch_date"] = launch_dates[d]
    save_meta_cache(meta_cache)
    print(f"✅ 简介更新 {changed} 个（其余复用缓存）\n")

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

            # 近 7 天按日数据（补齐缺失日期为 0，用于 HTML 折线图）
            daily7 = build_daily_series(filter_rows_by_days(daily, 7), start7, end7)

            result = {
                "site_url": url,
                "m1": m1, "m7": m7, "m30": m30,
                "clicks": m7["clicks"],            # 排序用 7 天点击
                "impressions": m7["impressions"],
                "ctr_pct": m7["ctr_pct"],
                "avg_position": m7["avg_position"],
                "daily_rows": m7["daily_rows"],
                "daily7": daily7,
                "launch_date": meta_cache.get(short_name(url), {}).get("launch_date", ""),
                "intro": meta_cache.get(short_name(url), {}).get("intro", ""),
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
                "daily7": [],
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

    # 固定文件名（线上访问入口 + 下载），覆盖式，保证 URL 不变
    index_html = os.path.join(OUTPUT_DIR, "index.html")
    report_xlsx = os.path.join(OUTPUT_DIR, "report.xlsx")
    write_html(stats, index_html, xlsx_filename="report.xlsx")
    wb.save(report_xlsx)

    # 带时间戳的存档（保留历史，不覆盖）
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    archive_xlsx = os.path.join(OUTPUT_DIR, f"gsc_report_{stamp}.xlsx")
    wb.save(archive_xlsx)

    print(f"\n{'='*70}")
    total_clicks_7d = sum(s["clicks"] for s in stats)
    print(f"🏁 {len(stats)} 站点 · 近7天总点击: {total_clicks_7d}")
    print(f"📊 线上页面: {index_html}")
    print(f"📄 下载表格: {report_xlsx}")
    print(f"🗄 历史存档: {archive_xlsx}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
