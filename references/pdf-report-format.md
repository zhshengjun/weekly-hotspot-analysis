# PDF 周报格式

仅当用户明确要求输出 PDF 时，才按 `SKILL.md` 完成资讯抓取、核验、去重、分类和摘要后，整理结构化 JSON，交给 `scripts/render_weekly_pdf.py` 生成 PDF。默认交付是在聊天中返回报告正文，不生成 PDF。

## 运行命令

优先使用跨环境包装脚本；它会寻找带 `reportlab` 的 Python runtime，再调用固定 renderer：

```bash
scripts/render_pdf.sh examples/sample-weekly-report.json output/pdf/sample-weekly-report.pdf
```

Windows PowerShell 使用：

```powershell
scripts\render_pdf.ps1 examples\sample-weekly-report.json output\pdf\sample-weekly-report.pdf
```

如果当前环境没有带 `reportlab` 的 Python，包装脚本会失败；此时按 Markdown 降级交付，不要声称 PDF 已生成。

底层 renderer 仍可直接调用：

```bash
python3 scripts/render_weekly_pdf.py examples/sample-weekly-report.json
python3 scripts/render_weekly_pdf.py report.json -o output/pdf/report.pdf
```

默认样式来自 `references/pdf-style-template.json`，不依赖外部项目、浏览器或 HTML/CSS。

## 执行闭环

用户要求 PDF 时，生成 Markdown/JSON 不是完成状态。必须执行 renderer 并确认 PDF 文件存在：

```bash
scripts/render_pdf.sh report.json output/pdf/report.pdf
test -f output/pdf/report.pdf
```

能运行 Python 校验时，至少抽检标题、分类名、总体判断和一个来源名称：

```bash
python3 -c "import pdfplumber; text='\\n'.join(p.extract_text() or '' for p in pdfplumber.open('output/pdf/report.pdf').pages); assert '本周热点分析' in text"
```

如果运行环境没有 Python、文件系统、命令执行能力，或无法使用 `reportlab`，只能交付报告正文降级结果，并在最终回复中明确说明无法在当前环境直接生成 PDF 文件。不要在线安装依赖、切换到 HTML/Word/LaTeX 或让 agent 自行设计 PDF。

## 报告 JSON

```json
{
  "title": "本周热点分析",
  "domain": "示例领域",
  "period_start": "2026-06-23",
  "period_end": "2026-06-30",
  "core_summary": ["短结论 1", "短结论 2"],
  "weekly_focus": ["焦点事项及入选原因"],
  "sections": [
    {
      "title": "分类名",
      "analysis": "150 到 250 字分类分析。",
      "items": [
        {
          "title": "资讯标题",
          "published_at": "2026-06-30",
          "source_name": "原始来源",
          "source_url": "https://example.com",
          "ai_summary": "单条 AI 摘要。",
          "importance": "高"
        }
      ]
    }
  ],
  "overall_judgment": "总体判断。"
}
```

分类由实际领域和本周资讯决定，通常 3 到 6 类，不写死业务栏目。PDF 不单独生成来源明细表；每条动态标题后的来源名称是可点击超链接。

## 样式模板

`references/pdf-style-template.json` 只保存视觉配置：页面边距、ReportLab CID 字体名、标题区颜色和栏目色板。默认使用内置 CID 字体 `STSong-Light`，保证中文 PDF 可生成且不依赖操作系统字体路径。

## 版式口径

PDF 参考低空经济周报的视觉语言：圆角蓝色标题区、不对称圆角栏目标题、左侧日期徽章、动态条目、标题来源链接和虚线分隔。不要把外部参考项目里的业务模块搬进来；当前 skill 没有的模块不需要新增。
