---
name: weekly-hotspot-analysis
description: Collect important news from the past week for a user-specified domain, classify items by topic, and output a browser-openable Chinese weekly hotspot analysis HTML report with original source, published time, source URL, and AI summary for every item. Use for weekly news, industry updates, domain monitoring, Zhejiang transportation/logistics/infrastructure policy, flow economy research, and sourced news digests. Generate PDF only when the user explicitly asks for PDF.
---

# 本周热点分析

围绕用户指定领域，抓取近一周重要资讯，分类整理，并输出可在浏览器打开的中文《本周热点分析》HTML 报告。

## 领域边界和示例场景

本 skill 必须围绕用户指定领域生成周报。用户未指定领域时，先追问明确重点，不要替用户预设行业、地域或机构口径。

浙江交通、物流、基础设施、港口、铁路、多式联运、低空物流、流量经济、国家“六张网”等是常见示例场景；只有用户明确指定这类主题时，才启用下面偏好：

- 领域：浙江交通、物流、基础设施、港口、铁路、多式联运、低空物流、流量经济、国家“六张网”及相关政策。
- 视角：省级发展改革、规划研究、政府决策咨询，而不是媒体综述或企业营销。
- 口径：重事实、重政策依据、重项目和指标，少空泛判断；涉及正式材料时使用规范中文政务文风。
- 地域：用户明确指定浙江、长三角或相关城市时，优先覆盖对应地域，再补充国家层面和典型省市经验。
- 非政务研究主题按用户指定领域处理，不要混入浙江政务热点分析。

## 工作方式

1. 确认领域和统计周期。用户未指定领域时，追问用户明确重点，不要替用户预设领域。用户未指定周期时，默认使用当前日期往前 7 天；如用户说“本周”，按当前自然周解释，并在报告中写明日期范围。用户未指定地域时按国内口径执行，不在标题或统计周期中额外标注地域；只有用户明确指定地域时才写明。
2. 读取 `references/crawling-guide.md` 和 `references/domain-presets.yaml`，先形成搜索计划，再收集资讯。优先使用用户指定信源；命中领域预置信源时，先用预置信源生成第一轮候选，再按默认流程把用户领域拆成相近关键词和查询簇，通过不同搜索入口广泛发现线索。主动搜索综述、公众号、周报、名单型和“国内动态”文章作为线索池，抽取政策、城市、机构、项目和企业，再回溯原始来源。最终保留官方、监管、协会、主流媒体、公司公告、研究机构、微信公众号等可追溯来源。
3. 过滤和去重。保留发布时间落在统计周期内、与指定领域直接相关、能找到原始来源链接的资讯；同一事件多源报道只保留最原始或最权威来源，必要时在摘要中提及补充来源。
4. 按主题分类。分类名应贴近用户指定领域，不要使用空泛分类；同一资讯只能进入一个最主要分类；分类建议控制在 3 到 6 个。若同类资讯超过 20 条，先按 `references/crawling-guide.md` 聚合成主题簇，再选择代表性资讯进入正文。
5. 读取 `references/summary-prompts.md`，为每条资讯写 AI 摘要。摘要必须说明“发生了什么、为什么重要、对该领域的影响”，避免只改写标题。
6. 默认直接写出单文件 HTML，不调用 Python 脚本。必须从 `assets/report-template.html` 复制并替换内容，保留模板 CSS、布局 class 和打印按钮；不要临场重写另一套 HTML。HTML 必须包含标题、统计周期、核心摘要、本周焦点、分类热点分析和总体判断；每条动态保留发布时间，并把来源名称写成可点击链接。
7. 最终回复用可点击链接给出 HTML 文件，例如 `[打开 HTML 报告](/absolute/path/report.html)`。用户可在浏览器中打开，使用打印导出 PDF 或截图/浏览器工具导出图片。
8. 只有用户明确要求输出 PDF 时，才整理结构化报告 JSON 并调用 PDF renderer。用户要求 Markdown/md 文件时，写出 `.md` 文件并返回路径。

## 交付方式

默认交付：生成中文《本周热点分析》单文件 HTML，并返回 HTML 文件路径；不生成 PDF，不生成 Markdown 文件。

HTML 交付：默认路径建议为 `output/html/{领域}-weekly-report.html`。执行：

复制 `assets/report-template.html` 到 `output/html/{领域}-weekly-report.html`，替换标题、周期、摘要、焦点、分类、动态和总体判断。文件必须是单文件 HTML，CSS 内联，不依赖外部 JS/CSS、Python、服务器或网络。保留这些样式锚点：`hero`、`section-heading`、`section-banner`、`timeline-item`、`date-badge`、`source-line`、`window.print()`。

执行后检查 HTML 文件存在；最终回复只需给出可点击 HTML 链接，并说明可用浏览器打开后自行打印导出 PDF 或截图导出图片。链接使用绝对路径，例如 `[打开 HTML 报告](/Users/.../output/html/report.html)`，不要只给相对路径。

PDF 交付：用户请求中出现“PDF、pdf、生成 PDF、导出 PDF、输出 PDF、PDF 文件”等语义时，最终交付必须包含 PDF 文件，不能只输出 Markdown、JSON 或报告正文。

Markdown 文件交付：用户请求中出现“Markdown 文件、md 文件、输出 md、导出 Markdown、保存为 Markdown”等语义时，写出 `.md` 文件并返回路径；不要生成 PDF，除非用户同时明确要求 PDF。

PDF 执行要求：

1. 先完成报告正文，确保每条动态正文中包含发布时间和可点击来源名称。
2. 整理一份临时报告 JSON，字段按 `references/pdf-report-format.md`。
3. 优先通过跨环境包装脚本执行：

```bash
scripts/render_pdf.sh report.json output/pdf/report.pdf
```

Windows PowerShell 使用：

```powershell
scripts\render_pdf.ps1 report.json output\pdf\report.pdf
```

4. 执行后检查 `output/pdf/report.pdf` 是否存在；包装脚本会在可用时抽取文本检查标题、分类、总体判断和至少一个来源名称。
5. 最终回复必须给出 PDF 文件路径，并简要说明已生成 PDF。不要把生成 PDF 的 Python 代码贴给用户后就收工。

如果当前运行环境没有 Python、没有文件系统、不能执行命令，或找不到带 `reportlab` 的 Python runtime，必须明确说明“当前环境不能直接生成 PDF 文件”，并优先交付默认 HTML；不要在线安装依赖、切换到 Word/LaTeX 或声称已生成 PDF。

## 执行闭环

不要一次性写完报告；按下面闭环推进，发现问题时只回到对应环节修正：

1. 候选资讯闭环：收集候选，核验来源、发布时间和领域相关性；合格资讯不足或来源过单一时，回到搜索阶段补搜。政策、产业、技术、项目或上市公司动态活跃的高频领域，少于 8 条合格资讯或少于 3 类时不得收工，除非已按抓取指南完成语义扩展搜索并说明仍然稀少。
2. 分类聚合闭环：初分分类后检查是否控制在 3 到 6 类；过散则合并，过粗则拆分；同类资讯超过 20 条时按主题簇聚合。
3. 态势判断闭环：生成核心摘要和态势判断后，检查每个判断是否有已入选资讯支撑；无证据则删除或降级为常态跟踪。
4. 报告自检闭环：生成正文后检查报告结构、动态来源链接、重复资讯和无来源判断；缺项只补问题部分，不重写全文。

## 交付前最小检查

默认生成 HTML 前，按 `references/checklist.md` 做 P0/P1 检查；P0 未通过不得交付。发现缺少固定栏目、统计周期、来源链接、发布时间、AI 摘要或分类数量不合格时，只修正问题部分再交付。不要把候选统计、搜索入口统计或来源明细表作为默认交付内容。

默认 HTML 交付时，写出文件后检查文件存在，并确认最终回复使用绝对路径可点击链接。用户要求 PDF 时，再执行 `references/pdf-report-format.md` 中的 renderer 文件存在检查。renderer 报告 JSON 字段缺失时，补齐报告数据后重跑，不要交付空壳 PDF。

## 报告结构

《本周热点分析》内容固定使用以下层级：

1. 标题和统计周期。
2. 核心摘要：3 到 6 条短 bullet，每条不超过 60 字。
3. 本周焦点：突出 1 到 3 条最重要资讯，说明入选原因。
4. 分类热点分析：每个分类先写 150 到 250 字综合分析，再列入选资讯。
5. 总体判断：写 120 到 200 字，说明本周态势和下一步关注变量。

每条入选资讯在分类下使用紧凑正文，不再额外生成来源明细表。建议格式：

```text
- 资讯标题
  来源：[来源名称](原文链接)；发布时间：YYYY-MM-DD
  AI摘要：……
```

Markdown/HTML 版式以结构清晰、来源链接完整、段落不臃肿为准。默认生成 HTML 文件；用户要求 Markdown 文件时才写 `.md` 文件；用户要求 PDF 时才生成 PDF。HTML 和 PDF 都是同一报告内容的格式化交付版本，栏目仍按实际领域和资讯分类生成，不写死业务栏目。

HTML 样式固定使用 `assets/report-template.html`：圆角蓝色标题区、不对称圆角栏目标题、左侧日期徽章、动态条目、标题来源链接和虚线分隔。只替换内容，不替换整体 CSS 和栏目结构。

用户未指定地域时，统计周期只写日期，不追加“中国大陆”“国内”等默认地域说明。

## 资讯字段

每条资讯必须包含：

- `title`：资讯标题
- `category`：分类
- `source_name`：原始来源名称
- `source_url`：原文链接
- `published_at`：发布时间，优先使用原文页面时间；格式建议为 `YYYY-MM-DD HH:MM` 或 `YYYY-MM-DD`
- `ai_summary`：AI 摘要

可选字段：

- `importance`：重要性，取 `高`、`中`、`低`
- `entities`：涉及公司、机构、政策、产品或人物
- `notes`：补充说明，例如多个来源口径差异

## 输出契约

默认只交付中文《本周热点分析》HTML 文件，不附加执行说明、候选统计、搜索入口统计或来源明细表。

用户要求文件交付时，在报告正文后追加必要文件结果即可：

- 默认 HTML：可点击 HTML 链接，使用绝对路径。
- 如用户要求 PDF：PDF 文件路径；无法生成时说明原因。
- 如用户要求 Markdown 文件：Markdown 文件路径。

## 质量要求

- 不要把搜索结果页、聚合页、转载页当作原始来源，除非找不到更原始来源，并在 `notes` 中说明。
- 不要引用没有发布时间的资讯；如果页面只有相对时间，先换算为具体日期并说明依据。
- 不要把同一事件拆成多条重复资讯。
- 不要生成缺少来源链接或发布时间的动态；不要单独生成来源明细表。
- 不要把态势判断写成无来源预测；判断必须来自已入选资讯。
- 不要跳过报告自检闭环；最终报告缺少固定层级时必须补齐。
- 默认必须生成真实 HTML 文件路径；不要只输出 JSON 或 Markdown 后收工。
- 用户要求 PDF 时，没有真实 PDF 文件路径不得宣称 PDF 已生成；用户未明确要求 PDF 时，不调用 PDF renderer。
- 用户要求 Markdown 文件时，必须写出 `.md` 文件并返回路径；默认交付必须写出 HTML 文件。

## 参考文件

- `references/crawling-guide.md`：信息抓取、信源优先级、去重和发布时间判定。
- `references/domain-presets.yaml`：领域预置信源和网站配置。
- `references/summary-prompts.md`：单条摘要、分类分析、核心摘要和结论的提示词。
- `references/pdf-report-format.md`：PDF 输出 JSON 结构、样式模板和运行方式。
- `references/checklist.md`：交付前 P0/P1/P2 质量门禁。
- `assets/report-template.html`：默认 HTML 报告模板；复制后替换内容，保持样式锚点不变。
- `scripts/render_pdf.sh` / `scripts/render_pdf.ps1`：跨 macOS、Linux、Windows 的 PDF 稳定生成入口。
