#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 伪装下载器（带网速/进度/百分比）
Android/QPython 终端单行刷新显示
"""

import requests
import os
import sys
import time

# ================== 用户配置区 ==================
DOWNLOAD_URL = "https://mpimg.cn/down.php/31d75f152d5ac34ee395947b877c21d2.zip"
SAVE_PATH    = "data/奇奇.zip"
EXTRACT      = False
# ===============================================

TVBOX_UAS = [
    ("okhttp/3.15", "com.iptvbox"),
    ("okhttp/4.9.3", "com.iptvbox"),
    ("TVBox/1.0.0", "com.iptvbox"),
    ("com.github.tvbox", "com.iptvbox"),
    ("Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)", "com.iptvbox"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", ""),
]

HEADERS_BASE = {
    "Accept": "*/*",
    "Connection": "keep-alive",
}

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass


def fmt_size(b):
    for u in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}TB"


def download(url, save_path):
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)

    for i, (ua, xrw) in enumerate(TVBOX_UAS):
        headers = dict(HEADERS_BASE)
        headers["User-Agent"] = ua
        if xrw:
            headers["X-Requested-With"] = xrw

        print(f"\n  [{i+1}/{len(TVBOX_UAS)}] {ua[:30]}...")

        try:
            r = requests.get(url, headers=headers, stream=True,
                             timeout=(10, 120), verify=False, allow_redirects=True)
            print(f"  状态: {r.status_code}")
            if r.status_code != 200:
                continue

            total = int(r.headers.get('Content-Length', 0))
            print(f"  大小: {fmt_size(total) if total else '未知'}\n")

            downloaded = 0
            start_time = time.time()
            last_time = start_time
            last_downloaded = 0

            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()

                        # 每 0.3 秒刷新一次显示
                        if now - last_time >= 0.3:
                            elapsed = now - start_time
                            speed = (downloaded - last_downloaded) / (now - last_time)

                            # 百分比和进度条
                            if total:
                                pct = downloaded / total * 100
                                bar_len = 25
                                filled = int(bar_len * downloaded / total)
                                bar = '█' * filled + '░' * (bar_len - filled)
                                line = f"\r  [{bar}] {pct:5.1f}% | {fmt_size(downloaded)}/{fmt_size(total)} | {fmt_size(speed)}/s | 耗时{int(elapsed)}s"
                            else:
                                speed_avg = downloaded / elapsed if elapsed > 0 else 0
                                line = f"\r  ↓ {fmt_size(downloaded)} | {fmt_size(speed)}/s | 耗时{int(elapsed)}s"

                            # 截断到终端宽度
                            line = line[:75]
                            print(line, end='', flush=True)

                            last_time = now
                            last_downloaded = downloaded

            # 最终状态
            print('\r' + ' ' * 75 + '\r', end='')  # 清行
            final_size = os.path.getsize(save_path)
            total_time = time.time() - start_time
            avg_speed = final_size / total_time if total_time > 0 else 0

            print(f"  ✅ 完成!")
            print(f"     大小: {fmt_size(final_size)}")
            print(f"     均速: {fmt_size(avg_speed)}/s")
            print(f"     耗时: {total_time:.1f}s")
            print(f"     路径: {os.path.abspath(save_path)}")

            # ZIP 校验
            with open(save_path, 'rb') as f:
                magic = f.read(2)
            if magic == b'PK':
                print(f"     类型: ZIP ✓")
                return True
            else:
                print(f"     ⚠️ 非 ZIP 文件")
                return False

        except requests.exceptions.Timeout:
            print(f"  ❌ 超时")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")

    return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DOWNLOAD_URL
    save = sys.argv[2] if len(sys.argv) > 2 else SAVE_PATH
    extract_flag = len(sys.argv) > 3 and sys.argv[3].lower() in ('1', 'true', 'yes')

    print("\n" + "=" * 60)
    print("  TVBox 伪装下载器（带网速监控）")
    print("=" * 60)
    print(f"  链接: {url}")
    print(f"  保存: {save}")
    print("=" * 60)

    if download(url, save):
        print("\n🎉 下载成功！")
    else:
        print("\n💀 全部失败")
