# HTML 渲染规范

用于把 `report.json` 填入 `assets/templates/weekly-hotspot.html`，生成可浏览器预览并由用户导出 PDF 的 HTML 文件。

## 模板结构映射

`weekly-hotspot.html` 使用研究简报风格：暖羊皮纸底色 `#f5f4ed`、墨蓝强调色 `#1B365D`、苍南金楷 + Charter 衬线字体。

| 报告层级 | HTML 容器 | 关键元素 |
|---------|----------|---------|
| 封面 | `.cover` | `.cover-eyebrow` 领域标签、`.cover-title` 标题、`.cover-sub` 副标题、`.cover-meta` 统计周期 |
| 本周要点 | `.highlights` | `ol.highlights-list > li` 编号条目，关键词用 `.hl-accent` |
| 目录 | `.toc` | `.toc-section-label` 分组标签、`.toc-item` 条目行 |
| 分析专栏 | `section.chapter` | `.chapter-num` 章节编号、`h1` 标题、每篇分析为 `.article` |
| 优选信息 | `section.chapter` | 同上，正文为 2 到 3 句话短讯 |
| 本周招标信息 | `section.chapter.tender-chapter` | 表格使用 `.tender-table` |
| 地理空间热力图 | `section.chapter.heatmap-chapter` | `.heatmap-grid` 并排放全国和浙江图块 |
| 每条资讯元数据 | `.source-meta` | 来源、发布时间、来源链接 |
| 分析专栏摘要 | `.summary-callout` | 仅用于分析专栏 |
| 尾注 | `.colophon` | 报告声明和统计周期 |

## 填入规则

1. 不改 CSS，只替换 `{{占位符}}` 和注释区间内容。
2. 封面替换 `{{领域标签}}`、`{{领域}}`、`{{开始日期}}`、`{{结束日期}}`、`{{入选资讯数}}`、`{{分类数}}`。
3. 本周要点在 `HIGHLIGHT_LOOP` 中复制 `<li>` 块。
4. 目录在 `TOC_ANALYSIS_LOOP` 和 `TOC_SELECTED_LOOP` 中复制 `.toc-item`。
   当前模板按固定章节页填目录页码：分析专栏 4，优选信息 5，本周招标信息 6，地理空间热力图 7；不要保留 `00` 占位。
5. 分析专栏在 `ANALYSIS_ARTICLE_LOOP` 中复制 `.article`，正文段落数 3 到 5 段。
6. 优选信息在 `SELECTED_ITEM_LOOP` 中复制 `.article`，正文为 2 到 3 句话。
7. 招标信息在 `TENDER_ROW_LOOP` 中复制 `<tr>`；没有招标数据时删除招标和热力图章节。
8. 页眉替换 `{{生成时间}}` 和 `{{报告短标题}}`；未提供 `generated_at` 时由 `scripts/fill_template.py` 自动写入当前时间。页脚只居中显示分页。
9. 热力图由 `scripts/fill_template.py` 内联 ECharts、全国 geojson 和浙江 geojson 生成，地图必须在图块中水平居中。
10. 填入完成后运行 `python3 scripts/build.py report.html --report-json report.json`。

## 浏览器导出 PDF

不要在 skill 默认流程中调用 PDF 生成脚本。需要 PDF 时：

```text
Chrome 打开 HTML → 打印 → 另存为 PDF → 边距选“无” → 勾选“背景图形”
```

HTML 预览页提供“导出 PDF”按钮，并拦截 `Cmd+P / Ctrl+P` 调用浏览器打印。

## 视觉验收

- 封面标题完整、无裁切，统计周期可见。
- 本周要点条目数与正文一致。
- 目录条目与正文 `h2` 标题逐项对应。
- `.source-meta` 每条的来源、发布时间、来源链接完整。
- 分析专栏 `.summary-callout` 摘要块存在且非空。
- 优选信息正文是 2 到 3 句话短讯。
- 招标表格位于优选信息下方，字段完整。
- 热力图位于招标表格下方，包含全国和浙江两个图块。
- 热力图在不同窗口宽度下保持居中，图块标题和地图不重叠。
- 非封面页面页眉左侧显示生成时间，报告短标题从页面中线开始左对齐，页脚居中显示分页。
- 无 `{{...}}` 残留占位符。
- 页面无异常空白页或单行孤行。
