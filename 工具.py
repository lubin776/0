#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 接口一键抓取工具（整合版）
======================================================================
整合「工具1」与「工具2」的优势：

  【来自工具1】稳健网络层
    - UA 伪装（TVBox 标识，避开浏览器响应）
    - 多 UA 轮询 + 镜像源重试（try_fetch_all）
    - requests / urllib 双兼容（零依赖兜底）

  【来自工具2】正确的 2423 AES-CBC 解密（能解天神IY）
    - 模拟 TVBox 官方 ApiConfig.FindResult() 运行环境
    - 2423 报文 = 整段 hex 编码（$#/#$/2423/2324 均为 hex）
    - 字节级 ** 标记搜索（兼容中文标记 TianShenIY**）
    - 递归剥壳（图片壳 → base64 → 2423 → JSON）

  【增强】filter_json / collapse_whitespace / selftest / --debug

零第三方依赖：AES-128-CBC + PKCS7 纯标准库手写（兼容 QPython）
运行：python tvbox_api.py                # 正常跑
      python tvbox_api.py --selftest     # 离线自测
      python tvbox_api.py --debug        # 开调试日志
输出：output/名称.json （固定文件名，直接覆盖）
======================================================================
"""

import re
import json
import base64
import os
import sys
import binascii
import gzip
from datetime import datetime

# ================== 网络层: 优先 requests, 兜底 urllib ==================
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

# ====================== 调试开关 ======================
DEBUG = "--debug" in sys.argv


def dbg(msg):
    if DEBUG:
        print(f"[DBG] {msg}")


# ======================================================================
# 纯 Python 标准库实现 AES-128-CBC + PKCS7（零依赖）
# ======================================================================
class AES128:
    """对标 TVBox AES.java：AES-128, CBC, PKCS7"""

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
        # 严格 PKCS7 去填充
        if len(plaintext) > 0:
            pad = plaintext[-1]
            if 1 <= pad <= 16 and len(plaintext) >= pad:
                if all(b == pad for b in plaintext[-pad:]):
                    plaintext = plaintext[:-pad]
        return bytes(plaintext).decode("utf-8", errors="replace")

    @staticmethod
    def _encrypt_block(block, rk):
        """仅供自测"""
        Nr = 10
        state = bytes(a ^ b for a, b in zip(block, rk[0:16]))
        for r in range(1, Nr):
            # 简化：仅用于自测，用查表版 SubBytes/ShiftRows/MixColumns
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
# 配置区
# ======================================================================
API_LIST = [
    ("肥猫",   "https://jk.catvod.site/"),
    ("少儿频道",   "https://0.12yue.de5.net/5/tv少儿.json"),
    ("饭太硬", "http://www.饭太硬.art/tv"),
    ("王二小", "http://tvbox.王二小放牛娃.top/"),
    ("天神IY", "https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/天神IY.png"),
]

# 镜像源（主链失败自动切换）【来自工具1】
API_MIRRORS = {
    "天神IY": [
        "https://cdn.jsdelivr.net/gh/IY-CPU/IY@main/天神IY.png",
        "https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/天神IY.png",
    ],
}

# TVBox 请求指纹池【整合工具1：完整 TVBox 身份，每组都带 X-Requested-With】
# 元素: (User-Agent, X-Requested-With)
#   X-Requested-With = 安卓 App 包名，是服务端区分「TVBox 客户端 / 浏览器」的核心校验项
#   很多配置编辑器(catvod)必须同时命中 UA + XRW 才返回接口 JSON，否则给 HTML 首页
TVBOX_UAS = [
    ("okhttp/3.15",                               "com.iptvbox"),
    ("okhttp/4.9.3",                               "com.iptvbox"),
    ("TVBox/1.0.0",                                "com.iptvbox"),
    ("com.github.tvbox",                           "com.iptvbox"),
    ("Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)", "com.iptvbox"),
    # 浏览器兜底：若服务端不区分 UA，用浏览器身份也能拿到 JSON
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", ""),
]

HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
}
OUTPUT_DIR = "output"
# ★ CI/本地输出目录分离（GitHub Actions 通过环境变量注入）
#   API_DIR  -> JSON 接口文件（CI 时 = api/）
#   USER_DIR -> 报告文件（CI 时 = user/）
#   本地直接运行时保持默认 "output"，全部输出到 output/
API_DIR = os.environ.get("TVBOX_API_DIR", OUTPUT_DIR)
USER_DIR = os.environ.get("TVBOX_USER_DIR", OUTPUT_DIR)
MAX_DEPTH = 5  # 递归剥壳最大深度
# ================================================


# ======================================================================
# 通用工具
# ======================================================================
def right_padding(s, ch, length):
    """Java StringUtils.rightPad：右侧补字符到指定长度"""
    if len(s) >= length:
        return s[:length]
    return s + (ch * (length - len(s)))


def is_json(text):
    if not text:
        return False
    t = text.strip()
    return t.startswith("{") or t.startswith("[")


def collapse_whitespace(text):
    """【用户建议】解密前先去掉几万换行/空格；无空白时直接返回（零开销）"""
    if text is None:
        return ""
    if not re.search(r"\s", text):
        return text
    return re.sub(r"\s+", " ", text).strip()


def format_json(text):
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except Exception:
        return text


def filter_json(text):
    """过滤 JSON：仅保留 TVBox 官方识别的顶层字段，去掉冗余/非标准内容"""
    try:
        obj = json.loads(text)
    except Exception:
        return text
    if not isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    keep = {"video", "sites", "lives", "parses", "rules",
            "spider", "wallpaper", "livePlayHeaders", "md5", "name", "homeSite",
            "homeLogo", "homeBg", "homeSearch", "homeRec", "searchable"}
    filtered = {k: v for k, v in obj.items() if k in keep}
    if not filtered:
        filtered = obj  # 没匹配到标准字段则保留原样
    return json.dumps(filtered, ensure_ascii=False, indent=2)


# ======================================================================
# 相对地址 → 绝对地址 转换
# ======================================================================
def get_base_url(source_url):
    """
    从源文件 URL 提取 base（目录部分），用于拼接相对路径。
    例：https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/天神IY.png
     →  https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/
    """
    if not source_url:
        return ""
    # 找到最后一个 '/' 的位置
    idx = source_url.rfind("/")
    if idx <= 0:
        return ""
    return source_url[:idx + 1]


def is_absolute_url(value):
    """判断是否为绝对地址（http/https/data: 开头等）"""
    if not isinstance(value, str):
        return True  # 非字符串不处理
    v = value.strip()
    if not v:
        return True  # 空字符串保持原样
    if v.startswith(("http://", "https://", "data:", "file://", "//")):
        return True
    return False


def resolve_url(rel_path, base_url):
    """
    将相对路径拼接为绝对地址。
    - 已经是绝对地址 → 原样返回
    - ./xxx 或 ../xxx → 基于 base 用 urljoin 正确解析
    - 纯文件名 → 拼到 base 后
    """
    if not rel_path or is_absolute_url(rel_path):
        return rel_path
    if not base_url:
        return rel_path
    from urllib.parse import urljoin
    return urljoin(base_url, rel_path)


def absolutize_json(text, source_url):
    """
    将 JSON 中的相对地址转为绝对地址。
    转换规则（基于 TVBox 配置结构）：
      - 顶层字段：spider, wallpaper → 转为绝对地址
      - sites[].ext, sites[].api, sites[].url → 转为绝对地址
      - lives[].url → 转为绝对地址
      - parses[].url → 转为绝对地址
    不会误转的字段：type, key, name, searchable 等非 URL 字符串
    """
    if not source_url:
        return text  # 无基准 URL 则不处理

    try:
        obj = json.loads(text)
    except Exception:
        return text  # 解析失败则不处理

    base = get_base_url(source_url)
    if not base:
        return text

    # ---- 顶层 URL 字段 ----
    top_url_fields = {"spider", "wallpaper", "homeLogo", "homeBg",
                      "homeSite", "livePlayHeaders"}
    if isinstance(obj, dict):
        for field in top_url_fields:
            if field in obj and isinstance(obj[field], str):
                obj[field] = resolve_url(obj[field], base)

        # ---- sites[] ----
        if "sites" in obj and isinstance(obj["sites"], list):
            for site in obj["sites"]:
                if not isinstance(site, dict):
                    continue
                # ext / jar / playUrl → 一定是 URL
                for field in ("ext", "jar", "playUrl"):
                    if field in site and isinstance(site[field], str):
                        site[field] = resolve_url(site[field], base)
                # api → 仅当值看起来像 URL（含 . 或 / 或 http）时才转换
                #      避免误转 csp_Market / csp_Xxx / json / xml 等 API 类型标识
                if "api" in site and isinstance(site["api"], str):
                    api_val = site["api"].strip()
                    if _looks_like_url(api_val):
                        site["api"] = resolve_url(api_val, base)

        # ---- lives[] ----
        if "lives" in obj and isinstance(obj["lives"], list):
            for live in obj["lives"]:
                if not isinstance(live, dict):
                    continue
                if "url" in live and isinstance(live["url"], str):
                    live["url"] = resolve_url(live["url"], base)

        # ---- parses[] ----
        if "parses" in obj and isinstance(obj["parses"], list):
            for parse in obj["parses"]:
                if not isinstance(parse, dict):
                    continue
                if "url" in parse and isinstance(parse["url"], str):
                    parse["url"] = resolve_url(parse["url"], base)

    return json.dumps(obj, ensure_ascii=False, indent=2)


def _looks_like_url(value):
    """判断值是否看起来像 URL（用于区分 api 字段的 URL vs 类型标识）"""
    if not value:
        return False
    if value.startswith(("http://", "https://", "//", "data:")):
        return True
    # 含 / 或含 .xxx 后缀（如 .com, .png, .jar）视为路径/URL
    if "/" in value:
        return True
    if "." in value and not value.startswith("."):
        # 形如 api.xxx.com / example.com/api
        parts = value.split(".")
        if len(parts) >= 2 and all(p for p in parts):
            return True
    return False


# ======================================================================
# ★ 核心：模拟 TVBox ApiConfig.FindResult()
#   支持双形态 2423 报文自动识别：
#     - 形态A（天神IY/工具2）：整段 hex 编码，$#/#$/2423/2324 均为 hex
#     - 形态B（工具1）：latin-1 明文，$#/#$ 为可见 ASCII
# ======================================================================
def _try_decrypt_2423_hex(stripped):
    """
    形态A：整段 hex 编码（对齐工具2 / 天神IY 真实样本）
    官方：data = substring(indexOf("2324")+4, length-26)
          content = new String(AES.toBytes(content))  // 整段 hex→bytes
          key = rightPadding(substring($#+2, #$), "0", 16)
          iv  = rightPadding(substring(length-13), "0", 16)
    """
    idx2423 = stripped.index("2423")
    idx2324 = stripped.index("2324")

    # key = "$#" 之后 ... "#$" 之前（hex 编码 → 解码得真正 key 字符串）
    key_hex = stripped[idx2423 + 4: idx2324]
    try:
        key_raw = bytes.fromhex(key_hex).decode("latin-1", errors="ignore")
    except Exception:
        key_raw = key_hex
    key_str = right_padding(key_raw, "0", 16)

    # 密文 = "#$" +4 ... 到 倒数第 26 hex 字符（= 13字节 iv + 13字节 ts）
    data_start = idx2324 + 4
    data_end = len(stripped) - 26
    if data_end <= data_start:
        raise ValueError("hex形态: data区间非法")
    data_hex = stripped[data_start: data_end]

    # IV = 报文末尾时间戳 ts：末 26 hex 字符 → 13 字节原始 ASCII → 右补"0"到16
    content_rstrip = stripped.rstrip()
    ts_hex = content_rstrip[len(content_rstrip) - 26:]   # 26 hex = 13 字节
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
    """
    形态B：latin-1 明文（对齐工具1）
    $# / #$ / 2423 / 2324 均为可见 ASCII
    """
    idx2324 = S.index("2324")
    p_doll = S.index("$#")
    p_sharp = S.index("#$")

    data_hex = S[idx2324 + 4: p_doll]
    data_hex = re.sub(r"[^0-9a-fA-F]", "", data_hex)
    if len(data_hex) % 2 != 0:
        data_hex = data_hex[:-1]

    key = right_padding(S[p_doll + 2: p_sharp], "0", 16)
    iv = right_padding(S[len(S) - 13:], "0", 16)   # 末13字节(ASCII)右补0到16

    key_bytes = key.encode("latin-1")[:16]
    iv_bytes = iv.encode("latin-1")[:16]
    cipher_bytes = bytes.fromhex(data_hex)

    return AES128.decrypt_cbc(cipher_bytes, key_bytes, iv_bytes)


def find_result(raw_text, _raw_bytes=None, _depth=0):
    """
    与 TVBox 安卓端 ApiConfig.FindResult() 等价。
    输入：原始响应文本 + 原始 bytes（用于字节级 ** 搜索）
    输出：解密后的明文 JSON 字符串
    """
    if _raw_bytes is None and raw_text is not None:
        _raw_bytes = raw_text.encode("utf-8", errors="ignore")

    content = raw_text if raw_text is not None else ""

    # ★ 修复：process() 常传 find_result("", _raw_bytes=raw)（为空以优先走字节级 ** 搜索）。
    #   若 content 为空但存在原始 bytes，需将其解码为文本，否则后续 ①is_json / ⑤gzip
    #   等文本分支全部失效 → 最终 return content='' → 写出 0 字节。
    #   （这正是肥猫/王二小/少儿频道「下载成功但0字符」的根因）
    if not content and _raw_bytes:
        content = _raw_bytes.decode("utf-8", errors="ignore")

    # ① 已经是 JSON 直接返回
    if is_json(content):
        dbg(f"find_result[{_depth}] 已是JSON, 直接返回")
        return content

    # ② 图片伪装壳：字节级搜索 ** 标记（兼容中文标记 TianShenIY**）
    star_idx = None
    if _raw_bytes is not None:
        pos = _raw_bytes.find(b"**")
        if pos >= 8:
            star_idx = pos
    if star_idx is None:
        m = re.search(r"[A-Za-z0-9]{8}\*\*", content)
        if m:
            star_idx = content.index(m.group()) + 10  # +10 跳过标记(8+2)

    if star_idx is not None:
        dbg(f"find_result[{_depth}] 发现 ** 标记 @ {star_idx}, 解base64")
        if _raw_bytes is not None:
            b64_bytes = _raw_bytes[star_idx + 2:]
            b64_bytes = bytes(b for b in b64_bytes if b not in (0x09, 0x0a, 0x0d, 0x20))
            try:
                decoded = base64.b64decode(b64_bytes + b"==").decode("utf-8", errors="ignore")
                return find_result(decoded, _depth=_depth + 1)  # 递归
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

    # ③ 2423 AES-CBC 自解密：双形态自动识别
    stripped = collapse_whitespace(content).strip()
    has_delim = "$#" in stripped and "#$" in stripped
    has_2423_structure = stripped.startswith("2423") and "2324" in stripped
    if stripped.startswith("2423") and (has_delim or has_2423_structure):
        dbg(f"find_result[{_depth}] 进入2423分支 (delim={has_delim}, struct={has_2423_structure}), 前缀={stripped[:20]!r}")
        last_err = None
        # 优先形态A（hex 编码，天神IY）
        try:
            result = _try_decrypt_2423_hex(stripped)
            dbg(f"2423 hex形态解密成功, 前缀={result[:40]!r}")
            return find_result(result, _depth=_depth + 1)  # 递归（可能嵌套多层）
        except Exception as e:
            dbg(f"hex形态失败({e}), 尝试明文形态")
            last_err = e
        # 兜底形态B（latin-1 明文）
        try:
            result = _try_decrypt_2423_plain(stripped)
            dbg(f"2423 明文形态解密成功, 前缀={result[:40]!r}")
            return find_result(result, _depth=_depth + 1)
        except Exception as e2:
            dbg(f"明文形态也失败: {e2}")
            raise RuntimeError(f"2423 双形态均解密失败: hex={last_err} / plain={e2}")

    # ④ 纯 base64 兜底
    clean = re.sub(r"\s", "", content)
    if re.match(r"^[A-Za-z0-9+/=]+$", clean) and len(clean) > 50:
        try:
            decoded = base64.b64decode(clean + "==").decode("utf-8", errors="ignore")
            if is_json(decoded):
                return decoded
        except Exception:
            pass

    # ⑤ gzip 兜底
    if _raw_bytes is not None:
        try:
            decompressed = gzip.decompress(_raw_bytes).decode("utf-8", errors="ignore")
            if is_json(decompressed):
                return decompressed
        except Exception:
            pass

    return content


# ======================================================================
# 网络请求（【来自工具1】稳健版：UA 轮询 + 镜像重试 + requests/urllib 双兼容）
# ======================================================================
def fetch_url(url, ua, xrw=""):
    headers = dict(HEADERS_BASE)
    headers["User-Agent"] = ua
    if xrw:  # ★ 关键：安卓包名，服务端据此识别 TVBox 客户端（来自工具1）
        headers["X-Requested-With"] = xrw
    if HAVE_REQUESTS:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True, verify=False)
        if r.status_code == 200 and len(r.content) > 20:
            return r.content
        raise RuntimeError(f"HTTP {r.status_code}")
    elif HAVE_URLLIB:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=20) as resp:
            data = resp.read()
            if len(data) > 20:
                return data
            raise RuntimeError("empty body")
    else:
        raise RuntimeError("无可用网络库(requests/urllib 均不可用)")


def try_fetch(url):
    """单个 URL：多 UA 轮询 + 智能判定（来自工具1）

    「返回 JSON=接口 / 返回 HTML=被当成浏览器」才认定成功；
    HTML 说明该 UA 身份未被识别，继续试下一组 UA。
    每组 UA 失败重试一次，应对服务端简单反爬（首次返回 HTML）。
    """
    last_err = None
    for ua, xrw in TVBOX_UAS:
        for _attempt in range(2):  # 每组重试一次
            try:
                raw = fetch_url(url, ua, xrw)
                # ★ 智能判定：HTML 首页 = 未识别为 TVBox，换下一组 UA
                if raw.lstrip().startswith(b"<"):
                    dbg(f"{url} UA={ua} 拿到HTML首页, 轮询下一组")
                    break
                return raw, ua
            except Exception as e:
                last_err = e
                dbg(f"{url} UA={ua} XRW={xrw} 失败: {e}")
    raise RuntimeError(str(last_err))


def try_fetch_all(urls):
    """多个 URL（含镜像）：任一成功即返回 (raw, ua, used_url)"""
    errs = []
    for u in urls:
        try:
            raw, ua = try_fetch(u)
            return raw, ua, u
        except Exception as e:
            errs.append(f"{u} -> {e}")
    raise RuntimeError(" | ".join(errs))


# ======================================================================
# 主流程
# ======================================================================
def process(name, urls) -> dict:
    if isinstance(urls, str):
        urls = [urls]
    print(f"\n▶ [{name}] 尝试 {len(urls)} 个源")
    raw, ua, used_url = try_fetch_all(urls)
    print(f"  ✓ 下载成功 ({len(raw)} 字节, UA={ua})")
    print(f"  源地址: {used_url}")

    # ★ 核心：模拟 TVBox FindResult 解密（传入原始 bytes 支持字节级 ** 搜索）
    decrypted = find_result("", _raw_bytes=raw)

    # 过滤 + 格式化 JSON
    try:
        formatted = filter_json(decrypted)
        status = "JSON"
    except Exception as e:
        formatted = decrypted
        status = f"TEXT"

    # ★ 相对地址 → 绝对地址（基于源 URL 拼接）
    if status == "JSON":
        formatted = absolutize_json(formatted, used_url)

    # 固定文件名输出（JSON 接口 -> API_DIR，可由环境变量指定，CI 时=api/）
    os.makedirs(API_DIR, exist_ok=True)
    safe = re.sub(r"[^\w\u4e00-\u9fff]", "_", name)
    path = os.path.join(API_DIR, f"{safe}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(formatted)

    # 输出统计
    print(f"  ✓ {status} | {len(formatted)} 字符 -> {path}")
    try:
        obj = json.loads(formatted)
        if isinstance(obj, dict):
            keys = [k for k in obj.keys() if k in {
                "sites", "lives", "parses", "rules", "spider", "wallpaper"}]
            print(f"  字段: {keys}")
            if "sites" in obj and isinstance(obj["sites"], list):
                print(f"  sites 数量: {len(obj['sites'])}")
    except Exception:
        pass
    preview = "\n".join(formatted.split("\n")[:5])
    print(f"  预览:\n  {'~'*50}\n  " + preview.replace("\n", "\n  "))
    print(f"  {'~'*50}")
    return {"name": name, "status": status, "file": path, "ua": ua}


def main():
    os.makedirs(API_DIR, exist_ok=True)
    os.makedirs(USER_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = []

    print("=" * 62)
    print(f"  TVBox 接口一键抓取（整合版）  {ts}")
    print(f"  输出: JSON->{API_DIR}/  报告->{USER_DIR}/")
    print("=" * 62)

    for name, url in API_LIST:
        urls = API_MIRRORS.get(name, url)
        try:
            info = process(name, urls)
            summary.append(info)
        except Exception as e:
            print(f"  ✗ 全部失败: {e}")
            summary.append({"name": name, "status": "FAILED", "file": None})

    # 汇总报告（报告 -> USER_DIR，可由环境变量指定，CI 时=user/）
    report = os.path.join(USER_DIR, "SUMMARY.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"TVBox 接口抓取报告  {ts}\n")
        f.write("=" * 62 + "\n\n")
        for it in summary:
            f.write(f"[{it['name']}] {it.get('ua','')}\n  状态: {it['status']}\n  文件: {it.get('file')}\n\n")

    print("\n" + "=" * 62)
    print("  汇总")
    print("=" * 62)
    for it in summary:
        icon = "✓" if it["status"] == "JSON" else "✗"
        print(f"  {icon} {it['name']:8s} | {it['status']:10s} | {it.get('file','')}")
    print(f"\n  报告: {report}")
    print("=" * 62)


# ======================================================================
# 自测（离线验证解密逻辑，零依赖）【来自工具2】
# ======================================================================
def selftest():
    print("\n" + "=" * 62)
    print("  自测：模拟 TVBox 官方解密逻辑（离线，零第三方依赖）")
    print("=" * 62)

    plain = json.dumps({
        "sites": [{"key": "demo", "name": "测试源", "api": "http://x.com/api", "type": 1}],
        "parses": [], "rules": [], "spider": ""
    }, ensure_ascii=False)

    key_str = right_padding("mySecretKey123", "0", 16)
    ts = "1788447203629"   # 13 字节时间戳
    iv_str = right_padding(ts, "0", 16)
    key_b = key_str.encode("utf-8")
    iv_b = iv_str.encode("utf-8")

    # 用自带 AES 加密 + PKCS7
    plain_bytes = plain.encode("utf-8")
    pad_len = 16 - (len(plain_bytes) % 16)
    ct = AES128._encrypt_cbc(plain_bytes + bytes([pad_len] * pad_len), key_b, iv_b)
    data_hex = binascii.hexlify(ct).decode("utf-8").lower()

    # 组装【形态A hex】报文：2423 [key] 2324 [cipher_hex] [ts_hex(26字符)]
    ts_hex = binascii.hexlify(ts.encode("utf-8")).decode("utf-8")
    payload_hex = "2423" + "mySecretKey123" + "2324" + data_hex + ts_hex

    print(f"\n[测试1] 构造 2423 hex形态 报文 (明文 {len(plain)} 字节)")
    print(f"  payload 前缀: {payload_hex[:60]}...")

    result = find_result(payload_hex)
    print(f"\n[测试1] 解密结果前缀: {result[:120]}")
    parsed = json.loads(result)
    assert parsed["sites"][0]["key"] == "demo"
    print("  ✓ sites 解析正确，key=demo")

    # 测试2：已是 JSON 直接返回
    assert find_result('{"a":1}') == '{"a":1}'
    print("\n[测试2] ✓ 已是 JSON 直接返回")

    # 测试3：图片伪装壳 + base64（中文标记，考验字节级 ** 搜索）
    json_str = '{"sites":[],"hello":"世界"}'
    b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    png_head = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    marker = "TianShenIY**".encode("utf-8")
    raw = png_head + marker + b64.encode("utf-8")
    out = find_result("", _raw_bytes=raw)
    assert json.loads(out)["hello"] == "世界"
    print("[测试3] ✓ 图片伪装壳 (中文标记+base64) 解密正确")

    # 测试4：collapse_whitespace 去几万换行
    huge = "{" + "\n" * 30000 + '"k":1' + "\n" * 20000 + "}"
    assert json.loads(find_result(huge))["k"] == 1
    print("[测试4] ✓ collapse_whitespace 处理几万换行正常")

    # 测试5：filter_json 仅保留 TVBox 标准字段
    mixed = json.dumps({"sites": [{"key": "a"}], "secret_internal": "should_be_filtered",
                        "wallpaper": "http://x/y.jpg"}, ensure_ascii=False)
    filtered = json.loads(filter_json(mixed))
    assert "sites" in filtered and "wallpaper" in filtered
    assert "secret_internal" not in filtered
    print("[测试5] ✓ filter_json 过滤非标准字段")

    # 测试6：absolutize_json 相对地址 → 绝对地址
    source_url = "https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/天神IY.png"
    tianshen_json = json.dumps({
        "spider": "./spider.jar",
        "wallpaper": "https://wp.upx8.com/api.php",
        "sites": [
            {
                "key": "版本信息",
                "name": "🌹天神｜小屋",
                "type": 3,
                "api": "csp_Market",
                "ext": "./天神小屋.png"
            },
            {
                "key": "site2",
                "name": "正常源",
                "type": 1,
                "api": "http://example.com/api",
                "ext": "../icons/icon.png"
            }
        ],
        "lives": [{"name": "live1", "url": "./live.m3u"}],
        "parses": [{"name": "p1", "url": "./parse.js"}]
    }, ensure_ascii=False)

    resolved = json.loads(absolutize_json(tianshen_json, source_url))
    expected_base = "https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/main/"

    assert resolved["spider"] == expected_base + "spider.jar", \
        f"spider 转换失败: {resolved['spider']}"
    assert resolved["wallpaper"] == "https://wp.upx8.com/api.php", \
        f"wallpaper 不应被修改: {resolved['wallpaper']}"
    # ★ api=csp_Market 是类型标识 → 不转
    assert resolved["sites"][0]["api"] == "csp_Market", \
        f"api 类型标识不应被转: {resolved['sites'][0]['api']}"
    # ★ ext 是 URL → 转绝对
    assert resolved["sites"][0]["ext"] == expected_base + "天神小屋.png", \
        f"sites[0].ext 转换失败: {resolved['sites'][0]['ext']}"
    # ../icons/icon.png 经 urljoin 解析 → 上一级目录（标准 URL 行为）
    assert resolved["sites"][1]["ext"] == "https://gh-proxy.com/raw.githubusercontent.com/IY-CPU/IY/icons/icon.png", \
        f"sites[1].ext 转换失败: {resolved['sites'][1]['ext']}"
    assert resolved["lives"][0]["url"] == expected_base + "live.m3u", \
        f"lives[0].url 转换失败: {resolved['lives'][0]['url']}"
    assert resolved["parses"][0]["url"] == expected_base + "parse.js", \
        f"parses[0].url 转换失败: {resolved['parses'][0]['url']}"
    print("[测试6] ✓ absolutize_json 相对→绝对地址转换正确")
    print(f"        spider:   {resolved['spider']}")
    print(f"        wallpaper: {resolved['wallpaper']}")
    print(f"        ext:       {resolved['sites'][0]['ext']}")
    print(f"        api[0]:    {resolved['sites'][0]['api']} (类型标识,不转)")

    # 测试7：空 base_url 时不处理
    no_change = absolutize_json('{"spider":"./x.jar"}', "")
    assert json.loads(no_change)["spider"] == "./x.jar"
    print("[测试7] ✓ 无源 URL 时不修改（保持原样）")

    print("\n" + "=" * 62)
    print("  全部自测通过 ✓ 解密 + 地址转换 与 TVBox 官方一致（零依赖）")
    print("=" * 62)


def apply_ci_env():
    """CI 模式：JSON 输出到 api/，报告输出到 user/（可被环境变量覆盖）"""
    global API_DIR, USER_DIR
    API_DIR = os.environ.get("TVBOX_API_DIR", "api")
    USER_DIR = os.environ.get("TVBOX_USER_DIR", "user")


if __name__ == "__main__":
    if "--ci" in sys.argv:
        apply_ci_env()
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
