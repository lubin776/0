#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TVBox 直播源聚合下载器。

流程：
1. 扫描仓库根 tvbox/ 下所有接口 JSON，提取 lives 模块（type=0）
2. URL 去重、名称冲突自动编号、无名称兜底为「接口名+直播」
3. 模拟 TVBox 环境下载直播源 -> tvbox/live/（.m3u + .txt）
4. 聚合索引 -> tvbox/海量直播线路.json
5. 合并生成仓库根 livelist.txt（旧记录保留、本次成功记录覆盖、仅更新时间变动）

livelist.txt 位置约定：仓库根目录（REPO_ROOT / "livelist.txt"）。
"""

import os
import re
import json
import time
import uuid
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urlunparse

# ---------- 请求配置 ----------
TVBOX_UAS = [
    "okhttp/3.12.13",
    "Mozilla/5.0 (Linux; Android 9; Pixel 3 XL Build/PQ3A.190801.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36",
    "VLC/3.0.16 LibVLC/3.0.16",
    "AppleCoreMedia/1.0.0.19C56 (iPhone; U; CPU OS 15_2 like Mac OS X; en_us)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "bingcha/1.1 (mianfeifenxiang)",
]
TVBOX_HEADERS = {
    "X-Requested-With": "com.fongmi.android.tv",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# ---------- 路径配置 ----------
REPO_ROOT = Path(__file__).resolve().parent.parent   # 仓库根目录
SCAN_DIR = REPO_ROOT / "tvbox"                      # 接口 JSON 扫描目录
OUTPUT_LIVE_DIR = SCAN_DIR / "live"                 # 直播源输出目录
AGGREGATE_JSON = SCAN_DIR / "海量直播线路.json"      # 聚合索引文件
LIVELIST_PATH = REPO_ROOT / "livelist.txt"          # 根目录 livelist

IGNORE_URL_KEYWORDS = [
    "127.0.0.1", "localhost", "example.com",
    "切换成你自己的地址", "your.url.here", "test.com",
]

DOWNLOAD_TIMEOUT = 25
MAX_RETRIES = 3
TODAY = datetime.now().strftime("%Y%m%d")
DEBUG = False


# ---------- 工具函数 ----------
def normalize_url(url):
    try:
        p = urlparse(url.strip())
        return urlunparse(p._replace(
            scheme=p.scheme.lower(), netloc=p.netloc.lower(),
            path=p.path.rstrip("/"), fragment=""))
    except Exception:
        return url.strip()


def is_valid_url(url):
    if not url or not isinstance(url, str):
        return False
    u = url.lower()
    if not u.startswith(("http://", "https://")):
        return False
    return not any(kw.lower() in u for kw in IGNORE_URL_KEYWORDS)


def format_file_size(n):
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}K"
    return f"{n / (1024 * 1024):.1f}M"


def get_unique_name(base, used):
    if base not in used:
        used.add(base)
        return base
    idx = 1
    while True:
        name = f"{base}{idx}线"
        if name not in used:
            used.add(name)
            return name
        idx += 1


# ---------- 核心步骤 ----------
def scan_and_extract_lives():
    """扫描 tvbox/ 下所有 JSON，提取有效 live 条目（type=0）。"""
    print("\n[1/4] scan interface files, extract lives ...")
    all_lives = []
    used_urls = set()

    if not SCAN_DIR.exists():
        print(f"  scan dir not found: {SCAN_DIR}")
        return all_lives

    for json_file in SCAN_DIR.glob("*.json"):
        if json_file.name == AGGREGATE_JSON.name or "live" in json_file.name:
            continue
        source = json_file.name
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  skip {source}: {e}")
            continue

        lives = data.get("lives", [])
        if not isinstance(lives, list):
            continue

        valid = 0
        for item in lives:
            if not isinstance(item, dict) or item.get("type", 0) != 0:
                continue
            url = item.get("url", "")
            if not is_valid_url(url):
                continue
            norm = normalize_url(url)
            if norm in used_urls:
                continue
            used_urls.add(norm)

            all_lives.append({
                "name": item.get("name", "").strip(),
                "url": url,
                "type": 0,
                "playerType": item.get("playerType"),
                "ua": item.get("ua", ""),
                "source": source,
            })
            valid += 1
        print(f"  {source}: {valid} live(s)")

    print(f"  total (deduped): {len(all_lives)}")
    return all_lives


def aggregate_lives(lives):
    """命名 + 生成聚合索引 tvbox/海量直播线路.json。"""
    print("\n[2/4] aggregate & name ...")
    used_names = set()
    aggregated = []

    for item in lives:
        base = item["name"] if item["name"] else Path(item["source"]).stem + "直播"
        item["name"] = get_unique_name(base, used_names)
        aggregated.append(item)
        if len(aggregated) <= 10:
            print(f"      {len(aggregated)}. {item['name']}  <=  {item['url'][:60]}")
    if len(aggregated) > 10:
        print(f"      ... total {len(aggregated)}")

    OUTPUT_LIVE_DIR.mkdir(parents=True, exist_ok=True)
    with open(AGGREGATE_JSON, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)
    print(f"  index -> {AGGREGATE_JSON}")

    return aggregated


def download_live_source(live):
    """下载单个直播源 -> tvbox/live/{name}.m3u + .txt。"""
    name, url, ua = live["name"], live["url"], live.get("ua", "")
    headers = dict(TVBOX_HEADERS)
    headers["User-Agent"] = ua.strip() if ua and isinstance(ua, str) and ua.strip() else TVBOX_UAS[int(time.time()) % len(TVBOX_UAS)]

    for retry in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True, verify=True)
            resp.raise_for_status()
            content = resp.content
            size = len(content)

            with open(OUTPUT_LIVE_DIR / f"{name}.m3u", "wb") as f:
                f.write(b"#EXTM3U\n")
                f.write(f'#EXTINF:-1 tvg-name="{name}",{name}\n'.encode("utf-8"))
                f.write(content)

            with open(OUTPUT_LIVE_DIR / f"{name}.txt", "w", encoding="utf-8") as f:
                f.write(url + "\n")
            return True, size
        except Exception:
            if DEBUG and retry == MAX_RETRIES - 1:
                import traceback
                traceback.print_exc()
            if retry == MAX_RETRIES - 1:
                return False, 0
            time.sleep(1)
    return False, 0


def download_all_lives(lives):
    print(f"\n[3/4] download live sources ...")
    print(f"  output: {OUTPUT_LIVE_DIR}")
    results = {}
    fail = []
    for idx, live in enumerate(lives, 1):
        ok, size = download_live_source(live)
        results[live["name"]] = (ok, size)
        print(f"  [{idx}/{len(lives)}] {live['name']} {'ok' if ok else 'FAIL'} ({format_file_size(size)})")
        if not ok:
            fail.append(live["name"])
    print(f"\n  done: {sum(1 for v in results.values() if v[0])}/{len(lives)} ok")
    if fail:
        print(f"  failed: {', '.join(fail)}")
    return results


def generate_livelist(lives, results):
    """合并新旧记录，写入仓库根 livelist.txt。新记录覆盖旧记录。"""
    print("\n[4/4] generate/merge livelist.txt ...")

    old_records = {}
    if LIVELIST_PATH.exists():
        with open(LIVELIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split("|")
                    old_records[parts[0]] = line

    new_records = {}
    for live in lives:
        name = live["name"]
        if name not in results or not results[name][0]:
            continue
        _, size = results[name]
        new_records[name] = (
            f"{name}|{TODAY}|{format_file_size(size)}|{live['url']}|{live['source']}|{live.get('ua', '')}"
        )

    merged = {**old_records, **new_records}

    # 本次成功的排前面（按聚合顺序），旧记录未被覆盖的放后面
    final = [new_records[n] for n in new_records]
    final += [old_records[n] for n in old_records if n not in new_records]

    with open(LIVELIST_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(final))

    print(f"  -> {LIVELIST_PATH}")
    print(f"  updated: {len(new_records)}, preserved: {len(old_records) - len(new_records)}")


def main():
    start = time.time()
    import argparse
    ap = argparse.ArgumentParser(description="TVBox 直播源聚合器")
    ap.add_argument("--debug", action="store_true", help="输出详细调试日志")
    ap.add_argument("--force", action="store_true", help="强制执行（工作流手动触发时使用）")
    args = ap.parse_args()
    DEBUG = args.debug  # 模块级
    print("=" * 60)
    print("TVBox Live aggregator")
    print("=" * 60)

    raw = scan_and_extract_lives()
    if not raw:
        print("\nno valid live interfaces, exit")
        return

    aggregated = aggregate_lives(raw)
    results = download_all_lives(aggregated)
    generate_livelist(aggregated, results)

    print("\n" + "=" * 60)
    print(f"done in {time.time() - start:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
