"""
gen_list.py - 扫描当前目录的 .json 文件,自动生成 list.txt
用法: python gen_list.py > list.txt
       或直接把这段逻辑集成到你的解析工具里,每次解析完自动更新 list.txt
"""
import os
import json
from datetime import datetime

def gen_list(directory=".", output="list.txt"):
    lines = ["# 格式: 文件名 | 更新时间(YYYYMMDD) | 大小(字节) | 备注"]
    for f in sorted(os.listdir(directory)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(directory, f)
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y%m%d")
        note = ""
        # 尝试从 json 里读 name 字段作为备注
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            note = data.get("name", "")
        except Exception:
            pass
        lines.append(f"{f}|{mtime}|{size}|{note}")
    with open(output, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    gen_list()
