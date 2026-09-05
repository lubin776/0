#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描当前目录下的所有 .json 文件，自动生成 list.txt
格式: 文件名 | 更新时间(YYYYMMDD) | 字节数 | (备注留空)

用法:
    python3 gen_list.py            # 扫描当前目录
    python3 gen_list.py /path/to  # 扫描指定目录
"""
import os
import sys
from datetime import datetime

EXT = ".json"
NOTE_FILE = "_note.txt"  # 可选：同目录下的备注映射文件（文件名=备注）


def load_notes(directory):
    """读取可选备注文件，格式: 文件名=备注"""
    notes = {}
    note_path = os.path.join(directory, NOTE_FILE)
    if os.path.exists(note_path):
        with open(note_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    notes[k.strip()] = v.strip()
    return notes


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    directory = os.path.abspath(directory)
    notes = load_notes(directory)

    entries = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(EXT) or name == os.path.basename(__file__):
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        date = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        note = notes.get(name, "")
        entries.append(f"{name}|{date}|{size}|{note}")

    out = os.path.join(directory, "list.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")

    print(f"已生成: {out}")
    print(f"共 {len(entries)} 个 {EXT} 文件")


if __name__ == "__main__":
    main()
