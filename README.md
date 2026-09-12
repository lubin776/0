# TVBox 接口搬运备份站

> 一个集「接口备份解析」+「静态展示站点」+「CI/CD 自动更新」于一体的完整项目。
>
> **核心能力**：自动抓取 TVBox 接口线路与下载资源，解析后通过静态站点展示，全部过程由 GitHub Actions 定时驱动，无需人工维护。
┌─ 直播条目 ─────────────────────────────────────────┐
│  标题 + 时间                                       │
│                                                    │
│  ┌────────────────────────────────────────────────┐ │
│  │ 王二小二线  原始线路      ← 标签（和备份一线同级）│ │
│  │ ua: bingcha/1.1 (...)    ← UA独占一行           │ │
│  │ https://xxx...        复制 ← URL+复制占第二行    │ │
│  └────────────────────────────────────────────────┘ │
│                                                    │
│  ┌────────────────────────────────────────────────┐ │
│  │ 📦备份一线  https://...  复制                    │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ 📦备份二线  https://...  复制                    │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ 📦备份三线  https://...  复制                    │ │
│  └────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘

---

## 📑 目录

- [项目简介](#项目简介)
- [整体架构](#整体架构)
- [仓库目录结构](#仓库目录结构)
- [快速开始](#快速开始)
- [模块一：静态展示站点](#模块一静态展示站点)
- [模块二：双脚本自动化](#模块二双脚本自动化)
- [模块三：GitHub Actions 工作流](#模块三github-actions-工作流)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 项目简介

本项目解决三个核心问题：

| 问题 | 解决方案 |
|------|---------|
| **接口线路经常失效** | 多镜像自动选通 + 定时备份，始终有可用线路 |
| **下载资源分散难找** | 统一抓取、分类展示，一键复制/下载 |
| **手动维护成本高** | GitHub Actions 全自动运行，commit 回仓库 |

**技术栈**：Python（数据抓取） + 原生 HTML/CSS/JS（前端展示） + GitHub Actions（CI/CD）

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub 仓库 (main 分支)                    │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  工作流 A（每日）  │         │ 工作流 B（每两日） │          │
│  │  ry下载器.py      │         │ tvbox_get_api.py │          │
│  │  → ry/           │         │ → tvbox/          │          │
│  │                   │         │ → list.txt        │          │
│  └────────┬──────────┘         └────────┬──────────┘          │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌─────────────────────────────────────────────┐             │
│  │              config.json (下载源)             │             │
│  │              index.html (静态站点)            │             │
│  │              list.txt (接口清单)             │             │
│  └─────────────────────────────────────────────┘             │
│                          │                                   │
│                          ▼ (GitHub Pages / 直链访问)          │
│  ┌─────────────────────────────────────────────┐             │
│  │          用户浏览器（简洁版/全能版）          │             │
│  └─────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

**数据流**：

```
原始接口/下载源 → [Python 脚本解析] → 产物文件 (ry/ tvbox/ list.txt)
                                    ↓
                              [Git Commit] → 仓库更新
                                    ↓
                              [静态站点读取] → 用户访问展示
```

---

## 仓库目录结构

```
你的仓库/
│
├── .github/
│   └── workflows/
│       ├── daily-ry-parser.yml          ← 工作流A：每日解析 ry
│       └── every-2days-tvbox-api.yml    ← 工作流B：每两日抓取 tvbox
│
├── python/                               ← 脚本统一目录
│   ├── ry下载器.py                       ← 脚本A：下载资源解析
│   └── tvbox_get_api.py                  ← 脚本B：接口线路抓取
│
├── rylinks.txt                           ← 脚本A 配置（名称+URL，文本格式）
├── tvboxapilinks.txt                     ← 脚本B 配置（API_LIST+API_MIRRORS，JSON）
│
├── ry/                                   ← 脚本A 产物（自动生成）
├── tvbox/                                ← 脚本B 产物（自动生成）
├── list.txt                              ← 脚本B 产物（接口清单）
├── SUMMARY.txt                           ← 脚本B 产物（运行摘要）
│
├── index.html                            ← ⭐ 静态站点（整体版单文件）
├── config.json                           ← ⭐ 站点配置（仅下载外延逻辑）
├── style.css                             ← 站点样式（如已分离）
├── js/                                   ← 站点 JS 模块（如已分离）
│
└── README.md                             ← 本文件
```

> **约定**：所有相对路径均相对于**仓库根目录**。工作流通过 `working-directory: ${{ github.workspace }}` 锁定 CWD = 仓库根。

---

## 快速开始

### 方案一：纯静态站点（最快上手）

只需 3 个文件即可运行：

```bash
# 1. 准备文件
index.html          # 主页面
config.json         # 下载源配置
list.txt            # 接口清单（一行一个接口名）

# 2. 本地预览
python3 -m http.server 8080
# → 访问 http://localhost:8080
```

`list.txt` 格式示例：
```
饭太硬
南风
菠菜园
更新专用接口
```

`config.json` 格式（仅需 `downloadSources`）：
```json
{
  "downloadSources": [
    { "name": "菠菜园", "url": "菠菜园下载.json", "description": "整理者：误道者" },
    { "name": "无忧", "url": "ry/无忧下载.json", "description": "云星" }
  ]
}
```

### 方案二：完整自动化（推荐）

```bash
# 1. 克隆仓库
git clone <你的仓库>
cd <仓库>

# 2. 本地验证双脚本
python3 python/ry下载器.py --debug
python3 python/tvbox_get_api.py --check-config

# 3. 推送后 GitHub Actions 自动运行
git push origin main
```

---

## 模块一：静态展示站点

### 页面结构

| 模式 | 说明 | 默认 |
|------|------|------|
| **简洁版** | 仅显示接口列表，无导航栏 | ✅ 默认 |
| **全能版** | 含导航栏，三分页（接口/下载/关于） | 手动切换 |

### 三分页模块

```
┌─────────────────────────────────┐
│  [Logo] 海量接口搬运备份         │ ← 头部：标题行
│  备用数据源，防屏不迷路          │ ← 小字第一行
│  QQ交流群：1067685939           │ ← 小字第二行
├─────────────────────────────────┤
│  🔍 搜索...                     │ ← 搜索框
├─────────────────────────────────┤
│  [接口] [下载] [关于]            │ ← 导航栏（全能版）
├─────────────────────────────────┤
│                                 │
│  分页1：接口列表                 │
│  ┌───────────────────────────┐  │
│  │ ● 饭太硬                   │  │
│  │   备份时间 2026年09月10日   │  │
│  │   [原始线路] [备份一二三线]  │  │
│  └───────────────────────────┘  │
│                                 │
│  分页2：下载资源                 │
│  分页3：关于本站                 │
│                                 │
├─────────────────────────────────┤
│  © 2026 TVBox 备份站 | QQ群...  │ ← Footer（始终贴底）
└─────────────────────────────────┘
```

### 接口列表渲染规则

每个接口条目显示：
- **名称**（权重排序，权重小的靠前）
- **备份时间**（2天内=绿色，超2天=橙色）
- **原始线路** + **三个备份镜像**（自动补 `.json` 后缀）
- **复制按钮**（一键复制 URL）

### 配置驱动原则

| 内容 | 来源 |
|------|------|
| 标题、Logo、副标题、Footer | ✅ 写死在 HTML（便于 SEO/首屏） |
| 导航标签、API 域名、权重排序 | ✅ 写死在 JS 常量 |
| **下载资源源列表** | ✅ **仅此部分从 `config.json` 动态加载** |

> 设计理念：`config.json` 只管「下载外延逻辑」，改下载源无需动 HTML。

### Footer 置底实现

采用 **Flexbox Sticky Footer** 方案：

```css
body { min-height: 100vh; display: flex; flex-direction: column; }
.container { flex: 1; display: flex; flex-direction: column; }
.main-card { flex: 1; }          /* 内容区自动撑开 */
.page-footer { flex-shrink: 0; }  /* 防止被压缩 */
```

效果：内容少时 footer 贴视窗底，内容多时随内容下推。

---

## 模块二：双脚本自动化

### 脚本 A：`ry下载器.py`

**职责**：批量下载「本地包/下载资源」类接口（菠菜园下载、潇洒下载等），解析 JSON，落到 `ry/`。

**配置**（`rylinks.txt`，仓库根）：
```
# 名称, 链接（英文逗号分隔；# 开头为注释）
潇洒下载, https://9877.kstore.space/single.json
菠菜园下载, https://0.12yue.de5.net/tvbox/x/lib/菠菜园下载.json

# 省略名称时自动用域名命名
https://no-name.com/api.json
```

**运行**：
```bash
python3 python/ry下载器.py
python3 python/ry下载器.py -l "https://example.com/api.json" --name 测试  # 单链接调试
```

### 脚本 B：`tvbox_get_api.py`

**职责**：抓取 TVBox 接口线路（饭太硬、嗷呜、肥猫等 90+ 线路），每线路多镜像自动选通，生成 `tvbox/*.json` + `list.txt` + `SUMMARY.txt`。

**配置**（`tvboxapilinks.txt`，仓库根，JSON）：
```json
{
  "API_LIST": [
    ["饭太硬", "http://www.饭太硬.net/tv"],
    ["嗷呜", "http://www.英格里希嗷呜.top/tv"]
  ],
  "API_MIRRORS": {
    "饭太硬": [
      "http://www.饭太硬.net/tv",
      "http://www.饭太硬.cc/tv"
    ]
  }
}
```

**运行**：
```bash
python3 python/tvbox_get_api.py --check-config   # 先校验配置
python3 python/tvbox_get_api.py --debug          # 调试模式
```

### 配置加载优先级（脚本 B）

```
1. 命令行 --config 指定路径（最高）
2. 仓库根/tvboxapilinks.txt（默认，推荐）
3. 兼容旧名：仓库根/api_list.json
4. 兼容旧式 Python 模块：api_list.py（兜底）
```

找不到任何配置时使用空列表（不崩溃）。

---

## 模块三：GitHub Actions 工作流

### 工作流 A：`daily-ry-parser.yml`

| 属性 | 值 |
|------|-----|
| **触发** | 每天 UTC 17:00（北京次日 01:00） |
| **手动** | ✅ 支持 `workflow_dispatch` |
| **脚本** | `python/ry下载器.py` |
| **配置** | `rylinks.txt` |
| **产物** | `ry/`（强制覆盖） |
| **提交** | `git add ry/ rylinks.txt` |

### 工作流 B：`every-2days-tvbox-api.yml`

| 属性 | 值 |
|------|-----|
| **触发** | 每天 UTC 16:05（北京次日 00:05），**奇偶日 gate 实现每两日** |
| **手动** | ✅ 支持 `workflow_dispatch`（**不受奇偶日限制**） |
| **脚本** | `python/tvbox_get_api.py` |
| **配置** | `tvboxapilinks.txt` |
| **产物** | `tvbox/` + `list.txt` + `SUMMARY.txt` |
| **提交** | `git add tvbox/ list.txt SUMMARY.txt tvboxapilinks.txt` |

### 协作矩阵

| 维度 | 工作流 A（ry） | 工作流 B（tvbox） |
|------|---------------|------------------|
| 频率 | 每天 | 每两日（奇偶日） |
| 产物目录 | `ry/` | `tvbox/` |
| 配置 | `rylinks.txt` | `tvboxapilinks.txt` |
| 共享锁 | `tvbox-repo-write` | `tvbox-repo-write` |

### 关键设计

**1. 共享锁防止 push 冲突**
```yaml
concurrency:
  group: tvbox-repo-write
  cancel-in-progress: false
```

**2. 强制覆盖保证干净**
```yaml
- name: 清空旧产物
  run: |
    rm -rf ry
    mkdir ry
```

**3. Rebase 后再 push**
```yaml
git pull --rebase --autostash origin "${GITHUB_REF_NAME}"
git push origin "HEAD:${GITHUB_REF_NAME}"
```

**4. 只提交自己负责的产物**（避免互相覆盖）
```yaml
# 工作流 A
git add ry/ rylinks.txt

# 工作流 B
git add tvbox/ list.txt SUMMARY.txt tvboxapilinks.txt
```

### Cron 时间换算

| 北京时间 | UTC | Cron |
|---------|-----|------|
| 每日 01:00 | 前一日 17:00 | `0 17 * * *` |
| 每日 00:05 | 前一日 16:05 | `5 16 * * *` |

公式：**UTC = 北京时间 − 8 小时**（注意跨日）

---

## 配置说明

### 修改速查表

| 想做什么 | 改哪里 | 重新部署 |
|---------|--------|---------|
| 增删下载链接 | `config.json` 的 `downloadSources` | ❌ 自动 |
| 增删 ry 源 | 编辑 `rylinks.txt` | ❌ 自动 |
| 增删接口线路 | 编辑 `tvboxapilinks.txt` 的 `API_LIST` | ❌ 自动 |
| 调整镜像 | 编辑 `tvboxapilinks.txt` 的 `API_MIRRORS` | ❌ 自动 |
| 改站点标题/Logo | 编辑 `index.html` | ✅ push 后 |
| 改调度时间 | 工作流 yml 的 `cron` | ✅ push 后 |
| 改每 N 天运行 | 改 gate 判断（如 `% 3`） | ✅ push 后 |

### 站点配置示例（`config.json`）

```json
{
  "downloadSources": [
    { "name": "菠菜园",   "url": "菠菜园下载.json",     "description": "整理者：误道者" },
    { "name": "奇奇副本", "url": "ry/奇奇副本.json",    "description": "整理者：误道者" },
    { "name": "无忧",     "url": "ry/无忧下载.json",    "description": "云星" },
    { "name": "潇洒",     "url": "ry/潇洒下载.json",    "description": "潇洒" },
    { "name": "柒豪下载", "url": "ry/柒豪下载.json",    "description": "" },
    { "name": "应用下载", "url": "ry/应用市场二.json",  "description": "" },
    { "name": "应用市场", "url": "ry/应用市场一.json",  "description": "" }
  ]
}
```

> `url` 支持子目录路径（如 `ry/xxx.json`），脚本原样 fetch。

---

## 常见问题

### Q1：站点打开 footer 不在底部？
→ 确保 `index.html` 包含完整的 flex 置底规则（`body` / `.container` / `.main-card` / `.page-footer` 四件套）。关于页内容少时也能贴底。

### Q2：Actions 页面看不到某个工作流？
→ 检查 `.github/workflows/` 下是否**两个独立 `.yml` 文件**。两个工作流写在同一文件里只会识别第一个。

### Q3：本地能跑，Actions 跑不动（网络超时）？
→ Runner 网络对国内域名不稳定属正常，脚本有重试。可加大 `REQUEST_TIMEOUT` 或换镜像。

### Q4：两个工作流并发 push 冲突？
→ 已配共享锁 `tvbox-repo-write`，自动排队串行。偶发失败可手动重跑。

### Q5：如何立即补跑（不等定时）？
→ Actions → 点工作流 → 右上角 **Run workflow** → 选 `main` → 触发。脚本B 手动触发不受奇偶日限制。

### Q6：下载页显示「加载失败」？
→ 检查 `config.json` 的 `downloadSources[].url` 路径是否正确，对应 JSON 文件是否存在。

---

## 部署检查清单

```bash
# 在仓库根执行，全部通过即部署成功

echo "=== 1. 结构检查 ==="
ls index.html config.json list.txt
ls .github/workflows/daily-ry-parser.yml
ls .github/workflows/every-2days-tvbox-api.yml
ls python/ry下载器.py python/tvbox_get_api.py
ls rylinks.txt tvboxapilinks.txt

echo "=== 2. YAML 语法校验 ==="
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/daily-ry-parser.yml')); print('A OK')"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/every-2days-tvbox-api.yml')); print('B OK')"

echo "=== 3. 站点配置校验 ==="
python3 -c "import json; json.load(open('config.json')); print('config.json OK')"

echo "=== 4. 脚本本地试跑 ==="
python3 python/tvbox_get_api.py --check-config
python3 python/ry下载器.py
ls ry/ tvbox/ list.txt

echo "=== 5. 站点本地预览 ==="
python3 -m http.server 8080
# → 访问 http://localhost:8080 检查 footer 是否贴底
```

---

## 许可证

本站接口资源由社区整理，所有资源均来自互联网，版权归原作者所有。

**仅供测试学习使用，请勿用于违法及商业用途，请勿付费购买。如涉及侵权，请联系删除。**

QQ 交流群：1067685939

---

**版本**：v1.0.0（发行版）
**维护者**：误道者
**更新时间**：2026-09-10
