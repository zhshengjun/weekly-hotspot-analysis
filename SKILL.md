---
name: weekly-hotspot-analysis
description: Collect or ingest weekly news and tender data for a user-specified domain, evaluate relevance and importance, then generate a browser-previewable Chinese weekly hotspot HTML briefing with an analysis column, short selected updates, a tender table, and national/Zhejiang tender heatmaps. Use for competition-ready weekly reports, industry monitoring, policy tracking, source-verified news digests, and report generation from uploaded documents or spreadsheets.
---

# 本周热点分析

围绕用户指定领域，通过“信息搜集 → 评价 → 处理 → 交付”生成中文《本周热点分析》HTML 周报。报告样式参考 `weekly-hotspot-2026-06-26-2026-07-03.pdf`，内容结构为分析专栏、短讯式优选信息、招标列表和地理空间热力图。

## 领域边界

本 skill 必须围绕用户指定领域生成周报。用户未指定领域时，先追问明确重点，不要替用户预设行业、地域、机构口径或研究视角。

用户明确指定地域、机构、行业链条、政策视角或受众时，按用户口径执行；用户未指定时，默认按国内公开信息和领域通用口径处理，不内置任何固定行业或地域偏好。

## 工作方式

1. 确认领域和统计周期。用户未指定领域时，追问用户明确重点。用户未指定周期时，默认使用当前日期往前 7 天；如用户说“本周”，按当前自然周解释，并在正文中写明日期范围。用户未指定地域时按国内口径执行，不在标题或统计周期中额外标注地域；只有用户明确指定地域时才写明。
2. 信息搜集：优先读取用户上传的资讯文档、PDF、Markdown、网页摘录、Excel 或 CSV；再读取 `references/crawling-guide.md`，按用户主题补充联网搜索。上传资料先作为候选池，不直接进入正文；仍需判断主题相关性、来源、发布时间和可追溯链接。
3. 过滤和去重。保留发布时间落在统计周期内、与指定领域直接相关、能找到原始来源链接的资讯；同一事件多源报道只保留最原始或最权威来源，必要时在内部 `notes` 记录补充来源。
4. 评价筛选：读取 `references/scoring-rubric.md`。分析专栏不参与评分，按态势识别选择 1 到 2 个最能解释本周变化的主题；优选信息按两层六指标逐条评分后排序，选 8 到 15 条短讯；招标信息单独筛选，不参与资讯评分。优选信息必须保持来源多样，不能由单一网站或单一来源类型主导。
5. 内容处理：读取 `references/report-structure.md` 和 `references/summary-prompts.md`。分析专栏写 3 到 5 个自然段；优选信息按低空周报形式，每条写 2 到 3 句话，重点交代主体、动作、时间、地点和意义。
6. 结构化交付：把最终内容整理为 `report.json`，再读取 `references/html-rendering.md`，运行 `python3 scripts/fill_template.py report.json --output report.html` 填入 `assets/templates/weekly-hotspot.html`。
7. HTML 检查：运行 `python3 scripts/build.py report.html --report-json report.json`。P0 未通过不得交付。发现缺少固定栏目、统计周期、来源链接、发布时间、短讯正文、资讯评分、招标表或热力图时，只修正问题部分再交付。
8. PDF 交付：不要自动生成 PDF。用户需要 PDF 时，在浏览器打开 HTML 后用打印/导出 PDF 完成，最终 PDF 视觉应与参考 PDF 同一体系。

## 交付方式

分两步交付：

1. **第一步 — report.json**：整理最终结构化数据，作为模板填入输入。
2. **第二步 — HTML 预览**：将 `report.json` 填入 `assets/templates/weekly-hotspot.html`，生成可浏览器打开的 HTML 文件。用户明确说“不用渲染”时跳过；不要自动生成 PDF。
3. **第三步 — 对话摘要**：在最终回复中给出 HTML 路径和验证结果，不附加候选池、剔除池或来源明细表。

## 执行闭环

不要一次性写完报告；按下面闭环推进，发现问题时只回到对应环节修正：

1. 候选资讯闭环：收集候选，核验来源、发布时间和领域相关性；合格资讯不足、来源过单一，或优选信息主要来自采购/招标公告时，回到搜索阶段补搜。政策、产业、技术、项目或上市公司动态活跃的高频领域，少于 8 条合格资讯、少于 3 类或少于 4 类来源类型时不得收工，除非已按抓取指南完成语义扩展搜索并说明仍然稀少。
2. 分类聚合闭环：初分分类后检查是否控制在 3 到 6 类；过散则合并，过粗则拆分；同类资讯超过 20 条时按主题簇聚合。
3. 资讯评分闭环：优选信息候选必须按两层六指标打分；分数缺失、指标越界或综合分公式不一致时，先修正评分再排序。分析专栏候选和招标数据不强制打分。
4. 判断支撑闭环：生成分析专栏和优选信息后，检查每条核心判断是否有已入选资讯支撑；无证据则删除或改写为可由事实支撑的审慎判断。优选信息不得写成长评论，必须保持 2 到 3 句话的要讯形态。
5. 交付自检闭环：生成 HTML 后检查本周要点、目录、分析专栏、优选信息、招标表、热力图、来源核验、重复资讯、逐条来源链接、逐条发布时间和可见元数据；缺项只补问题部分，不重写全文。

## 结构与渲染规则

- 报告层级、资讯字段、`report.json` 最小结构和硬失败格式见 `references/report-structure.md`。
- HTML 模板映射、占位符填充、招标/热力图渲染、浏览器导出 PDF 和视觉验收见 `references/html-rendering.md`。
- 用户未指定地域时，统计周期只写日期，不追加“中国大陆”“国内”等默认地域说明。

## 质量要求

- 不要把搜索结果页、聚合页、转载页当作原始来源，除非找不到更原始来源，并在 `notes` 中说明。
- 不要引用没有发布时间的资讯；如果页面只有相对时间，先换算为具体日期并说明依据。
- 不要把同一事件拆成多条重复资讯。
- 不要让单一网站、单一平台或单一信息类型占据优选信息主体；采购、招标、公告类信息可以入选，但不能替代政策、产业、技术、企业、地方和媒体等多类型来源。
- 不要纳入缺少来源链接或发布时间的动态；默认正文必须在每条信息下展示来源名称、发布时间和来源链接。
- 不要在最终正文中展示原文文章标题；原文标题只用于内部核验和理解。
- 不要在正文末尾附“核验来源”“参考来源”“来源列表”等来源汇总区块；来源名称、发布时间和来源链接只保留在每条正文标题下的元数据行。
- 不要写“这条信息”“这类信息”“该信息”“这条资讯”“该资讯”“这条信息的价值在于”“这条信息的重要性在于”等资讯播报腔；改为直接陈述事实变化、判断和影响。
- 不要写“约束也很清楚”“约束在于”“风险在于”“限制在于”“真正的执行难点在于”“这一变化值得重视”等模板衔接句；把约束、风险和重要性自然写进事实分析。
- 不要把态势判断写成无来源预测；判断必须来自已入选资讯。
- 不要写“总体判断”栏目；不要写“最终分析结论”。
- 不要把 AI 分析写成标题改写、普通摘要或字段式“AI分析：”；必须用连续段落包含事实、判断依据、影响链条、约束条件和下一步关注变量。
- 不要让目录出现空白编号；目录标题必须与正文中的编辑主题标题一致。
- 不要让正文条目缺少 `〖〗` 标题，或出现只有 `〖` 没有 `〗` 的残缺标题。
- 不要跳过报告自检闭环；最终报告缺少固定层级时必须补齐。
- 不要自动生成 PDF；PDF 由用户从 HTML 预览页导出。

## 参考文件

- `references/crawling-guide.md`：信息抓取、信源优先级、去重和发布时间判定。
- `references/scoring-rubric.md`：优选信息两层六指标评分体系，只服务于资讯筛选排序。
- `references/report-structure.md`：报告层级、字段要求、`report.json` 结构和硬失败格式。
- `references/html-rendering.md`：HTML 模板映射、占位符填充、招标/热力图渲染和浏览器导出 PDF。
- `references/summary-prompts.md`：单条评论式分析、目录、栏目分析和自检的提示词。
- `references/checklist.md`：交付前 P0/P1/P2 质量门禁。
- `references/domain-presets.yaml`：领域预设、别名、信源和种子查询。
- `assets/templates/weekly-hotspot.html`：HTML 排版模板，用于生成最终浏览器预览和用户导出的 PDF。
- `scripts/fill_template.py`：从 `report.json` 填充 HTML，并内联 ECharts 全国/浙江热力图。
- `scripts/build.py`：内置 HTML 检查脚本，支持占位符、结构和评分公式验证；不生成 PDF。
