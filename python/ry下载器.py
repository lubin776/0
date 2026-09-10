#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 批量解析器 —— 一键脚本
=================================
使用方式：改好下面「用户设置区」，然后 python3 tvbox_batch.py 即可，无需交互。

──────────────────────────────────
【用户设置区】只改这里 ↓
──────────────────────────────────
"""

# ========== ① 链接列表：一行一个，「名称, 链接」 ==========
# 说明：
#   - 名称在前，链接在后，英文逗号分隔
#   - 第一行链接会生成文件名：潇洒.json
#   - 第二行链接会生成文件名：菠菜.json
#   - 名称可省略（省略时自动用域名命名），逗号也可省略
#   - 以 # 开头为注释
#   - 支持 file:// 本地文件、raw:base64 内联，用来绕过 WAF

LINKS = [
    "潇洒下载, https://9877.kstore.space/single.json",
    "奇奇下载, http://bd.qiqiv.cn/666.json",
    "菠菜园下载, https://0.12yue.de5.net/tvbox/x/lib/菠菜园下载.json",
    "奇奇副本, https://0.12yue.de5.net/tvbox/x/lib/666.json",
    "柒豪下载, https://raw.gitcode.com/qihao/qihaoyyds/raw/main/版本.json",
    "天神下载, https://cdn.jsdelivr.net/gh/IY-CPU/IY@main/天神小屋.png",
    "应用市场二, https://cdn.jsdelivr.net/gh/woshishiq1/hipy-drpy2@main/wzxxcz/json/market.json",
    "应用市场一, https://cdn.jsdelivr.net/gh/SimonWang911/simonwangsub@main/appupdate/appupdate.json",
    # "本地测试, file:///data/workspace/test_data/single.json",   # 本地文件绕过 WAF
    # "内联, raw:W3sibmFtZSI6InRlc3QifV0=",                       # 内联 base64
    # "https://no-name.com/api.json",                             # 不写名称，自动用域名
]

# ========== ② 输出文件夹（结果保存到哪里） ==========
OUTPUT_DIR = "./ry"

# ========== ③ 名称里非法字符替换成这个（Windows 兼容） ==========
NAME_SAFE_CHAR = "_"

# ========== ④ 请求设置 ==========
REQUEST_TIMEOUT = 20
SSL_VERIFY = False      # 遇到自签证书设 False
DISABLE_WAF = False     # True = 跳过真实网络，配合下方 MOCK_RESPONSES 本地调试
ALLOW_HTTP_FALLBACK = True   # 请求失败时自动尝试 http://

# ========== ⑤ 本地调试用（DISABLE_WAF=True 时生效） ==========
# 键为链接里的关键字，值为模拟响应文本（可为 JSON 字符串或 base64 等伪装内容）
MOCK_RESPONSES = {
    "9877": '{"推荐":[{"name":"首页","url":"https://x.com/a.json"}],"本地包":[{"name":"v1","url":"https://x.com/b.json","version":"1.0"}]}',
    "example": '{"sites":[{"key":"abc","name":"测试","url":"https://example.com/source.json"}]}',
}

# ========== ⑥ 命令行参数（一般不需要改，可用 -o / -n 临时覆盖） ==========
# --out  输出文件夹        --name  名称（单链接时覆盖用）
# --waf  开启本地 mock 模式（等价于 DISABLE_WAF=True）

"""
──────────────────────────────────
【用户设置区】只改上面 ↑
──────────────────────────────────
下面是解析核心，一般不用动。
"""

import os
import re
import sys
import json
import base64
import binascii
import gzip
import time
import argparse
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("需要 requests: pip3 install requests")

# ================== UA 池 ==================
TVBOX_UAS = [
    "okhttp/3.15", "okhttp/4.9.3", "TVBox/1.0.0",
    "com.github.tvbox",
    "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)",
]
HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}


# ================== AES-128-CBC（纯标准库） ==================
class AES128:
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
    RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]

    @staticmethod
    def _sub_word(w):
        return (AES128.SBOX[(w>>24)&0xFF]<<24 | AES128.SBOX[(w>>16)&0xFF]<<16 |
                AES128.SBOX[(w>>8)&0xFF]<<8 | AES128.SBOX[w&0xFF])

    @staticmethod
    def _rot_word(w):
        return ((w<<8)&0xFFFFFFFF) | ((w>>24)&0xFF)

    @staticmethod
    def _expand_key(key):
        Nk,Nr = 4,10
        w=[0]*(4*(Nr+1))
        for i in range(Nk):
            w[i]=(key[4*i]<<24)|(key[4*i+1]<<16)|(key[4*i+2]<<8)|key[4*i+3]
        for i in range(Nk,4*(Nr+1)):
            temp=w[i-1]
            if i%Nk==0:
                temp=AES128._sub_word(AES128._rot_word(temp))^(AES128.RCON[i//Nk]<<24)
            w[i]=w[i-Nk]^temp
        out=bytearray(16*(Nr+1))
        for i in range(4*(Nr+1)):
            out[4*i]=(w[i]>>24)&0xFF; out[4*i+1]=(w[i]>>16)&0xFF
            out[4*i+2]=(w[i]>>8)&0xFF; out[4*i+3]=w[i]&0xFF
        return bytes(out)

    @staticmethod
    def _xtime(b):
        return ((b<<1)^(0x1B if b&0x80 else 0))&0xFF

    @staticmethod
    def _inv_sub_bytes(state):
        inv=[0]*256
        for i in range(256): inv[AES128.SBOX[i]]=i
        return bytes(inv[b] for b in state)

    @staticmethod
    def _inv_shift_rows(state):
        s=list(state)
        for row,shift in [(1,1),(2,2),(3,3)]:
            base=[s[row+4*c] for c in range(4)]
            base=base[-shift:]+base[:-shift]
            for c in range(4): s[row+4*c]=base[c]
        return bytes(s)

    @staticmethod
    def _inv_mix_columns(state):
        def mul(a,b):
            r=0
            while b:
                if b&1: r^=a
                a=AES128._xtime(a); b>>=1
            return r
        s=list(state)
        for c in range(4):
            i=4*c; a0,a1,a2,a3=s[i],s[i+1],s[i+2],s[i+3]
            s[i]=mul(a0,0x0e)^mul(a1,0x0b)^mul(a2,0x0d)^mul(a3,0x09)
            s[i+1]=mul(a0,0x09)^mul(a1,0x0e)^mul(a2,0x0b)^mul(a3,0x0d)
            s[i+2]=mul(a0,0x0d)^mul(a1,0x09)^mul(a2,0x0e)^mul(a3,0x0b)
            s[i+3]=mul(a0,0x0b)^mul(a1,0x0d)^mul(a2,0x09)^mul(a3,0x0e)
        return bytes(s)

    @staticmethod
    def _decrypt_block(block,rk):
        Nr=10; state=bytes(a^b for a,b in zip(block,rk[16*Nr:16*(Nr+1)]))
        for r in range(Nr-1,0,-1):
            state=AES128._inv_shift_rows(state)
            state=AES128._inv_sub_bytes(state)
            state=bytes(a^b for a,b in zip(state,rk[16*r:16*(r+1)]))
            state=AES128._inv_mix_columns(state)
        state=AES128._inv_shift_rows(state)
        state=AES128._inv_sub_bytes(state)
        state=bytes(a^b for a,b in zip(state,rk[0:16]))
        return state

    @staticmethod
    def decrypt_cbc(ciphertext,key,iv):
        assert len(key)==16 and len(iv)==16
        assert len(ciphertext)%16==0
        rk=AES128._expand_key(key)
        plain=bytearray(); prev=iv
        for i in range(0,len(ciphertext),16):
            decrypted=AES128._decrypt_block(ciphertext[i:i+16],rk)
            plain+=bytes(a^b for a,b in zip(decrypted,prev))
            prev=ciphertext[i:i+16]
        if plain:
            pad=plain[-1]
            if 1<=pad<=16 and len(plain)>=pad and all(b==pad for b in plain[-pad:]):
                plain=plain[:-pad]
        return bytes(plain).decode("utf-8",errors="replace")


# ================== 文本工具 ==================
def clean_json_comments(text):
    if not text: return text
    if text.startswith('\ufeff'): text=text[1:]
    lines=text.split('\n'); out=[]; in_block=False
    for line in lines:
        if in_block:
            if '*/' in line: in_block=False; line=line[line.index('*/')+2:]
            else: continue
        if '/*' in line:
            before,after=line.split('/*',1)
            if '*/' in after: line=before+after[after.index('*/')+2:]
            else: line=before; in_block=True
        if '//' in line:
            in_str=False; sc=None
            for i,ch in enumerate(line):
                if ch in ('"',"'") and (i==0 or line[i-1]!='\\'):
                    if not in_str: in_str=True; sc=ch
                    elif ch==sc: in_str=False
                elif ch=='/' and i+1<len(line) and line[i+1]=='/' and not in_str:
                    line=line[:i]; break
        if line.strip(): out.append(line)
    return '\n'.join(out)


def extract_json(text):
    if not text: return text
    text=clean_json_comments(text)
    start=next((i for i,ch in enumerate(text) if ch in '{['), -1)
    if start==-1: return text
    end=next((i for i in range(len(text)-1,-1,-1) if text[i] in '}]'), -1)
    if end<=start: return text
    jt=text[start:end+1]
    try: json.loads(jt); return jt
    except: return text


def find_result(raw_text, _raw_bytes=None, _depth=0):
    """递归解密/解混淆：base64、**壳、2423-AES、gzip，直到拿到 JSON"""
    if _depth>10: return raw_text
    if _raw_bytes is None and raw_text is not None:
        _raw_bytes=raw_text.encode("utf-8",errors="ignore")
    content=raw_text if raw_text is not None else ""
    if not content and _raw_bytes:
        content=_raw_bytes.decode("utf-8",errors="ignore")
    if content.strip().startswith(("{","[")):
        try: json.loads(content); return content
        except: pass

    # ** 壳 + base64
    star=None
    if _raw_bytes is not None:
        pos=_raw_bytes.find(b"**")
        if pos>=8: star=pos
    if star is not None:
        if _raw_bytes is not None:
            b64=bytes(b for b in _raw_bytes[star+2:] if b not in (0x09,0x0a,0x0d,0x20))
            try: return find_result(b64.decode("latin-1",errors="ignore"),_depth=_depth+1)
            except: pass

    stripped=re.sub(r"\s+","",content).strip()
    # 2423 AES
    if stripped.startswith("2423") and "2324" in stripped:
        try:
            i2324=stripped.index("2324")
            p_doll=stripped.index("$#"); p_sharp=stripped.index("#$")
            data_hex=re.sub(r"[^0-9a-fA-F]","",stripped[i2324+4:p_doll])
            if len(data_hex)%2: data_hex=data_hex[:-1]
            key=(stripped[p_doll+2:p_sharp]+"0"*16)[:16]
            iv=(stripped[-13:]+"0"*16)[:16]
            res=AES128.decrypt_cbc(bytes.fromhex(data_hex),key.encode("latin-1")[:16],iv.encode("latin-1")[:16])
            return find_result(res,_depth=_depth+1)
        except: pass
    # 纯 base64
    clean=re.sub(r"\s","",content)
    if re.match(r"^[A-Za-z0-9+/=]+$",clean) and len(clean)>50:
        try:
            d=base64.b64decode(clean+"==").decode("utf-8",errors="ignore")
            if d.strip().startswith(("{","[")): return find_result(d,_depth=_depth+1)
        except: pass
    # gzip
    if _raw_bytes is not None:
        try:
            d=gzip.decompress(_raw_bytes).decode("utf-8",errors="ignore")
            if d.strip().startswith(("{","[")): return find_result(d,_depth=_depth+1)
        except: pass
    return content


# ================== 解析入口 ==================
def parse_text(raw_bytes):
    """把原始响应字节 → 格式化 JSON 文本"""
    decrypted=find_result("",_raw_bytes=raw_bytes)
    extracted=extract_json(decrypted)
    try:
        obj=json.loads(extracted)
        return json.dumps(obj,ensure_ascii=False,indent=2), True
    except json.JSONDecodeError:
        return extracted, False


# ================== 网络 ==================
def _prepare_url(url):
    """IDN 域名处理"""
    if url.startswith("file://") or url.startswith("raw:"):
        return url
    try:
        p=urlparse(url)
        if p.netloc and any(ord(c)>127 for c in p.netloc):
            import idna
            netloc=idna.encode(p.netloc).decode("ascii")
            url=url.replace(p.netloc,netloc)
    except: pass
    return url


def fetch_url(url, ua=""):
    url=_prepare_url(url)
    if url.startswith("file://"):
        path=url[7:]
        if not os.path.exists(path): raise RuntimeError(f"本地文件不存在: {path}")
        with open(path,"rb") as f: return f.read()
    if url.startswith("raw:"):
        return base64.b64decode(url[4:]+"==")
    headers=dict(HEADERS_BASE)
    headers["User-Agent"]=ua or TVBOX_UAS[0]
    headers["X-Requested-With"]="com.iptvbox"
    r=requests.get(url,headers=headers,timeout=REQUEST_TIMEOUT,allow_redirects=True,verify=SSL_VERIFY)
    if r.status_code==200 and len(r.content)>20: return r.content
    raise RuntimeError(f"HTTP {r.status_code}")


def fetch_with_fallback(url):
    """带 http 降级 + UA 轮换；DISABLE_WAF 时用 mock"""
    if DISABLE_WAF:
        for k,v in MOCK_RESPONSES.items():
            if k in url:
                print(f"    [mock] 命中本地调试: {k}")
                return v.encode("utf-8"), "MOCK", url
        raise RuntimeError("DISABLE_WAF=True 但未匹配 MOCK_RESPONSES")

    last=None
    candidates=[url]
    if ALLOW_HTTP_FALLBACK and url.startswith("https://"):
        candidates.append("http://"+url[8:])
    for u in candidates:
        for ua in TVBOX_UAS:
            try:
                raw=fetch_url(u,ua)
                if raw.lstrip().startswith(b"<"):
                    # HTML 响应（可能是 WAF 拦截页），尝试下一个 UA
                    last=RuntimeError("返回 HTML，疑似 WAF 拦截")
                    continue
                return raw,ua,u
            except Exception as e:
                last=e; time.sleep(0.3)
    raise RuntimeError(f"全部失败: {last}")


# ================== 链接解析 ==================
def parse_link_entry(entry):
    """
    把一行配置解析成 (name, url)
    支持格式：
        潇洒, https://...
        潇洒,https://...
        https://...                    （无名称）
    """
    entry=entry.strip()
    if not entry or entry.startswith("#"):
        return None, None
    # 去掉两端引号
    entry=entry.strip().strip('"').strip("'").strip(",")
    if not entry:
        return None, None
    # 按第一个逗号切分
    if "," in entry:
        name,url=entry.split(",",1)
        name=name.strip().strip('"').strip("'")
        url=url.strip().strip('"').strip("'")
    else:
        url=entry
        name=""
    if not url:
        return None, None
    return name, url


def safe_name(name, fallback_host):
    """生成安全的文件名（不含扩展名）"""
    if not name:
        name=fallback_host or "unnamed"
    name=re.sub(r'[\\/:*?"<>|\x00-\x1f]', NAME_SAFE_CHAR, name)
    name=name.strip().strip(".")
    return name[:120] or "unnamed"


# ================== 主流程 ==================
def main():
    ap=argparse.ArgumentParser(description="TVBox 批量解析器")
    ap.add_argument("-o","--out",default=OUTPUT_DIR,help="输出文件夹")
    ap.add_argument("-n","--name",default="",help="单链接时覆盖文件名（不含扩展名）")
    ap.add_argument("-l","--links",default="",help="覆盖 LINKS：多个链接用 | 分隔，可用 file:// 或 raw:")
    ap.add_argument("--waf",action="store_true",help="开启本地 mock 模式（绕过 WAF）")
    args=ap.parse_args()

    out_dir=args.out
    disable_waf=args.waf or DISABLE_WAF

    # 组装链接列表
    entries=[]
    if args.links:
        for part in args.links.split("|"):
            part=part.strip()
            if part: entries.append(part)
    else:
        entries=list(LINKS)

    # 解析 (name, url)
    tasks=[]
    for ent in entries:
        name,url=parse_link_entry(ent)
        if url: tasks.append((name,url))

    if not tasks:
        print("⚠ 没有有效的链接。请在脚本头部「用户设置区」配置 LINKS。")
        sys.exit(1)

    os.makedirs(out_dir,exist_ok=True)
    print(f"📁 输出目录: {os.path.abspath(out_dir)}")
    print(f"🔗 共 {len(tasks)} 个链接\n")

    results=[]
    for idx,(name,url) in enumerate(tasks,1):
        # 单链接且命令行指定了 --name，覆盖
        use_name=args.name if (args.name and len(tasks)==1) else name
        host=urlparse(url).netloc or "local"
        fname=safe_name(use_name,host)+".json"

        print(f"[{idx}/{len(tasks)}] {use_name or '(自动命名)'} ← {url}")
        print(f"    → 输出: {fname}")

        try:
            raw,ua,used=fetch_with_fallback(url)
            print(f"    ✓ 下载 {len(raw)} 字节 (UA={ua.split('/')[0]})")
            if used!=url: print(f"    实际地址: {used}")
        except Exception as e:
            print(f"    ✗ 请求失败: {e}")
            print(f"    💡 提示: 若被 WAF 拦截，请先用浏览器/手机保存响应，")
            print(f"        再用 file:///path/to/saved.json 或 raw:<base64> 形式配置")
            results.append({"name":use_name or host,"url":url,"file":None,"ok":False,"error":str(e)})
            continue

        text,ok=parse_text(raw)
        out_path=os.path.join(out_dir,fname)
        with open(out_path,"w",encoding="utf-8") as f:
            f.write(text)

        if ok:
            try:
                obj=json.loads(text)
                if isinstance(obj,dict):
                    keys=list(obj.keys())
                    print(f"    ✓ 解析成功 · 字段: {keys}")
                else:
                    print(f"    ✓ 解析成功 · 数组，长度 {len(obj)}")
            except: pass
        else:
            print(f"    ⚠ 未能解析为 JSON，已保存原始文本")
        results.append({"name":use_name or host,"url":url,"file":out_path,"ok":ok})

    # 汇总
    print("\n"+"="*50)
    print("📊 汇总")
    print("="*50)
    ok_n=sum(1 for r in results if r["ok"])
    for r in results:
        tag="✓" if r["ok"] else "✗"
        nm=r["name"] or r["url"]
        extra=os.path.basename(r["file"]) if r["ok"] else r.get("error","")
        print(f"  {tag} {nm}  {extra}")
    print(f"\n  成功 {ok_n}/{len(results)}")
    print(f"  目录: {os.path.abspath(out_dir)}")

    # 写汇总文件
    summary_path=os.path.join(out_dir,"_summary.json")
    try:
        with open(summary_path,"w",encoding="utf-8") as f:
            json.dump({"time":time.strftime("%Y-%m-%d %H:%M:%S"),
                       "output_dir":os.path.abspath(out_dir),
                       "total":len(results),"success":ok_n,
                       "items":results},f,ensure_ascii=False,indent=2)
    except: pass

    sys.exit(0 if ok_n==len(results) else 2)


if __name__=="__main__":
    if not SSL_VERIFY:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except: pass
    main()
