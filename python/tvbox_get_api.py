#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TVBox 接口抓取工具。

配置（API_LIST / API_MIRRORS）统一放在仓库根目录的 tvboxapilinks.txt（JSON 格式），
运行时由本脚本读取；可用 --config 指定其它配置文件路径。
输出：tvbox/ 目录下的接口 JSON，以及仓库根目录的 list.txt 与 SUMMARY.txt。

list.txt 位置约定：仓库根目录（LIST_TXT = "list.txt"）。
"""

import re
import json
import base64
import os
import sys
import argparse
import binascii
import gzip
import time
import functools
from datetime import datetime, timezone, timedelta
from threading import Thread
from queue import Queue
from collections import OrderedDict


# ---------- 时间工具 ----------
def beijing_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


def today_str():
    return beijing_now().strftime("%Y%m%d")


# ---------- 配置加载 ----------
DEFAULT_CONFIG_FILE = "tvboxapilinks.txt"


def _load_api_config():
    config_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
            break
        elif arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
            break

    candidates = []
    if config_path:
        candidates.append(config_path)
    candidates += [DEFAULT_CONFIG_FILE, "api_list.json"]

    for json_path in candidates:
        if json_path and os.path.exists(json_path):
            print(f"  using config: {json_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            api_list = [tuple(x) for x in cfg.get("API_LIST", [])]
            api_mirrors = cfg.get("API_MIRRORS", {})
            return api_list, api_mirrors

    # 兼容旧式 Python 模块 api_list.py
    try:
        import importlib
        mod = importlib.import_module("api_list")
        return mod.API_LIST, mod.API_MIRRORS
    except Exception as e:
        print(f"  no config found ({DEFAULT_CONFIG_FILE} / api_list.py), using empty: {e}")
        return [], {}


# ---------- 网络库兼容 ----------
try:
    import requests
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False

try:
    from urllib.request import Request, urlopen
    HAVE_URLLIB = True
except Exception:
    HAVE_URLLIB = False

if HAVE_REQUESTS:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass


# ---------- 调试开关 ----------
parser = argparse.ArgumentParser(description="TVBox 接口抓取与备份")
parser.add_argument("--debug", action="store_true", help="输出详细调试日志")
parser.add_argument("--force", action="store_true", help="强制执行（工作流手动触发时使用）")
parser.add_argument("--check-config", action="store_true", help="仅检查配置，不抓取")
parser.add_argument("--selftest", action="store_true", help="自测模式")
ARGS, _ = parser.parse_known_args()
DEBUG = ARGS.debug


def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")


# ---------- 超时装饰器 ----------
class TimeoutError(Exception):
    pass


def timeout(seconds):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result_queue = Queue()

            def target():
                try:
                    result_queue.put(("success", func(*args, **kwargs)))
                except Exception as e:
                    result_queue.put(("error", e))

            thread = Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                raise TimeoutError(f"{func.__name__} timed out after {seconds}s")

            status, value = result_queue.get()
            if status == "error":
                raise value
            return value
        return wrapper
    return decorator


# ---------- AES-128-CBC（纯标准库，含加解密） ----------
class AES128:
    RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]
    SBOX = [
        0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
        0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
        0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
        0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
        0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
        0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
        0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
        0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
        0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
        0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
        0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
        0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
        0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
        0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
        0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
        0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16,
    ]

    @staticmethod
    def _sub_word(w):
        return (AES128.SBOX[(w >> 24) & 0xFF] << 24 |
                AES128.SBOX[(w >> 16) & 0xFF] << 16 |
                AES128.SBOX[(w >> 8) & 0xFF] << 8 |
                AES128.SBOX[w & 0xFF])

    @staticmethod
    def _rot_word(w):
        return ((w << 8) & 0xFFFFFFFF) | ((w >> 24) & 0xFF)

    @staticmethod
    def _expand_key(key):
        Nk, Nr = 4, 10
        w = [0] * (4 * (Nr + 1))
        for i in range(Nk):
            w[i] = (key[4*i] << 24) | (key[4*i+1] << 16) | (key[4*i+2] << 8) | key[4*i+3]
        for i in range(Nk, 4 * (Nr + 1)):
            temp = w[i - 1]
            if i % Nk == 0:
                temp = AES128._sub_word(AES128._rot_word(temp)) ^ (AES128.RCON[i // Nk] << 24)
            w[i] = w[i - Nk] ^ temp
        out = bytearray(16 * (Nr + 1))
        for i in range(4 * (Nr + 1)):
            out[4*i]   = (w[i] >> 24) & 0xFF
            out[4*i+1] = (w[i] >> 16) & 0xFF
            out[4*i+2] = (w[i] >> 8) & 0xFF
            out[4*i+3] = w[i] & 0xFF
        return bytes(out)

    @staticmethod
    def _xtime(b):
        return ((b << 1) ^ (0x1B if b & 0x80 else 0)) & 0xFF

    @staticmethod
    def _inv_sub_bytes(state):
        inv = [0] * 256
        for i in range(256):
            inv[AES128.SBOX[i]] = i
        return bytes(inv[b] for b in state)

    @staticmethod
    def _inv_shift_rows(state):
        s = list(state)
        for row, shift in [(1, 1), (2, 2), (3, 3)]:
            base = [s[row + 4*c] for c in range(4)]
            base = base[-shift:] + base[:-shift]
            for c in range(4):
                s[row + 4*c] = base[c]
        return bytes(s)

    @staticmethod
    def _inv_mix_columns(state):
        def mul(a, b):
            r = 0
            while b:
                if b & 1:
                    r ^= a
                a = AES128._xtime(a)
                b >>= 1
            return r
        s = list(state)
        for c in range(4):
            i = 4*c
            a0, a1, a2, a3 = s[i], s[i+1], s[i+2], s[i+3]
            s[i]   = mul(a0,0x0e) ^ mul(a1,0x0b) ^ mul(a2,0x0d) ^ mul(a3,0x09)
            s[i+1] = mul(a0,0x09) ^ mul(a1,0x0e) ^ mul(a2,0x0b) ^ mul(a3,0x0d)
            s[i+2] = mul(a0,0x0d) ^ mul(a1,0x09) ^ mul(a2,0x0e) ^ mul(a3,0x0b)
            s[i+3] = mul(a0,0x0b) ^ mul(a1,0x0d) ^ mul(a2,0x09) ^ mul(a3,0x0e)
        return bytes(s)

    @staticmethod
    def _decrypt_block(block, rk):
        Nr = 10
        state = bytes(a ^ b for a, b in zip(block, rk[16*Nr:16*(Nr+1)]))
        for r in range(Nr-1, 0, -1):
            state = AES128._inv_shift_rows(state)
            state = AES128._inv_sub_bytes(state)
            state = bytes(a ^ b for a, b in zip(state, rk[16*r:16*(r+1)]))
            state = AES128._inv_mix_columns(state)
        state = AES128._inv_shift_rows(state)
        state = AES128._inv_sub_bytes(state)
        state = bytes(a ^ b for a, b in zip(state, rk[0:16]))
        return state

    @staticmethod
    def decrypt_cbc(ciphertext, key, iv):
        assert len(key) == 16 and len(iv) == 16
        assert len(ciphertext) % 16 == 0
        rk = AES128._expand_key(key)
        plaintext = bytearray()
        prev = iv
        for i in range(0, len(ciphertext), 16):
            decrypted = AES128._decrypt_block(ciphertext[i:i+16], rk)
            plain_block = bytes(a ^ b for a, b in zip(decrypted, prev))
            plaintext += plain_block
            prev = ciphertext[i:i+16]
        if len(plaintext) > 0:
            pad = plaintext[-1]
            if 1 <= pad <= 16 and len(plaintext) >= pad:
                if all(b == pad for b in plaintext[-pad:]):
                    plaintext = plaintext[:-pad]
        return bytes(plaintext).decode("utf-8", errors="replace")

    @staticmethod
    def _encrypt_block(block, rk):
        Nr = 10
        state = bytes(a ^ b for a, b in zip(block, rk[0:16]))
        for r in range(1, Nr):
            state = AES128._sub_bytes(state)
            state = AES128._shift_rows(state)
            state = AES128._mix_columns(state)
            state = bytes(a ^ b for a, b in zip(state, rk[16*r:16*(r+1)]))
        state = AES128._sub_bytes(state)
        state = AES128._shift_rows(state)
        return bytes(a ^ b for a, b in zip(state, rk[16*Nr:16*(Nr+1)]))

    @staticmethod
    def _sub_bytes(state):
        return bytes(AES128.SBOX[b] for b in state)

    @staticmethod
    def _shift_rows(state):
        s = list(state)
        for row, shift in [(1, 1), (2, 2), (3, 3)]:
            base = [s[row + 4*c] for c in range(4)]
            base = base[shift:] + base[:shift]
            for c in range(4):
                s[row + 4*c] = base[c]
        return bytes(s)

    @staticmethod
    def _mix_columns(state):
        def mul(a, b):
            r = 0
            while b:
                if b & 1:
                    r ^= a
                a = AES128._xtime(a)
                b >>= 1
            return r
        s = list(state)
        for c in range(4):
            i = 4*c
            a0, a1, a2, a3 = s[i], s[i+1], s[i+2], s[i+3]
            s[i]   = AES128._xtime(a0) ^ (AES128._xtime(a1) ^ a1) ^ a2 ^ a3
            s[i+1] = a0 ^ AES128._xtime(a1) ^ (AES128._xtime(a2) ^ a2) ^ a3
            s[i+2] = a0 ^ a1 ^ AES128._xtime(a2) ^ (AES128._xtime(a3) ^ a3)
            s[i+3] = (AES128._xtime(a0) ^ a0) ^ a1 ^ a2 ^ AES128._xtime(a3)
        return bytes(s)

    @staticmethod
    def encrypt_cbc(plaintext, key, iv):
        assert len(key) == 16 and len(iv) == 16
        rk = AES128._expand_key(key)
        prev = iv
        out = bytearray()
        for i in range(0, len(plaintext), 16):
            block = plaintext[i:i+16]
            xored = bytes(a ^ b for a, b in zip(block, prev))
            encrypted = AES128._encrypt_block(xored, rk)
            out += encrypted
            prev = encrypted
        return bytes(out)


# ---------- 运行配置 ----------
RAW_API_LIST, API_MIRRORS = _load_api_config()

TVBOX_UAS = [
    ("okhttp/3.15",                               "com.iptvbox"),
    ("okhttp/4.9.3",                               "com.iptvbox"),
    ("TVBox/1.0.0",                                "com.iptvbox"),
    ("com.github.tvbox",                           "com.iptvbox"),
    ("Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)", "com.iptvbox"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", ""),
]

HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
}

OUTPUT_DIR = "tvbox"
LIST_TXT = "list.txt"
MAX_DEPTH = 5
REQUEST_TIMEOUT = 20
PER_URL_TIMEOUT = 30   # 每个 URL 独立超时（秒）


# ---------- URL 规范化 + 接口分组 ----------
def normalize_url(url):
    if not url:
        return url
    u = url.strip()
    matches = list(re.finditer(r"https?://", u))
    if len(matches) >= 2:
        u = u[matches[-1].start():]
    if u.endswith("/") and u.count("/") > 2:
        u = u.rstrip("/")
    return u


def build_api_list(raw_api_list, api_mirrors):
    grouped = OrderedDict()
    for item in raw_api_list:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        name, url = item[0], item[1]
        if not url:
            continue
        grouped.setdefault(name, OrderedDict())
        grouped[name][normalize_url(url)] = None

    for name, mirrors in api_mirrors.items():
        if not isinstance(mirrors, list):
            mirrors = [mirrors]
        grouped.setdefault(name, OrderedDict())
        for u in mirrors:
            if not u:
                continue
            grouped[name][normalize_url(u)] = None

    return [(name, list(url_dict.keys())) for name, url_dict in grouped.items()]


API_LIST = build_api_list(RAW_API_LIST, API_MIRRORS)


# ---------- 通用工具 ----------
def right_padding(s, ch, length):
    return s[:length] if len(s) >= length else s + (ch * (length - len(s)))


def is_json(text):
    if not text:
        return False
    t = text.strip()
    return t.startswith("{") or t.startswith("[")


def collapse_whitespace(text):
    if text is None:
        return ""
    if not re.search(r"\s", text):
        return text
    return re.sub(r"\s+", " ", text).strip()


def filter_json(text):
    try:
        obj = json.loads(text)
    except Exception:
        return text
    if not isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    keep = {"video", "sites", "lives", "parses", "rules",
            "spider", "wallpaper", "livePlayHeaders", "md5", "name", "homeSite",
            "homeLogo", "homeBg", "homeSearch", "homeRec", "searchable", "logo"}
    filtered = {k: v for k, v in obj.items() if k in keep}
    return json.dumps(filtered if filtered else obj, ensure_ascii=False, indent=2)


def get_base_url(source_url):
    if not source_url:
        return ""
    idx = source_url.rfind("/")
    return source_url[:idx + 1] if idx > 0 else ""


def is_absolute_url(value):
    if not isinstance(value, str):
        return True
    v = value.strip()
    if not v:
        return True
    return v.startswith(("http://", "https://", "data:", "file://", "//"))


def resolve_url(rel_path, base_url):
    if not rel_path or is_absolute_url(rel_path):
        return rel_path
    if not base_url:
        return rel_path
    from urllib.parse import urljoin
    return urljoin(base_url, rel_path)


# ---------- URL 绝对化（相对地址补全） ----------
def absolutize_json(text, source_url):
    if not source_url:
        return text
    try:
        obj = json.loads(text)
    except Exception:
        return text

    base = get_base_url(source_url)
    if not base:
        return text

    top_url_fields = {
        "spider", "wallpaper", "homeLogo", "homeBg",
        "homeSite", "livePlayHeaders", "logo", "homeSearch",
        "homeRec", "md5"
    }
    spider_prefixes = ("csp_", "json_", "nodejs_", "py_", "js_", "http_")

    def should_resolve(val):
        if not val or not isinstance(val, str):
            return False
        val = val.strip()
        if not val:
            return False
        if val.startswith(("http://", "https://", "data:", "file://", "//")):
            return False
        if any(val.startswith(p) for p in spider_prefixes):
            return False
        return not val.isdigit()

    def resolve_if_needed(val):
        return resolve_url(val, base) if should_resolve(val) else val

    def resolve_ext_object(ext):
        if isinstance(ext, str):
            return resolve_if_needed(ext)
        if isinstance(ext, list):
            return [resolve_if_needed(v) if isinstance(v, str) else v for v in ext]
        if isinstance(ext, dict):
            for k, v in ext.items():
                if isinstance(v, str):
                    ext[k] = resolve_if_needed(v)
                elif isinstance(v, list):
                    ext[k] = [resolve_if_needed(i) if isinstance(i, str) else i for i in v]
                elif isinstance(v, dict):
                    resolve_ext_object(v)
        return ext

    if isinstance(obj, dict):
        for field in top_url_fields:
            if field in obj and should_resolve(obj[field]):
                obj[field] = resolve_url(obj[field], base)

        if "sites" in obj and isinstance(obj["sites"], list):
            for site in obj["sites"]:
                if not isinstance(site, dict):
                    continue
                if "ext" in site:
                    site["ext"] = resolve_ext_object(site["ext"])
                for field in ("jar", "playUrl", "logo", "url", "epg"):
                    if field in site and should_resolve(site[field]):
                        site[field] = resolve_url(site[field], base)
                if "api" in site and isinstance(site["api"], str):
                    api_val = site["api"].strip()
                    if _looks_like_url(api_val) and should_resolve(api_val):
                        site["api"] = resolve_url(api_val, base)

        if "lives" in obj and isinstance(obj["lives"], list):
            for live in obj["lives"]:
                if not isinstance(live, dict):
                    continue
                for field in ("url", "logo", "epg", "playUrl"):
                    if field in live and should_resolve(live[field]):
                        live[field] = resolve_url(live[field], base)

        if "parses" in obj and isinstance(obj["parses"], list):
            for parse in obj["parses"]:
                if not isinstance(parse, dict):
                    continue
                for field in ("url", "logo"):
                    if field in parse and should_resolve(parse[field]):
                        parse[field] = resolve_url(parse[field], base)

        if "rules" in obj and isinstance(obj["rules"], list):
            for rule in obj["rules"]:
                if not isinstance(rule, dict):
                    continue
                if "url" in rule and should_resolve(rule["url"]):
                    rule["url"] = resolve_url(rule["url"], base)

    return json.dumps(obj, ensure_ascii=False, indent=2)


def _looks_like_url(value):
    if not value:
        return False
    if value.startswith(("http://", "https://", "//", "data:")):
        return True
    if "/" in value:
        return True
    if "." in value and not value.startswith("."):
        parts = value.split(".")
        return len(parts) >= 2 and all(p for p in parts)
    return False


# ---------- list.txt 读写（位置：仓库根目录） ----------
def fmt_size(num_bytes):
    if num_bytes is None:
        return "-"
    try:
        num_bytes = int(num_bytes)
    except (ValueError, TypeError):
        return "-"
    if num_bytes < 0:
        return "-"
    if num_bytes < 1024:
        return f"{num_bytes}B"
    return f"{num_bytes / 1024:.1f}K"


def _file_key(name):
    return re.sub(r"[^\w\u4e00-\u9fff]", "_", name)


_SUFFIX_RE = re.compile(r"(?:线路|一线|二线|三线|vip线|专线|备用|主线路?|测试|勿传|vip|line)\s*$", re.I)


def _note_of(name):
    if not name:
        return ""
    cleaned = _SUFFIX_RE.sub("", _file_key(name))
    return cleaned or _file_key(name)


def load_list_txt(path=LIST_TXT):
    old = {}
    if not os.path.exists(path):
        return old
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r").strip()
            if not line:
                continue
            parts = re.split(r"\t|\|", line, maxsplit=3)
            if len(parts) < 2:
                continue
            file_name = parts[0].strip()
            date_str = parts[1].strip()
            size_str = parts[2].strip() if len(parts) >= 3 else "-"
            url_str = parts[3].strip() if len(parts) >= 4 else ""
            if not file_name or not date_str:
                continue
            old[file_name] = (date_str, size_str, url_str)
    return old


def save_list_txt(latest, path=LIST_TXT):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for file_name, rec in sorted(latest.items(), key=lambda kv: kv[1][0], reverse=True):
            date_str, size_str, url_str = rec if len(rec) == 3 else (rec[0], rec[1], "")
            f.write(f"{file_name}|{date_str}|{size_str}|{url_str}\n")


def update_list_txt(results, path=LIST_TXT):
    today = today_str()
    old = load_list_txt(path)

    new_by_key = {}
    for info in results:
        name = info.get("name")
        if not name or not info.get("ok"):
            continue
        new_by_key[_file_key(name) + ".json"] = info

    merged = dict(old)
    for file_name, info in new_by_key.items():
        if info.get("ok"):
            merged[file_name] = (
                info.get("date") or today,
                fmt_size(info.get("bytes")),
                info.get("success_url", ""),
            )

    save_list_txt(merged, path)

    print("\n" + "=" * 62)
    print(f"  list.txt updated ({path})")
    print("=" * 62)
    if not merged:
        print("  (empty)")
    for file_name, rec in sorted(merged.items(), key=lambda kv: kv[1][0], reverse=True):
        date_str, size_str, url_str = rec if len(rec) == 3 else (rec[0], rec[1], "")
        tag = "更新" if (file_name in old and file_name in new_by_key) else (
            "新增" if file_name in new_by_key else "保留")
        print(f"  {file_name}|{date_str}|{size_str}|{url_str}  [{tag}]")
    print("=" * 62)
    return merged


# ---------- 解密 / 解混淆 ----------
def _try_decrypt_2423_hex(stripped):
    idx2423 = stripped.index("2423")
    idx2324 = stripped.index("2324")
    key_hex = stripped[idx2423 + 4: idx2324]
    try:
        key_raw = bytes.fromhex(key_hex).decode("latin-1", errors="ignore")
    except Exception:
        key_raw = key_hex
    key_str = right_padding(key_raw, "0", 16)
    data_start = idx2324 + 4
    data_end = len(stripped) - 26
    if data_end <= data_start:
        raise ValueError("hex: invalid data range")
    data_hex = stripped[data_start: data_end]
    ts_hex = stripped.rstrip()[-26:]
    try:
        ts_bytes = bytes.fromhex(ts_hex)
    except Exception:
        ts_bytes = ts_hex.encode("utf-8")
    key_bytes = key_str.encode("utf-8")[:16]
    iv_bytes = right_padding(ts_bytes.decode("latin-1"), "0", 16).encode("utf-8")[:16]
    cipher_bytes = binascii.unhexlify(data_hex)
    return AES128.decrypt_cbc(cipher_bytes, key_bytes, iv_bytes)


def _try_decrypt_2423_plain(S):
    idx2324 = S.index("2324")
    p_doll = S.index("$#")
    p_sharp = S.index("#$")
    data_hex = re.sub(r"[^0-9a-fA-F]", "", S[idx2324 + 4: p_doll])
    if len(data_hex) % 2 != 0:
        data_hex = data_hex[:-1]
    key = right_padding(S[p_doll + 2: p_sharp], "0", 16)
    iv = right_padding(S[-13:], "0", 16)
    return AES128.decrypt_cbc(bytes.fromhex(data_hex), key.encode("latin-1")[:16], iv.encode("latin-1")[:16])


def find_result(raw_text, _raw_bytes=None, _depth=0):
    """递归解密：base64、**壳、2423-AES、gzip，直到得到 JSON。"""
    if _raw_bytes is None and raw_text is not None:
        _raw_bytes = raw_text.encode("utf-8", errors="ignore")
    content = raw_text if raw_text is not None else ""
    if not content and _raw_bytes:
        content = _raw_bytes.decode("utf-8", errors="ignore")
    if is_json(content):
        return content

    star_idx = None
    if _raw_bytes is not None:
        pos = _raw_bytes.find(b"**")
        if pos >= 8:
            star_idx = pos
    if star_idx is None:
        m = re.search(r"[A-Za-z0-9]{8}\*\*", content)
        if m:
            star_idx = content.index(m.group()) + 10

    if star_idx is not None:
        if _raw_bytes is not None:
            b64_bytes = bytes(b for b in _raw_bytes[star_idx + 2:] if b not in (0x09, 0x0a, 0x0d, 0x20))
            try:
                return find_result(b64_bytes.decode("latin-1", errors="ignore"), _depth=_depth + 1)
            except Exception as e:
                dbg(f"shell base64 decode failed: {e}")
                content = b64_bytes.decode("latin-1", errors="ignore")
        else:
            b64 = re.sub(r"[^A-Za-z0-9+/=]", "", content[star_idx:])
            try:
                return find_result(base64.b64decode(b64 + "==").decode("utf-8", errors="ignore"), _depth=_depth + 1)
            except Exception:
                content = b64

    stripped = collapse_whitespace(content).strip()
    has_delim = "$#" in stripped and "#$" in stripped
    has_2423_structure = stripped.startswith("2423") and "2324" in stripped
    if stripped.startswith("2423") and (has_delim or has_2423_structure):
        last_err = None
        try:
            return find_result(_try_decrypt_2423_hex(stripped), _depth=_depth + 1)
        except Exception as e:
            last_err = e
        try:
            return find_result(_try_decrypt_2423_plain(stripped), _depth=_depth + 1)
        except Exception as e2:
            raise RuntimeError(f"2423 decrypt failed (hex={last_err} / plain={e2})")

    clean = re.sub(r"\s", "", content)
    if re.match(r"^[A-Za-z0-9+/=]+$", clean) and len(clean) > 50:
        try:
            decoded = base64.b64decode(clean + "==").decode("utf-8", errors="ignore")
            if is_json(decoded):
                return decoded
        except Exception:
            pass

    if _raw_bytes is not None:
        try:
            decompressed = gzip.decompress(_raw_bytes).decode("utf-8", errors="ignore")
            if is_json(decompressed):
                return decompressed
        except Exception:
            pass
    return content


# ---------- 网络 ----------
def fetch_url(url, ua, xrw=""):
    headers = dict(HEADERS_BASE)
    headers["User-Agent"] = ua
    if xrw:
        headers["X-Requested-With"] = xrw
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc and any(ord(c) > 127 for c in parsed.netloc):
            try:
                import idna
                netloc = idna.encode(parsed.netloc).decode("ascii")
                url = url.replace(parsed.netloc, netloc)
            except Exception:
                pass
    except Exception:
        pass

    if HAVE_REQUESTS:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True, verify=False)
        if r.status_code == 200 and len(r.content) > 20:
            return r.content
        raise RuntimeError(f"HTTP {r.status_code}")
    elif HAVE_URLLIB:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
            if len(data) > 20:
                return data
            raise RuntimeError("empty body")
    else:
        raise RuntimeError("no available http library")


def try_fetch(url):
    last_err = None
    for ua, xrw in TVBOX_UAS:
        for attempt in range(2):
            try:
                raw = fetch_url(url, ua, xrw)
                if raw.lstrip().startswith(b"<"):
                    break
                return raw, ua
            except Exception as e:
                last_err = e
                if attempt == 0:
                    time.sleep(0.5)
    raise RuntimeError(str(last_err))


@timeout(PER_URL_TIMEOUT)
def try_fetch_one(url):
    return try_fetch(url)


def try_fetch_all(urls):
    """遍历 URL 列表：实时打印当前 URL，每个独立超时，成功即返回。"""
    errs = []
    for idx, u in enumerate(urls, 1):
        print(f"    [{idx}/{len(urls)}] trying: {u}")
        try:
            raw, ua = try_fetch_one(u)
            print(f"    ok [{idx}/{len(urls)}] {u} (UA={ua})")
            return raw, ua, u
        except TimeoutError:
            print(f"    timeout [{idx}/{len(urls)}] {u}")
            errs.append(f"{u} -> timeout")
        except Exception as e:
            print(f"    fail [{idx}/{len(urls)}] {u} ({e})")
            errs.append(f"{u} -> {e}")
    raise RuntimeError(" | ".join(errs))


# ---------- JSON 处理 ----------
def clean_json_comments(text):
    if not text:
        return text
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    out, in_block = [], False
    for line in lines:
        if in_block:
            if "*/" in line:
                in_block = False
                line = line[line.index("*/") + 2:]
            else:
                continue
        if "/*" in line:
            before, after = line.split("/*", 1)
            line = before + (after[after.index("*/") + 2:] if "*/" in after else "")
            if "*/" not in after:
                in_block = True
        if "//" in line:
            in_str, sc = False, None
            for i, ch in enumerate(line):
                if ch in ('"', "'") and (i == 0 or line[i-1] != "\\"):
                    if not in_str:
                        in_str, sc = True, ch
                    elif ch == sc:
                        in_str = False
                elif ch == "/" and i + 1 < len(line) and line[i+1] == "/" and not in_str:
                    line = line[:i]
                    break
        if line.strip():
            out.append(line)
    return "\n".join(out)


def extract_json(text):
    if not text:
        return text
    text = clean_json_comments(text)
    start = next((i for i, ch in enumerate(text) if ch in "{["), -1)
    if start == -1:
        return text
    end = next((i for i in range(len(text) - 1, -1, -1) if text[i] in "}]"), -1)
    if end <= start:
        return text
    jt = text[start:end + 1]
    try:
        json.loads(jt)
        return jt
    except Exception:
        return text


def process(name, urls) -> dict:
    print(f"\n[{name}] {len(urls)} source(s)")
    try:
        raw, ua, used = try_fetch_all(urls)
    except Exception as e:
        print(f"  all failed: {e}")
        return {"name": name, "status": "FAILED", "file": None, "ok": False, "success_url": "", "bytes": 0}

    text = find_result("", _raw_bytes=raw)
    text = extract_json(text)
    text = absolutize_json(text, used)

    try:
        json.loads(text)
        parsed = True
    except Exception:
        parsed = False

    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip().strip(".")[:120] or "unnamed"
    file_name = safe + ".json"
    out_path = os.path.join(OUTPUT_DIR, file_name)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  -> {out_path} ({len(raw)} bytes, parsed={'yes' if parsed else 'no'})")
    return {
        "name": name,
        "status": "OK" if parsed else "RAW",
        "file": out_path,
        "ok": True,
        "success_url": used,
        "bytes": len(raw),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = beijing_now().strftime("%Y%m%d_%H%M%S")
    summary = []

    print("=" * 62)
    print(f"  TVBox API fetcher  {ts}")
    print("=" * 62)

    old = load_list_txt(LIST_TXT)
    if old:
        print(f"  loaded existing list.txt: {len(old)} entries, will merge")

    for name, urls in API_LIST:
        try:
            summary.append(process(name, urls))
        except TimeoutError as e:
            print(f"  timeout: {e}")
            summary.append({"name": name, "status": "TIMEOUT", "file": None, "ok": False, "success_url": ""})
        except Exception as e:
            print(f"  failed: {e}")
            summary.append({"name": name, "status": "FAILED", "file": None, "ok": False, "success_url": ""})

    update_list_txt(summary, LIST_TXT)

    report = "SUMMARY.txt"
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"TVBox API fetch report  {ts}\n")
        f.write("=" * 62 + "\n\n")
        for it in summary:
            f.write(f"[{it['name']}] {it.get('ua','')}\n")
            f.write(f"  status: {it['status']}\n")
            f.write(f"  file: {it.get('file')}\n")
            f.write(f"  url: {it.get('success_url','')}\n\n")

    print("\n" + "=" * 62)
    print("  summary")
    print("=" * 62)
    for it in summary:
        icon = "ok" if it.get("ok") else "--"
        print(f"  {icon} {it['name']:8s} | {it['status']:10s} | {it.get('file','')}")
    print(f"\n  report: {report}")
    print(f"  changelog: {LIST_TXT}")
    print("=" * 62)


def selftest():
    global RAW_API_LIST, API_MIRRORS, API_LIST
    RAW_API_LIST = [
        ["饭太硬", "http://www.example.net/tv"],
        ["南风", "https://gh-proxy.com/https://raw.githubusercontent.com/yoursmile66/TVBox/main/XC.json"],
    ]
    API_MIRRORS = {"饭太硬": ["http://www.example.net/tv"]}
    API_LIST = build_api_list(RAW_API_LIST, API_MIRRORS)
    print("  selftest config loaded")


if __name__ == "__main__":
    if ARGS.selftest:
        selftest()
    elif ARGS.check_config:
        print("=" * 62)
        print("  config check (normalize + group + dedupe, no fetch)")
        print("=" * 62)
        for name, urls in API_LIST:
            print(f"\n  [{name}] {len(urls)} source(s)")
            for i, u in enumerate(urls, 1):
                print(f"    {i}. {u}")
        print("\n" + "=" * 62)
        print(f"  total {len(API_LIST)} interfaces")
        print("=" * 62)
    else:
        main()
