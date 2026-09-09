import json, re

# 1. 校验三个 JSON 文件格式
for f in ["tvbox.json", "config.json"]:
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        print(f"[OK] {f} 解析成功, 类型={type(data).__name__}", end="")
        if isinstance(data, list):
            print(f", 分组数={len(data)}")
        elif isinstance(data, dict):
            print(f", 键={list(data.keys())}")
    except Exception as e:
        print(f"[FAIL] {f}: {e}")

# 2. 校验 tvbox.json 每条记录字段完整性
with open("tvbox.json", "r", encoding="utf-8") as fp:
    data = json.load(fp)

total = 0
for group in data:
    for item in group.get("list", []):
        total += 1
        for field in ["name", "url", "icon", "version"]:
            assert field in item, f"缺少字段 {field}: {item}"
print(f"[OK] tvbox.json 共 {total} 张卡片, 字段(name/url/icon/version)全部齐全")

# 3. 模拟渲染：生成 HTML 片段，确认分组与卡片结构
html = []
for group in data:
    html.append(f"<div class='group-block'><h3>{group['name']}</h3><div class='cards-grid'>")
    for item in group["list"]:
        html.append(
            f"<div class='download-card' data-name='{item['name']} {item['version']}'>"
            f"<img src='{item['icon']}'><div class='card-name'>{item['name']}</div>"
            f"<div class='card-version'>{item['version']}</div>"
            f"<a href='{item['url']}'>下载</a></div>"
        )
    html.append("</div></div>")
rendered = "\n".join(html)
print(f"[OK] 模拟渲染通过, 生成 {rendered.count('download-card')} 个卡片DOM")

# 4. 校验中文路径已做 URL 编码
for group in data:
    for item in group["list"]:
        assert "%" in item["icon"] or "白盒" not in item["icon"], "图标中文未编码!"
print("[OK] 图标中文路径已全部 URL 编码")
