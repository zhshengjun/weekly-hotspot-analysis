#!/usr/bin/env python3
"""Fill the weekly hotspot HTML template from report.json.

Usage:
  python3 scripts/fill_template.py examples/sample-report.json --output /tmp/report.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "assets" / "templates" / "weekly-hotspot.html"
ECHARTS = ROOT / "assets" / "vendor" / "echarts.min.js"
CHINA_GEO = ROOT / "assets" / "geo" / "china_provinces.json"
ZHEJIANG_GEO = ROOT / "assets" / "geo" / "zhejiang_cities.json"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def budget_display(value: object) -> str:
    return str(value or "").strip().replace("万元", "万")


def paragraphs(parts: list[str]) -> str:
    return "\n".join(f"    <p>{esc(part)}</p>" for part in parts if str(part).strip())


def loop(html_text: str, name: str, rows: list[dict[str, str]]) -> str:
    pattern = re.compile(
        rf"(<!-- {name}_START -->)(.*?)(<!-- {name}_END -->)",
        re.S,
    )
    match = pattern.search(html_text)
    if not match:
        return html_text
    block = match.group(2)
    rendered = []
    for row in rows:
        item = block
        for key, value in row.items():
            item = item.replace("{{" + key + "}}", value)
        rendered.append(item)
    return html_text[: match.start()] + match.group(1) + "".join(rendered) + match.group(3) + html_text[match.end() :]


def section_items(items: list[dict]) -> list[dict[str, str]]:
    rows = []
    for index, item in enumerate(items, 1):
        parts = item.get("paragraphs") or []
        rows.append(
            {
                "序号": str(index),
                "编辑主题标题": esc(item.get("title")),
                "标签：编辑主题标题": esc(item.get("title")),
                "来源名称": esc(item.get("source_name")),
                "发布时间": esc(item.get("published_at")),
                "来源链接": esc(item.get("source_url")),
                "摘要 · 2-4 句话概括事实变化、重要性及影响": esc(item.get("summary")),
                "正文段落 1": esc(" ".join(str(part).strip() for part in parts if str(part).strip())),
                "正文段落 2": "",
                "正文段落 3": "",
                "__paragraphs__": paragraphs(parts),
            }
        )
    return rows


def replace_article_paragraphs(html_text: str) -> str:
    return re.sub(
        r"\s*<p>\{\{正文段落 1\}\}</p>\s*<p>\{\{正文段落 2\}\}</p>\s*<p>\{\{正文段落 3\}\}</p>",
        "\n{{__paragraphs__}}",
        html_text,
    )


def normalize_region(name: str) -> str:
    for suffix in ("特别行政区", "维吾尔自治区", "回族自治区", "壮族自治区", "自治区", "省", "市"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def heatmap_from_tenders(tenders: list[dict], zhejiang: bool = False) -> list[dict]:
    field = "city" if zhejiang else "region"
    counter: Counter[str] = Counter()
    for tender in tenders:
        if zhejiang and "浙江" not in str(tender.get("region") or ""):
            continue
        name = str(tender.get(field) or "").strip()
        if not name:
            continue
        counter[normalize_region(name)] += 1
    return [{"name": name, "value": count} for name, count in counter.items()]


def map_summary(rows: list[dict], empty: str) -> str:
    ranked = sorted(rows, key=lambda item: int(item.get("value") or item.get("count") or 0), reverse=True)
    ranked = [item for item in ranked if int(item.get("value") or item.get("count") or 0) > 0][:5]
    if not ranked:
        return empty
    return "、".join(f"{normalize_region(str(item.get('name') or item.get('region')))}{int(item.get('value') or item.get('count') or 0)}项" for item in ranked)


def generated_at(meta: dict) -> str:
    value = str(meta.get("generated_at") or "").strip()
    if value:
        return value
    now = datetime.now()
    return f"{now.year}/{now.month}/{now.day} {now.hour:02d}:{now.minute:02d}"


def heatmap_script(china_rows: list[dict], zhejiang_rows: list[dict]) -> str:
    if not china_rows and not zhejiang_rows:
        return ""
    echarts = ECHARTS.read_text(encoding="utf-8")
    china_geo = json.loads(CHINA_GEO.read_text(encoding="utf-8"))
    zhejiang_geo = json.loads(ZHEJIANG_GEO.read_text(encoding="utf-8"))
    payload = {
        "china": china_rows,
        "zhejiang": zhejiang_rows,
        "chinaGeo": china_geo,
        "zhejiangGeo": zhejiang_geo,
    }
    return f"""
<script>{echarts}</script>
<script>
(function() {{
  var payload = {json.dumps(payload, ensure_ascii=False)};
  function shortName(name) {{
    return String(name || '')
      .replace(/特别行政区$/u, '')
      .replace(/维吾尔自治区$/u, '')
      .replace(/回族自治区$/u, '')
      .replace(/壮族自治区$/u, '')
      .replace(/自治区$/u, '')
      .replace(/省$/u, '')
      .replace(/市$/u, '');
  }}
  function color(value) {{
    if (!value) return '#dbeaf6';
    if (value === 1) return '#5aa4d4';
    if (value === 2) return '#2474af';
    return '#123e6d';
  }}
  function align(rows, geo) {{
    var byName = {{}};
    (rows || []).forEach(function(row) {{
      var name = shortName(row.name || row.region);
      if (name) byName[name] = Number(row.value || row.count || 0);
    }});
    return (geo.features || []).map(function(feature) {{
      var full = feature.properties && feature.properties.name;
      var value = byName[shortName(full)] || 0;
      return {{ name: full, value: value, itemStyle: {{ areaColor: color(value) }} }};
    }});
  }}
  function render(id, mapName, geo, rows, layoutSize) {{
    var el = document.getElementById(id);
    if (!el || !window.echarts) return;
    echarts.registerMap(mapName, geo);
    var chart = echarts.init(el, null, {{renderer: 'svg'}});
    chart.setOption({{
      animation: false,
      tooltip: {{ trigger: 'item', formatter: function(p) {{ return shortName(p.name) + '：' + (p.value || 0) + '项'; }} }},
      series: [{{
        type: 'map',
        map: mapName,
        roam: false,
        layoutCenter: ['50%', '50%'],
        layoutSize: layoutSize,
        data: align(rows, geo),
        label: {{
          show: true,
          color: '#8aa0b5',
          fontSize: mapName === 'zhejiang' ? 9 : 7,
          formatter: function(p) {{ return shortName(p.name) + (p.value ? '\\n' + p.value : ''); }}
        }},
        emphasis: {{ disabled: true }},
        itemStyle: {{ areaColor: '#dbeaf6', borderColor: '#fff', borderWidth: 1 }}
      }}]
    }});
    chart.resize();
    if (window.ResizeObserver) {{
      new ResizeObserver(function() {{ chart.resize(); }}).observe(el);
    }}
    window.addEventListener('resize', function() {{ chart.resize(); }});
  }}
  render('china-heatmap', 'china', payload.chinaGeo, payload.china, '86%');
  render('zhejiang-heatmap', 'zhejiang', payload.zhejiangGeo, payload.zhejiang, '78%');
}})();
</script>
"""


def remove_optional_sections(html_text: str) -> str:
    html_text = re.sub(r"\n\s*<div class=\"toc-section-label\">〖本周招标信息〗</div>.*?<div class=\"toc-section-label\">〖地理空间热力图〗</div>.*?</div>\n", "\n", html_text, flags=re.S)
    html_text = re.sub(r"\n<!-- ═══════════════ 本周招标信息 ═══════════════ -->.*?<!-- ═══════════════ STANDALONE COLOPHON ═══════════════ -->", "\n<!-- ═══════════════ STANDALONE COLOPHON ═══════════════ -->", html_text, flags=re.S)
    return html_text


def fill(report: dict, template: Path) -> str:
    meta = report.get("meta") or {}
    html_text = replace_article_paragraphs(template.read_text(encoding="utf-8"))

    analysis = report.get("analysis") or []
    selected = report.get("selected") or report.get("highlights_news") or []
    tenders = report.get("tenders") or []

    simple = {
        "文档标题": meta.get("title") or f"{meta.get('domain', '')}本周热点分析",
        "作者": meta.get("author") or "",
        "摘要": meta.get("description") or "",
        "关键词": meta.get("keywords") or meta.get("domain") or "",
        "生成时间": generated_at(meta),
        "报告短标题": meta.get("short_title") or f"{meta.get('domain', '')}本周热点分析",
        "领域标签 · 如 \"现代物流\" / \"新能源\"": meta.get("label") or meta.get("domain") or "",
        "领域": meta.get("domain") or "",
        "开始日期": meta.get("start_date") or "",
        "结束日期": meta.get("end_date") or "",
        "入选资讯数": meta.get("item_count") or len(analysis) + len(selected),
        "分类数": meta.get("category_count") or "",
        "招标栏目导语": report.get("tender_intro") or "本栏目收录本周可核验、与主题相关的招标采购项目。",
        "招标收录口径": report.get("tender_note") or "收录口径：投标截止日、文件获取期或发布日期落在统计周期内，且附可访问原文链接的项目。",
        "全国热力图摘要": report.get("china_heatmap_summary") or "",
        "浙江热力图摘要": report.get("zhejiang_heatmap_summary") or "",
    }

    html_text = loop(html_text, "HIGHLIGHT_LOOP", [
        {"要点关键词": esc(item.get("keyword")), "要点正文": esc(item.get("body"))}
        for item in report.get("highlights", [])
    ])
    html_text = loop(html_text, "TOC_ANALYSIS_LOOP", [
        {"序号": str(i), "分析专栏编辑主题标题": esc(item.get("title"))}
        for i, item in enumerate(analysis, 1)
    ])
    html_text = loop(html_text, "TOC_SELECTED_LOOP", [
        {"序号": str(i), "优选信息编辑主题标题": esc(item.get("title"))}
        for i, item in enumerate(selected, 1)
    ])
    html_text = loop(html_text, "ANALYSIS_ARTICLE_LOOP", section_items(analysis))
    html_text = loop(html_text, "SELECTED_ITEM_LOOP", section_items(selected))

    if tenders:
        html_text = loop(html_text, "TENDER_ROW_LOOP", [
            {
                "序号": str(i),
                "项目名称": esc(item.get("project_name")),
                "采购主体": esc(item.get("purchaser")),
                "地区": esc(item.get("region")),
                "预算金额": esc(budget_display(item.get("budget") or item.get("budget_text"))),
                "本周节点": esc(item.get("node") or item.get("deadline") or item.get("published_at")),
                "招标链接": esc(item.get("url")),
            }
            for i, item in enumerate(tenders, 1)
        ])
        heatmaps = report.get("heatmaps") or {}
        china_rows = heatmaps.get("china") or heatmap_from_tenders(tenders)
        zhejiang_rows = heatmaps.get("zhejiang") or heatmap_from_tenders(tenders, zhejiang=True)
        simple["全国招标热力图"] = '<div id="china-heatmap" class="echarts-map"></div>'
        simple["浙江招标热力图"] = '<div id="zhejiang-heatmap" class="echarts-map"></div>'
        simple["全国热力图摘要"] = simple["全国热力图摘要"] or map_summary(china_rows, "本周期全国暂无可汇总招标项目")
        simple["浙江热力图摘要"] = simple["浙江热力图摘要"] or map_summary(zhejiang_rows, "本周期浙江暂无可汇总招标项目")
        html_text = html_text.replace("</body>", heatmap_script(china_rows, zhejiang_rows) + "\n</body>")
        html_text = re.sub(r"\n<!-- ═══════════════ STANDALONE COLOPHON ═══════════════ -->\s*<section class=\"standalone-colophon\">.*?</section>\n", "\n", html_text, flags=re.S)
    else:
        html_text = loop(html_text, "TENDER_ROW_LOOP", [])
        html_text = remove_optional_sections(html_text)

    for key, value in simple.items():
        html_text = html_text.replace("{{" + key + "}}", esc(value) if key not in {"全国招标热力图", "浙江招标热力图"} else str(value))
    return html_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill weekly hotspot HTML template from report.json")
    parser.add_argument("report_json")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--output", "-o", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    output = fill(report, Path(args.template))
    Path(args.output).write_text(output, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
