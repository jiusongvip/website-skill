# -*- coding: utf-8 -*-
"""GPT-Image-2 批量生图：批量提交、批量轮询、批量下载。

用法:
  python gen_batch.py --subjects "a red apple|a blue whale|a green forest"
  python gen_batch.py --subjects-file subjects.txt
  python gen_batch.py --subjects "a red apple" --size 16:9 --out ./images --no-webp

说明:
  - 配置统一从上级目录 config.json 读取（API Key / prompt 模板 / size 映射 / 轮询参数）
  - 主题列表支持 | 分隔或每行一个的主题文件
  - 输出文件按主题词转 kebab-case 命名，默认同时输出 WebP（质量 80%）
依赖: requests, Pillow（--no-webp 时不需要 Pillow）
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

API_KEY = os.environ.get(CONFIG["env_key_override"]) or CONFIG["api_key"]
GEN_URL = CONFIG["endpoints"]["generate"]
DETAIL_URL = CONFIG["endpoints"]["detail"]
POLL_INTERVAL = CONFIG["poll"]["interval_seconds"]
POLL_MAX = CONFIG["poll"]["max_attempts"]
HEADERS = {"Authorization": API_KEY, "Content-Type": "application/json"}

# 带退避重试的会话：GET/轮询自动重试（连接被重置/5xx 时），POST 不重试避免重复扣费
SESSION = requests.Session()
RETRY = Retry(
    total=6,
    connect=6,
    read=6,
    backoff_factor=2.0,
    status_forcelist=[429, 500, 502, 503, 504],
)
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY))
SESSION.mount("http://", HTTPAdapter(max_retries=RETRY))


def build_prompt(subject):
    """按 config.json 的 prompt 模板组合提示词，只需替换主题词"""
    return CONFIG["prompt"]["base"].format(
        subject=subject,
        style=CONFIG["prompt"]["style"],
        lighting=CONFIG["prompt"]["lighting"],
        composition=CONFIG["prompt"]["composition"],
        negative=CONFIG["prompt"]["negative"],
    )


def submit(subject, size):
    """提交单个生图任务，返回 (subject, task_id)。POST 不自动重试，避免重复扣费"""
    resp = SESSION.post(
        GEN_URL + "?key=" + API_KEY,
        json={"prompt": build_prompt(subject), "size": size},
        headers=HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    r = resp.json()
    if r.get("code") != 200:
        raise RuntimeError(f"[{subject}] 提交失败: {r.get('msg')}")
    return subject, r["data"]["id"]


def extract_image_url(data):
    """递归查找成图 URL（兼容不同字段名）"""
    if isinstance(data, dict):
        for k in ("url", "image", "image_url", "images", "output", "result", "img"):
            v = data.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
            if isinstance(v, list) and v:
                for item in v:
                    if isinstance(item, str) and item.startswith("http"):
                        return item
        for v in data.values():
            u = extract_image_url(v)
            if u:
                return u
    elif isinstance(data, list):
        for item in data:
            u = extract_image_url(item)
            if u:
                return u
    return None


def query(task):
    """查询单个任务状态，返回 (subject, task_id, status, data)。GET 带自动重试"""
    subject, task_id = task
    resp = SESSION.get(
        DETAIL_URL + "?key=" + API_KEY + "&id=" + task_id,
        headers=HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    d = resp.json()
    data = d.get("data", {})
    return subject, task_id, data.get("status"), data


def slugify(subject):
    """主题词转安全文件名（kebab-case），支持中英文"""
    s = subject.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff-]+", "", s)
    return s.strip("-")[:80] or "image"


def main():
    parser = argparse.ArgumentParser(description="GPT-Image-2 批量生图")
    parser.add_argument("--subjects", help="主题列表，用 | 分隔")
    parser.add_argument("--subjects-file", help="主题文件，每行一个主题")
    parser.add_argument("--size", default=CONFIG["size"]["default"], help="图片尺寸")
    parser.add_argument("--out", default=CONFIG["batch"]["default_output_dir"], help="输出目录")
    parser.add_argument("--no-webp", action="store_true", help="仅下载原图，不转 WebP")
    args = parser.parse_args()

    # ---- 收集主题（支持每行 “文件名|主题”，文件名留空时自动从主题生成）----
    subjects = []  # list of (name, subject)
    if args.subjects_file:
        with open(args.subjects_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if "|" in line:
                    name, subject = line.split("|", 1)
                    subjects.append((name.strip(), subject.strip()))
                else:
                    subjects.append((slugify(line), line))
    elif args.subjects:
        for s in args.subjects.split("|"):
            s = s.strip()
            if s:
                subjects.append((slugify(s), s))
    if not subjects:
        parser.error("请提供 --subjects 或 --subjects-file")
    print(f"共 {len(subjects)} 个主题，size={args.size}")

    # ---- Step 2: 批量提交 ----
    print("=== 批量提交 ===")
    tasks = []
    name_map = {}
    workers = min(CONFIG["batch"]["submit_threads"], len(subjects))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for (name, subject), (_, tid) in zip(subjects, ex.map(lambda s: submit(s[1], args.size), subjects)):
            tasks.append((subject, tid))
            name_map[subject] = name
            print(f"  已提交: {name} -> {tid}")

    # ---- Step 3: 批量轮询 ----
    print("=== 批量轮询 ===")
    done, failed = {}, {}
    for attempt in range(POLL_MAX):
        pending = [t for t in tasks if t not in done and t not in failed]
        if not pending:
            break
        time.sleep(POLL_INTERVAL)
        workers = min(CONFIG["batch"]["poll_threads"], len(pending))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(query, pending))
        for subject, tid, status, data in results:
            if status == 2:
                url = extract_image_url(data)
                if url:
                    done[(subject, tid)] = url
                    print(f"  [完成] {subject}")
                else:
                    failed[(subject, tid)] = "未找到成图 URL"
                    print(f"  [失败] {subject}: 未找到成图 URL")
            elif status == 3:
                msg = data.get("message") or "未知错误"
                failed[(subject, tid)] = msg
                print(f"  [失败] {subject}: {msg}")
        print(f"  第 {attempt + 1} 轮: 完成 {len(done)}/{len(tasks)}")
        if len(done) + len(failed) >= len(tasks):
            break
    else:
        for t in tasks:
            if t not in done and t not in failed:
                failed[t] = "轮询超时"

    # ---- Step 4: 批量下载 ----
    print("=== 批量下载 ===")
    os.makedirs(args.out, exist_ok=True)
    try:
        from PIL import Image
        has_pil = True
    except ImportError:
        has_pil = False

    for (subject, tid), url in done.items():
        slug = name_map.get(subject, slugify(subject))
        raw_path = os.path.join(args.out, slug + ".png")
        resp = SESSION.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        resp.raise_for_status()
        with open(raw_path, "wb") as f:
            f.write(resp.content)
        if not args.no_webp and has_pil:
            quality = CONFIG["image_processing"]["quality"]
            webp_path = os.path.join(args.out, slug + ".webp")
            Image.open(raw_path).save(webp_path, "WEBP", quality=quality)
            os.remove(raw_path)
            print(f"  {subject} -> {webp_path}")
        else:
            print(f"  {subject} -> {raw_path}")

    print(f"\n完成: 成功 {len(done)} 张, 失败 {len(failed)} 张")
    if failed:
        for (subject, tid), msg in failed.items():
            print(f"  [失败详情] {subject}: {msg}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
