#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 接口一键抓取工具（增强版 · 含 list.txt 插入式更新日志）
运行：python tvbox_get_api.py            # 正常抓取
      python tvbox_get_api.py --selftest # 离线自测
      python tvbox_get_api.py --debug    # 调试日志
输出：output/名称.json（固定文件名，直接覆盖）
      output/list.txt（插入式更新日志，自动追加）

配置加载优先级：
  1. api_list.json（如果存在）
  2. api_list.py（默认，需自行创建）

list.txt 格式（两列，"|" 分隔，同名文件追加新行，旧行保留作历史）：
    饭太硬.json|20260905
    嗷呜.json|20260903
    饭太硬.json|20260908   <- 更新成功再追加一行（网页取最新那条 = 上一次成功时间）
更新失败时不追加新行，网页继续显示该文件"上一次成功的时间"。
"""

import re
import json
import base64
import os
import sys
import binascii
import gzip
import time
import functools
from datetime import datetime
from threading import Thread
from queue import Queue

# ================== 配置加载（JSON / PY 双版本） ==================
def _load_api_config():
    """
    优先级：
    1. api_list.json（如果存在）
    2. api_list.py（默认）
    """
    json_path = "api_list.json"
    py_module = "api_list"

    # ---- JSON 版 ----
    if os.path.exists(json_path):
        print(f"  📄 使用配置文件: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        api_list = [tuple(x) for x in cfg.get("API_LIST", [])]
        api_mirrors = cfg.get("API_MIRRORS", {})
        return api_list, api_mirrors

    # ---- PY 版 ----
    print(f"  📄 使用配置文件: {py_module}.py")
    import importlib
    mod = importlib.import_module(py_module)
    return mod.API_LIST, mod.API_MIRRORS


# ================== 网络库兼容 ==================
try:
    import requests
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError
    HAVE_URLLIB = True
except Exception:
    HAVE_URLLIB = False

if HAVE_REQUESTS:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

# ====================== 调试开关 ======================
DEBUG = "--debug" in sys.argv


def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")


# ======================================================================
# 超时装饰器（通用解决方案）
# ======================================================================
class TimeoutError(Exception):
    pass


def timeout(seconds):
    """函数超时装饰器，支持 Windows 和 Unix"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result_queue = Queue()

            def target():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))

            thread = Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")

            status, value = result_queue.get()
            if status == 'error':
                raise value
            return value
        return wrapper
    return decorator


# ======================================================================
# AES-128-CBC + PKCS7（纯标准库实现）
# ======================================================================
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
        """AES-128-CBC 解密 + 严格 PKCS7 去填充"""
        assert len(key) == 16 and len(iv) == 16
        assert len(ciphertext) % 16 == 0
        rk = AES128._expand_key(key)
        plaintext = bytearray()
        prev = iv
        for i in range(0, len(ciphertext), 16):
            block = ciphertext[i:i+16]
            decrypted = AES128._decrypt_block(block, rk)
            plain_block = bytes(a ^ b for a, b in zip(decrypted, prev))
            plaintext += plain_block
            prev = block
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
        state = bytes(a ^ b for a, b in zip(state, rk[16*Nr:16*(Nr+1)]))
        return state

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
    def _encrypt_cbc(plaintext, key, iv):
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


# ======================================================================
# 配置区 —— 从外部文件加载
# ======================================================================
API_LIST, API_MIRRORS = _load_api_config()

# 请求指纹池
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
OUTPUT_DIR = "output"
LIST_TXT = os.path.join(OUTPUT_DIR, "list.txt")   # ★ 插入式更新日志路径
MAX_DEPTH = 5
REQUEST_TIMEOUT = 20
TOTAL_TIMEOUT = 45


# ======================================================================
# 通用工具
# ======================================================================
def right_padding(s, ch, length):
    if len(s) >= length:
        return s[:length]
    return s + (ch * (length - len(s)))


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
            "homeLogo", "homeBg", "homeSearch", "homeRec", "searchable",
            "logo"}
    filtered = {k: v for k, v in obj.items() if k in keep}
    if not filtered:
        filtered = obj
    return json.dumps(filtered, ensure_ascii=False, indent=2)


def get_base_url(source_url):
    if not source_url:
        return ""
    idx = source_url.rfind("/")
    if idx <= 0:
        return ""
    return source_url[:idx + 1]


def is_absolute_url(value):
    if not isinstance(value, str):
        return True
    v = value.strip()
    if not v:
        return True
    if v.startswith(("http://", "https://", "data:", "file://", "//")):
        return True
    return False


def resolve_url(rel_path, base_url):
    if not rel_path or is_absolute_url(rel_path):
        return rel_path
    if not base_url:
        return rel_path
    from urllib.parse import urljoin
    return urljoin(base_url, rel_path)


# ======================================================================
# ★ 修复后的 absolutize_json —— 递归处理 ext 对象中的相对路径
# ======================================================================
def absolutize_json(text, source_url):
    """将 JSON 中的所有相对 URL 转换为绝对 URL"""
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
        if val.isdigit():
            return False
        return True

    def resolve_if_needed(val):
        return resolve_url(val, base) if should_resolve(val) else val

    # ★★★ 递归处理 ext 对象 ★★★
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
        # 顶层字段
        for field in top_url_fields:
            if field in obj and should_resolve(obj[field]):
                obj[field] = resolve_url(obj[field], base)

        # sites
        if "sites" in obj and isinstance(obj["sites"], list):
            for site in obj["sites"]:
                if not isinstance(site, dict):
                    continue

                # ★★★ 关键修复：递归处理 ext（字符串 or 对象） ★★★
                if "ext" in site:
                    site["ext"] = resolve_ext_object(site["ext"])

                for field in ("jar", "playUrl", "logo", "url", "epg"):
                    if field in site and should_resolve(site[field]):
                        site[field] = resolve_url(site[field], base)

                if "api" in site and isinstance(site["api"], str):
                    api_val = site["api"].strip()
                    if _looks_like_url(api_val) and should_resolve(api_val):
                        site["api"] = resolve_url(api_val, base)

        # lives
        if "lives" in obj and isinstance(obj["lives"], list):
            for live in obj["lives"]:
                if not isinstance(live, dict):
                    continue
                for field in ("url", "logo", "epg", "playUrl"):
                    if field in live and should_resolve(live[field]):
                        live[field] = resolve_url(live[field], base)

        # parses
        if "parses" in obj and isinstance(obj["parses"], list):
            for parse in obj["parses"]:
                if not isinstance(parse, dict):
                    continue
                for field in ("url", "logo"):
                    if field in parse and should_resolve(parse[field]):
                        parse[field] = resolve_url(parse[field], base)

        # rules
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
        if len(parts) >= 2 and all(p for p in parts):
            return True
    return False


# ======================================================================
# list.txt —— 插入式更新日志
# ======================================================================
def fmt_size(num_bytes):
    """字节 → 人类可读：<1024 显示 B，否则显示 K（保留 1 位小数）。无效返回 '-'"""
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
    """把接口名转成安全的文件名（中文保留，非法字符转下划线），与 process() 保持一致"""
    return re.sub(r"[^\w\u4e00-\u9fff]", "_", name)

_SUFFIX_RE = re.compile(r"(?:线路|一线|二线|三线|vip线|专线|备用|主线路?|测试|勿传|vip|line)\s*$", re.I)

def _note_of(name):
    """
    ★ 备注 = 接口名去掉非中文/非单词字符后的主体，再去掉末尾通用后缀。
    """
    if not name:
        return ""
    base = _file_key(name)
    cleaned = _SUFFIX_RE.sub("", base)
    return cleaned if cleaned else base


def load_list_txt(path=LIST_TXT):
    latest = {}
    if not os.path.exists(path):
        return latest
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
            note_str = parts[3].strip() if len(parts) >= 4 else ""
            if not file_name or not date_str:
                continue
            latest[file_name] = (date_str, size_str, note_str)
    return latest


def append_list_txt(name, date_str, size_k="-", note="", path=LIST_TXT):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    file_name = _file_key(name) + ".json"
    note = note or _note_of(name)
    line = f"{file_name}|{date_str}|{size_k}|{note}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
    return line.strip()


def update_list_txt(results, path=LIST_TXT):
    today = datetime.now().strftime("%Y%m%d")
    latest = load_list_txt(path)

    for info in results:
        name = info.get("name")
        if not name:
            continue
        if info.get("ok"):
            date_str = info.get("date") or today
            size_k = fmt_size(info.get("bytes"))
            note = info.get("note") or _note_of(name)
            append_list_txt(name, date_str, size_k, note, path)
            latest[_file_key(name) + ".json"] = (date_str, size_k, note)

    print("\n" + "=" * 62)
    print(f"  list.txt 更新记录  ({path})")
    print("=" * 62)
    if not latest:
        print("  （暂无成功记录）")
    for file_name, rec in sorted(latest.items(), key=lambda kv: kv[1][0], reverse=True):
        date_str, size_str, note_str = rec if len(rec) == 3 else (rec[0], rec[1], "")
        flag = "最新" if date_str == today else "历史"
        print(f"  {file_name}|{date_str}|{size_str}|{note_str}  [{flag}]")
    print("=" * 62)
    return latest


# ======================================================================
# 解密相关
# ======================================================================
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
        raise ValueError("hex形态: data区间非法")
    data_hex = stripped[data_start: data_end]
    content_rstrip = stripped.rstrip()
    ts_hex = content_rstrip[len(content_rstrip) - 26:]
    try:
        ts_bytes = bytes.fromhex(ts_hex)
    except Exception:
        ts_bytes = ts_hex.encode("utf-8")
    iv_str = right_padding(ts_bytes.decode("latin-1"), "0", 16)
    key_bytes = key_str.encode("utf-8")[:16]
    iv_bytes = iv_str.encode("utf-8")[:16]
    cipher_bytes = binascii.unhexlify(data_hex)
    return AES128.decrypt_cbc(cipher_bytes, key_bytes, iv_bytes)


def _try_decrypt_2423_plain(S):
    idx2324 = S.index("2324")
    p_doll = S.index("$#")
    p_sharp = S.index("#$")
    data_hex = S[idx2324 + 4: p_doll]
    data_hex = re.sub(r"[^0-9a-fA-F]", "", data_hex)
    if len(data_hex) % 2 != 0:
        data_hex = data_hex[:-1]
    key = right_padding(S[p_doll + 2: p_sharp], "0", 16)
    iv = right_padding(S[len(S) - 13:], "0", 16)
    key_bytes = key.encode("latin-1")[:16]
    iv_bytes = iv.encode("latin-1")[:16]
    cipher_bytes = bytes.fromhex(data_hex)
    return AES128.decrypt_cbc(cipher_bytes, key_bytes, iv_bytes)


def find_result(raw_text, _raw_bytes=None, _depth=0):
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
            b64_bytes = _raw_bytes[star_idx + 2:]
            b64_bytes = bytes(b for b in b64_bytes if b not in (0x09, 0x0a, 0x0d, 0x20))
            try:
                decoded = base64.b64decode(b64_bytes + b"==").decode("utf-8", errors="ignore")
                return find_result(decoded, _depth=_depth + 1)
            except Exception as e:
                dbg(f"字节壳base64解码失败: {e}")
                content = b64_bytes.decode("latin-1", errors="ignore")
        else:
            b64 = re.sub(r"[^A-Za-z0-9+/=]", "", content[star_idx:])
            try:
                decoded = base64.b64decode(b64 + "==").decode("utf-8", errors="ignore")
                return find_result(decoded, _depth=_depth + 1)
            except Exception:
                content = b64
    stripped = collapse_whitespace(content).strip()
    has_delim = "$#" in stripped and "#$" in stripped
    has_2423_structure = stripped.startswith("2423") and "2324" in stripped
    if stripped.startswith("2423") and (has_delim or has_2423_structure):
        last_err = None
        try:
            result = _try_decrypt_2423_hex(stripped)
            return find_result(result, _depth=_depth + 1)
        except Exception as e:
            last_err = e
        try:
            result = _try_decrypt_2423_plain(stripped)
            return find_result(result, _depth=_depth + 1)
        except Exception as e2:
            raise RuntimeError(f"2423 双形态均解密失败: hex={last_err} / plain={e2}")
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


# ======================================================================
# 网络请求
# ======================================================================
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
                netloc = idna.encode(parsed.netloc).decode('ascii')
                url = url.replace(parsed.netloc, netloc)
                dbg(f"域名 punycode 转换: {parsed.netloc} -> {netloc}")
            except Exception as e:
                dbg(f"punycode转换失败: {e}")
    except Exception as e:
        dbg(f"URL解析失败: {e}")

    if HAVE_REQUESTS:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT,
                        allow_redirects=True, verify=False)
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
        raise RuntimeError("无可用网络库")


def try_fetch(url):
    last_err = None
    for ua, xrw in TVBOX_UAS:
        for attempt in range(2):
            try:
                raw = fetch_url(url, ua, xrw)
                if raw.lstrip().startswith(b"<"):
                    dbg(f"{url} 拿到HTML首页, 轮询下一组")
                    break
                return raw, ua
            except Exception as e:
                last_err = e
                dbg(f"{url} UA={ua} 尝试 {attempt+1} 失败: {e}")
                if attempt == 0:
                    time.sleep(0.5)
    raise RuntimeError(str(last_err))


@timeout(TOTAL_TIMEOUT)
def try_fetch_all(urls):
    errs = []
    for u in urls:
        try:
            raw, ua = try_fetch(u)
            return raw, ua, u
        except Exception as e:
            errs.append(f"{u} -> {e}")
            dbg(f"URL {u} 失败: {e}")
    raise RuntimeError(" | ".join(errs))


# ======================================================================
# 主流程
# ======================================================================
def clean_json_comments(text):
    if not text:
        return text
    if text.startswith('\ufeff'):
        text = text[1:]
    lines = text.split('\n')
    cleaned_lines = []
    in_block_comment = False
    for line in lines:
        if in_block_comment:
            if '*/' in line:
                in_block_comment = False
                line = line[line.index('*/') + 2:]
            else:
                continue
        if '/*' in line:
            before, after = line.split('/*', 1)
            if '*/' in after:
                line = before + after[after.index('*/') + 2:]
            else:
                line = before
                in_block_comment = True
        if '//' in line:
            in_string = False
            string_char = None
            for i, char in enumerate(line):
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                elif char == '/' and i + 1 < len(line) and line[i+1] == '/' and not in_string:
                    line = line[:i]
                    break
        if line.strip():
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def extract_json(text):
    if not text:
        return text
    text = clean_json_comments(text)
    start = -1
    end = -1
    for i, char in enumerate(text):
        if char in '{[':
            start = i
            break
    if start == -1:
        return text
    for i in range(len(text) - 1, -1, -1):
        if text[i] in '}]':
            end = i + 1
            break
    if end == -1 or end <= start:
        return text
    json_text = text[start:end]
    try:
        json.loads(json_text)
        return json_text
    except Exception:
        return text


@timeout(TOTAL_TIMEOUT + 10)
def process(name, urls) -> dict:
    if isinstance(urls, str):
        urls = [urls]
    print(f"\n▶ [{name}] 尝试 {len(urls)} 个源")

    t0 = time.time()
    try:
        raw, ua, used_url = try_fetch_all(urls)
    except TimeoutError:
        raise RuntimeError(f"抓取超时（{TOTAL_TIMEOUT}秒）")

    print(f"  ✓ 下载成功 ({len(raw)} 字节, UA={ua})")
    print(f"  源地址: {used_url}")

    decrypted = find_result("", _raw_bytes=raw)
    decrypted = extract_json(decrypted)

    try:
        obj = json.loads(decrypted)
        formatted = filter_json(decrypted)
        status = "JSON"
    except Exception as e:
        dbg(f"JSON解析失败: {e}")
        try:
            obj = json.loads(decrypted)
            formatted = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            formatted = decrypted
        status = "TEXT"

    # ★ 关键：在 filter_json 之后、写文件之前，做绝对路径转换
    if status == "JSON":
        formatted = absolutize_json(formatted, used_url)

    safe = re.sub(r"[^\w\u4e00-\u9fff]", "_", name)
    path = os.path.join(OUTPUT_DIR, f"{safe}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(formatted)

    elapsed_ms = int((time.time() - t0) * 1000)
    print(f"  ✓ {status} | {len(formatted)} 字符 -> {path}")

    try:
        obj = json.loads(formatted)
        if isinstance(obj, dict):
            keys = [k for k in obj.keys() if k in {
                "sites", "lives", "parses", "rules", "spider", "wallpaper"}]
            print(f"  字段: {keys}")
            if "sites" in obj and isinstance(obj["sites"], list):
                print(f"  sites 数量: {len(obj['sites'])}")
    except Exception as e:
        dbg(f"预览解析失败: {e}")

    preview = "\n".join(formatted.split("\n")[:5])
    print(f"  预览:\n  {'~'*50}\n  " + preview.replace("\n", "\n  "))
    print(f"  {'~'*50}")

    return {
        "name": name,
        "status": status,
        "file": path,
        "ua": ua,
        "ok": status == "JSON",
        "note": _note_of(name),
        "bytes": len(formatted),
        "time_ms": elapsed_ms,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = []

    print("=" * 62)
    print(f"  TVBox 接口一键抓取  {ts}")
    print("=" * 62)

    for name, url in API_LIST:
        urls = API_MIRRORS.get(name, url)
        try:
            info = process(name, urls)
            summary.append(info)
        except TimeoutError as e:
            print(f"  ✗ 超时: {e}")
            summary.append({"name": name, "status": "TIMEOUT", "file": None, "ok": False})
        except Exception as e:
            print(f"  ✗ 全部失败: {e}")
            summary.append({"name": name, "status": "FAILED", "file": None, "ok": False})

    update_list_txt(summary, LIST_TXT)

    report = os.path.join(OUTPUT_DIR, "SUMMARY.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"TVBox 接口抓取报告  {ts}\n")
        f.write("=" * 62 + "\n\n")
        for it in summary:
            f.write(f"[{it['name']}] {it.get('ua','')}\n")
            f.write(f"  状态: {it['status']}\n")
            f.write(f"  文件: {it.get('file')}\n\n")

    print("\n" + "=" * 62)
    print("  汇总")
    print("=" * 62)
    for it in summary:
        icon = "✓" if it.get("ok") else "✗"
        print(f"  {icon} {it['name']:8s} | {it['status']:10s} | {it.get('file','')}")
    print(f"\n  报告: {report}")
    print(f"  更新日志: {LIST_TXT}")
    print("=" * 62)


# ======================================================================
# 自测
# ======================================================================
def selftest():
    print("\n" + "=" * 62)
    print("  自测：解密逻辑验证（离线，零第三方依赖）")
    print("=" * 62)

    plain = json.dumps({
        "sites": [{"key": "demo", "name": "测试源", "api": "http://x.com/api", "type": 1}],
        "parses": [], "rules": [], "spider": ""
    }, ensure_ascii=False)

    key_str = right_padding("mySecretKey123", "0", 16)
    ts = "1788447203629"
    iv_str = right_padding(ts, "0", 16)
    key_b = key_str.encode("utf-8")
    iv_b = iv_str.encode("utf-8")

    plain_bytes = plain.encode("utf-8")
    pad_len = 16 - (len(plain_bytes) % 16)
    ct = AES128._encrypt_cbc(plain_bytes + bytes([pad_len] * pad_len), key_b, iv_b)
    data_hex = binascii.hexlify(ct).decode("utf-8").lower()

    ts_hex = binascii.hexlify(ts.encode("utf-8")).decode("utf-8")
    payload_hex = "2423" + "mySecretKey123" + "2324" + data_hex + ts_hex

    print(f"\n[测试1] 构造 2423 hex形态 报文 (明文 {len(plain)} 字节)")
    result = find_result(payload_hex)
    parsed = json.loads(result)
    assert parsed["sites"][0]["key"] == "demo"
    print("  ✓ 2423 hex形态 解密正确")

    assert find_result('{"a":1}') == '{"a":1}'
    print("[测试2] ✓ 已是 JSON 直接返回")

    json_str = '{"sites":[],"hello":"世界"}'
    b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    png_head = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    marker = "TianShenIY**".encode("utf-8")
    raw = png_head + marker + b64.encode("utf-8")
    out = find_result("", _raw_bytes=raw)
    assert json.loads(out)["hello"] == "世界"
    print("[测试3] ✓ 图片伪装壳 + base64 解密正确")

    huge = "{" + "\n" * 30000 + '"k":1' + "\n" * 20000 + "}"
    assert json.loads(find_result(huge))["k"] == 1
    print("[测试4] ✓ collapse_whitespace 正常")

    mixed = json.dumps({"sites": [{"key": "a"}], "secret": "filtered",
                        "wallpaper": "http://x/y.jpg"}, ensure_ascii=False)
    filtered = json.loads(filter_json(mixed))
    assert "sites" in filtered and "wallpaper" in filtered
    assert "secret" not in filtered
    print("[测试5] ✓ filter_json 过滤非标准字段")

    # ★ 自测6：验证 ext 对象递归转换
    source_url = "https://example.com/path/to/config.png"
    test_json = json.dumps({
        "spider": "./spider.jar",
        "wallpaper": "https://wp.upx8.com/api.php",
        "sites": [
            {
                "key": "a",
                "api": "csp_Market",
                "ext": {
                    "json": "./lib/哔哩合集.png",
                    "cookie": "./lib/blc.png",
                    "site": ["http://tvpanpan.site", "./local.txt"]
                }
            },
            {"key": "b", "api": "http://example.com/api", "ext": "../icons/icon.png"}
        ],
        "lives": [{"name": "live1", "url": "./live.m3u"}],
        "parses": [{"name": "p1", "url": "./parse.js"}]
    }, ensure_ascii=False)
    resolved = json.loads(absolutize_json(test_json, source_url))
    base = "https://example.com/path/to/"
    assert resolved["spider"] == base + "spider.jar"
    assert resolved["wallpaper"] == "https://wp.upx8.com/api.php"
    assert resolved["sites"][0]["api"] == "csp_Market"
    # ext 对象内的相对路径
    assert resolved["sites"][0]["ext"]["json"] == base + "lib/哔哩合集.png"
    assert resolved["sites"][0]["ext"]["cookie"] == base + "lib/blc.png"
    # ext.site 数组中的相对路径
    assert resolved["sites"][0]["ext"]["site"][1] == base + "local.txt"
    # ext 为字符串
    assert resolved["sites"][1]["ext"] == "https://example.com/path/icons/icon.png"
    assert resolved["lives"][0]["url"] == base + "live.m3u"
    assert resolved["parses"][0]["url"] == base + "parse.js"
    print("[测试6] ✓ 相对→绝对地址转换正确（含 ext 对象递归 + 天神接口场景）")

    no_change = absolutize_json('{"spider":"./x.jar"}', "")
    assert json.loads(no_change)["spider"] == "./x.jar"
    print("[测试7] ✓ 无源 URL 时不修改")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        lp = os.path.join(tmp, "list.txt")
        with open(lp, "w", encoding="utf-8") as f:
            f.write("饭太硬.json|20260903\n")
            f.write("嗷呜.json|20260901\n")
        fake_results = [
            {"name": "饭太硬", "ok": True,  "bytes": 24576},
            {"name": "嗷呜",   "ok": False, "bytes": 0},
            {"name": "香雅情", "ok": True,  "bytes": 32768},
        ]
        update_list_txt(fake_results, lp)
        latest = load_list_txt(lp)
        assert latest["饭太硬.json"] == ("20260905", "24.0K"), latest["饭太硬.json"]
        assert latest["香雅情.json"] == ("20260905", "32.0K"), latest["香雅情.json"]
        assert latest["嗷呜.json"] == ("20260901", "-"), latest["嗷呜.json"]
        with open(lp, "r", encoding="utf-8") as f:
            content = f.read()
        assert "|" in content and "\t" not in content
        assert "24.0K" in content and "32.0K" in content
        print("[测试8] ✓ list.txt 插入式追加 + 体积列 + 失败沿用上次时间（分隔符=|）")

    print("\n" + "=" * 62)
    print("  全部自测通过 ✓")
    print("=" * 62)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
        print("\n完成! 按回车退出...")
        try:
            input()
        except EOFError:
            pass
