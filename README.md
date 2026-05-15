# study-notion-heatmap

从 Notion 日计划数据库拉取每天的学习总时长，使用 `github-heatmap` 绘制 GitHub 风格热力图，并通过 GitHub Actions 每日自动更新，最终同步展示到 Notion 页面。

## 效果预览

热力图按学习时长分四档渐变着色：

| 时长 | 颜色 | 说明 |
|------|------|------|
| 0 分钟 | ⬜ `#ebedf0` | 未学习（GitHub 灰） |
| 1 ~ 240 分钟（≤4h） | 🔵 浅紫白 → 天蓝 | 轻度学习 |
| 241 ~ 480 分钟（4~8h） | 🌊 天蓝 → 深海蓝 | 中高强度 |
| > 480 分钟（>8h） | 🟢 春意绿 → 深翠绿 | 满课满格 |

## 前置条件

### Notion 数据库结构要求

你的日计划数据库（`日`）需要包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `日期` | 日期（Date） | 当天日期 |
| `总时长` | 数字/公式/汇总（Number / Formula / Rollup） | 当天学习总分钟数 |

> 如果你的字段名不同，修改 `update_study_heatmap.py` 中 `get_notion_data()` 里的 `"日期"` 和 `"总时长"` 即可。

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork**，在你的 GitHub 账户下创建副本。

### 2. 配置 Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `NOTION_TOKEN` | Notion Integration Token（在 [notion.so/my-integrations](https://www.notion.so/my-integrations) 创建） |
| `NOTION_DATABASE_ID` | 日计划数据库的 ID（从数据库 URL 中复制 32 位 ID） |
| `NOTION_PAGE` | （可选）热力图所在 Notion 页面的 URL 或 ID，用于自动同步 embed |

### 3. 连接 Notion Integration

在 Notion 中打开你的日计划数据库 → 右上角 `...` → **连接** → 选择你创建的 Integration。

### 4. 开启 GitHub Pages（可选，用于 Notion 嵌入展示）

在仓库 **Settings → Pages** 中，将 Source 设置为 `Deploy from a branch`，Branch 选 `main`，目录选 `/`（根目录）。

开启后，热力图展示页地址为：
```
https://<你的用户名>.github.io/study-notion-heatmap/study.html?image=<SVG raw URL>
```

### 5. 手动触发或等待定时任务

- **手动触发**：在 Actions → `Study Heatmap Engine` → `Run workflow`
- **自动运行**：每天北京时间 23:30 自动生成

## 在 Notion 中嵌入热力图

1. 等 GitHub Actions 成功运行后，找到 `study_heatmap/main.svg` 的 raw URL：
   ```
   https://raw.githubusercontent.com/<用户名>/study-notion-heatmap/main/study_heatmap/main.svg
   ```
2. 构造展示页 URL：
   ```
   https://<用户名>.github.io/study-notion-heatmap/study.html?image=<上面的 raw URL>
   ```
3. 在 Notion 中插入 `/embed` 块，粘贴上面的展示页 URL。

## 自定义

### 修改颜色方案

在 `update_study_heatmap.py` 的 `get_color_for_minutes()` 函数中修改颜色值。

### 修改热力图署名

在仓库 **Settings → Variables** 中添加变量 `HEATMAP_NAME`，填写你想显示的名字（默认为 `学习热力图`）。

### 修改定时时间

在 `.github/workflows/study.yml` 中修改 `cron` 表达式（UTC 时间）：
```yaml
- cron: "30 15 * * *"   # 当前为 UTC 15:30 = 北京 23:30
```

## 年度归档

每年 1 月 1 日北京时间 10:00，`Annual Study Heatmap Archive` workflow 会自动将上一年的热力图存档至 `old_heatmap/<年份>.svg`。

也可以在 Actions 页面手动触发，并在输入框中填写想归档的年份。

## 项目结构

```
study-notion-heatmap/
├── .github/
│   └── workflows/
│       ├── study.yml              # 每日热力图生成
│       └── annual_heatmap.yml     # 年度归档
├── study_heatmap/
│   └── main.svg                   # 当前年份热力图（自动生成）
├── old_heatmap/                   # 历史年份存档（自动生成）
├── study.html                     # GitHub Pages 展示页（支持深色模式）
├── update_study_heatmap.py        # 核心脚本：拉取数据 + 生成着色 SVG
├── update_notion_embed.py         # 可选：将热力图 URL 同步到 Notion
├── requirements.txt
└── README.md
```

## 参考

- 热力图引擎：[github-heatmap](https://pypi.org/project/github-heatmap/)
- 灵感来源：[keep2notion](https://github.com/malinkang/keep2notion)
