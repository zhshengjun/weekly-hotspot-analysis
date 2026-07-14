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


def category_loop(html_text: str, outer_name: str, inner_name: str, groups: list[dict]) -> str:
    """Render a category loop whose body contains a second item loop."""
    pattern = re.compile(
        rf"(<!-- {outer_name}_START -->)(.*?)(<!-- {outer_name}_END -->)",
        re.S,
    )
    match = pattern.search(html_text)
    if not match:
        return html_text
    outer_block = match.group(2)
    inner_pattern = re.compile(
        rf"<!-- {inner_name}_START -->(.*?)<!-- {inner_name}_END -->",
        re.S,
    )
    inner_match = inner_pattern.search(outer_block)
    rendered_groups = []
    for group in groups:
        group_block = outer_block.replace("{{分类名称}}", esc(group["name"]))
        group_inner_match = inner_pattern.search(group_block)
        if group_inner_match:
            item_block = group_inner_match.group(1)
            rendered_items = []
            for item in group["items"]:
                rendered = item_block
                for key, value in item.items():
                    rendered = rendered.replace("{{" + key + "}}", value)
                rendered_items.append(rendered)
            rendered_inner = (
                f"<!-- {inner_name}_START -->" + "".join(rendered_items) + f"<!-- {inner_name}_END -->"
            )
            group_block = (
                group_block[: group_inner_match.start()]
                + rendered_inner
                + group_block[group_inner_match.end() :]
            )
        rendered_groups.append(group_block)
    return html_text[: match.start()] + match.group(1) + "".join(rendered_groups) + match.group(3) + html_text[match.end() :]


def section_items(items: list[dict]) -> list[dict[str, str]]:
    rows = []
    for index, item in enumerate(items, 1):
        parts = item.get("paragraphs") or []
        rows.append(
            {
                "序号": str(index),
                "分析日期": esc(item.get("published_at")),
                "短讯日期": esc(item.get("published_at")),
                "编辑主题标题": esc(item.get("title")),
                "优选信息编辑主题标题": esc(item.get("title")),
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


def selected_category_groups(items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict[str, str]]] = {}
    order: list[str] = []
    for item in items:
        category = str(item.get("category") or item.get("category_name") or "优选信息").strip()
        if category not in groups:
            groups[category] = []
            order.append(category)
        groups[category].append(item)
    return [{"name": name, "items": section_items(groups[name])} for name in order]


def week_label(meta: dict) -> str:
    explicit = str(meta.get("week_label") or meta.get("week") or "").strip()
    if explicit:
        return explicit if "周" in explicit else f"{meta.get('year') or datetime.now().year}年第{explicit}周"
    end_date = str(meta.get("end_date") or "").strip()
    try:
        week = datetime.strptime(end_date[:10], "%Y-%m-%d").isocalendar().week
        year = datetime.strptime(end_date[:10], "%Y-%m-%d").year
        return f"{year}年第{week}周"
    except ValueError:
        return ""


def max_budget_display(tenders: list[dict]) -> str:
    best_value = -1.0
    best_text = ""
    for tender in tenders:
        raw = str(tender.get("budget") or tender.get("budget_text") or "").strip()
        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", raw)
        if not match:
            continue
        try:
            value = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        if value > best_value:
            best_value = value
            best_text = budget_display(raw)
    return best_text


def dashboard_tender_table(tenders: list[dict]) -> str:
    if not tenders:
        return '<p class="table-note">本周期暂无符合口径的招投标信息。</p>'
    rows = []
    for index, item in enumerate(tenders, 1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{esc(item.get('project_name'))}</td>"
            f"<td>{esc(item.get('purchaser'))}</td>"
            f"<td>{esc(item.get('region'))}</td>"
            f"<td>{esc(budget_display(item.get('budget') or item.get('budget_text')))}</td>"
            f"<td>{esc(item.get('node') or item.get('deadline') or item.get('published_at'))}</td>"
            f"<td><a href=\"{esc(item.get('url'))}\">原文</a></td>"
            "</tr>"
        )
    return (
        '<div class="data-table-wrapper"><table class="data-table">'
        '<thead><tr><th>序号</th><th>项目名称</th><th>采购主体</th><th>地区</th><th>预算金额</th><th>本周节点</th><th>来源</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def radar_rows(items: list[dict]) -> list[dict[str, str]]:
    rows = []
    for item in items:
        rows.append(
            {
                "业务雷达标题": esc(item.get("title")),
                "开展理由": esc(item.get("reason")),
                "涉及部门": esc(item.get("departments")),
                "业务建议": esc(item.get("advice")),
                "目标对象": esc(item.get("target_clients")),
                "优先级": esc(item.get("priority")),
            }
        )
    return rows


DEFAULT_PEER_GENERAL = [
    "国务院发展研究中心", "中国宏观经济研究院", "中国国际工程咨询有限公司",
    "国家信息中心", "中国社会科学院", "中国国际经济交流中心", "赛迪研究院",
    "中国科学技术发展战略研究院", "国研经济研究院", "浙江省经济信息中心",
    "浙江省社会科学院", "浙江省工业和信息化研究院", "浙江省科技信息研究院",
    "浙江清华长三角研究院", "之江实验室", "上海市发展改革研究院",
    "北京市经济社会发展研究院", "广东省发展和改革研究院", "深圳市发展改革研究院",
    "江苏省战略与发展研究中心", "山东省宏观经济研究院", "安徽省经济研究院",
    "四川省经济发展研究院", "湖北省宏观经济研究所", "福建省经济信息中心",
]


def peer_item_html(item: dict) -> str:
    source_type = str(item.get("source_type") or "web").strip().lower()
    source_label = "公众号" if source_type == "wechat" else str(item.get("source_name") or "公开来源")
    source_url = esc(item.get("source_url"))
    return (
        '<div class="peer-item">'
        f'<div class="peer-item-title"><span class="peer-item-type">{esc(item.get("type") or "其他")}</span>{esc(item.get("title"))}</div>'
        f'<div class="peer-item-meta">来源：{esc(source_label)}　发布时间：{esc(item.get("published_at"))}　'
        f'来源链接：<a href="{source_url}">原文</a></div>'
        f'<p class="peer-item-summary">{esc(item.get("summary"))}</p>'
        '</div>'
    )


def peer_rows(peers: dict) -> tuple[list[dict[str, str]], int, int]:
    config = peers.get("config") or {}
    groups = peers.get("items") or []
    by_name: dict[str, list[dict]] = {}
    order: list[str] = []
    for group in groups:
        name = str(group.get("org_name") or "").strip()
        if not name:
            continue
        if name not in by_name:
            by_name[name] = []
            order.append(name)
        by_name[name].extend(group.get("items") or [])

    configured = []
    for name in (config.get("general") or DEFAULT_PEER_GENERAL) + (config.get("domain_specific") or []):
        name = str(name).strip()
        if name and name not in configured:
            configured.append(name)
    for name in configured:
        by_name.setdefault(name, [])
    if not by_name:
        by_name = {name: [] for name in DEFAULT_PEER_GENERAL}

    # 只展示本周有可核验动态的同行单位；无动态单位不进入目录和正文。
    names = [name for name in by_name if by_name[name]]
    names = sorted(names)
    # Dynamic units按动态数量和最新发布时间排序。
    names.sort(key=lambda name: max((str(item.get("published_at") or "") for item in by_name[name]), default=""), reverse=True)
    names.sort(key=lambda name: len(by_name[name]), reverse=True)
    names.sort(key=lambda name: not bool(by_name[name]))
    rows = []
    dynamic_count = 0
    for name in names:
        items = sorted(by_name[name], key=lambda item: str(item.get("published_at") or ""), reverse=True)
        dynamic_count += len(items)
        content = "".join(peer_item_html(item) for item in items)
        rows.append({"同行单位名称": esc(name), "同行动态内容": content})
    return rows, len(names), dynamic_count


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
  var charts = {{}};
  var chartOptions = {{}};
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
    var option = {{
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
    }};
    chart.setOption(option);
    charts[id] = chart;
    chartOptions[id] = {{ mapName: mapName, geo: geo, option: option }};
    chart.resize();
    if (window.ResizeObserver) {{
      new ResizeObserver(function() {{ chart.resize(); }}).observe(el);
    }}
    window.addEventListener('resize', function() {{ chart.resize(); }});
  }}
  function update(id, rows) {{
    var entry = chartOptions[id];
    var chart = charts[id];
    if (!entry || !chart) return;
    entry.option.series[0].data = align(rows || [], entry.geo);
    chart.setOption({{ series: [{{ data: entry.option.series[0].data }}] }});
    chart.resize();
  }}
  window.weeklyHeatmaps = {{
    update: function(rows) {{
      rows = rows || {{}};
      update('china-heatmap', rows.china);
      update('zhejiang-heatmap', rows.zhejiang);
    }}
  }};
  render('china-heatmap', 'china', payload.chinaGeo, payload.china, '86%');
  render('zhejiang-heatmap', 'zhejiang', payload.zhejiangGeo, payload.zhejiang, '78%');
}})();
</script>
"""


def remove_optional_sections(html_text: str) -> str:
    html_text = re.sub(r"\n\s*<div class=\"toc-section-label\"[^>]*data-toc-label=\"tender\".*?<div class=\"toc-section-label\"[^>]*data-toc-label=\"peers\"", "\n  <div class=\"toc-section-label\" data-toc-label=\"peers\"", html_text, flags=re.S)
    html_text = re.sub(r"\n<!-- ═══════════════ (?:本周招标信息|招标信息) ═══════════════ -->.*?<!-- ═══════════════ 同行动态 ═══════════════ -->", "\n<!-- ═══════════════ 同行动态 ═══════════════ -->", html_text, flags=re.S)
    return html_text


def fill(report: dict, template: Path) -> str:
    meta = report.get("meta") or {}
    html_text = replace_article_paragraphs(template.read_text(encoding="utf-8"))

    analysis = report.get("analysis") or []
    selected = report.get("selected") or report.get("highlights_news") or []
    business_radar = report.get("business_radar") or []
    tenders = report.get("tenders") or []
    peer_config = report.get("peers") or {"config": {"general": DEFAULT_PEER_GENERAL}}
    peer_render_rows, peer_org_count, peer_dynamic_count = peer_rows(peer_config)

    simple = {
        "文档标题": meta.get("title") or f"{meta.get('domain', '')}本周热点分析",
        "作者": meta.get("author") or "",
        "摘要": meta.get("description") or "",
        "关键词": meta.get("keywords") or meta.get("domain") or "",
        "生成时间": generated_at(meta),
        "报告短标题": meta.get("short_title") or f"{meta.get('domain', '')}本周热点分析",
        "报告短摘要": report.get("summary") or meta.get("description") or "",
        "领域标签 · 如 \"现代物流\" / \"新能源\"": meta.get("label") or meta.get("domain") or "",
        "领域标签": meta.get("label") or meta.get("domain") or "",
        "领域": meta.get("domain") or "",
        "开始日期": meta.get("start_date") or "",
        "结束日期": meta.get("end_date") or "",
        "入选资讯数": meta.get("item_count") or len(analysis) + len(selected),
        "分类数": meta.get("category_count") or "",
        "招标栏目导语": report.get("tender_intro") or "本栏目收录本周可核验、与主题相关的招标采购项目。",
        "招标收录口径": report.get("tender_note") or "收录口径：投标截止日、文件获取期或发布日期落在统计周期内，且附可访问原文链接的项目。",
        "全国热力图摘要": report.get("china_heatmap_summary") or "",
        "浙江热力图摘要": report.get("zhejiang_heatmap_summary") or "",
        "同行单位数": peer_org_count,
        "同行动态数": peer_dynamic_count,
        "要点数量": len(report.get("highlights") or []),
        "招标数量": len(tenders),
        "最大招标金额": max_budget_display(tenders),
        "周次": week_label(meta),
        "页码信息": "",
        "招标目录条目": "",
        "招标表格或空状态": dashboard_tender_table(tenders),
        "ECharts脚本": "",
    }

    html_text = loop(html_text, "HIGHLIGHT_LOOP", [
        {"要点序号": str(i), "要点关键词": esc(item.get("keyword")), "要点正文": esc(item.get("body"))}
        for i, item in enumerate(report.get("highlights", []), 1)
    ])
    html_text = loop(html_text, "TOC_ANALYSIS_LOOP", [
        {"序号": str(i), "分析专栏编辑主题标题": esc(item.get("title"))}
        for i, item in enumerate(analysis, 1)
    ])
    html_text = loop(html_text, "TOC_SELECTED_LOOP", [
        {"序号": str(i), "优选信息编辑主题标题": esc(item.get("title"))}
        for i, item in enumerate(selected, 1)
    ])
    category_groups = selected_category_groups(selected)
    html_text = category_loop(html_text, "TOC_CATEGORY_LOOP", "TOC_SELECTED_ITEM_LOOP", category_groups)
    html_text = category_loop(html_text, "SELECTED_CATEGORY_LOOP", "SELECTED_ITEM_IN_CATEGORY_LOOP", category_groups)
    html_text = loop(html_text, "TOC_PEER_LOOP", [
        {"序号": str(i), "同行单位名称": row["同行单位名称"]}
        for i, row in enumerate(peer_render_rows, 1)
    ])
    html_text = loop(html_text, "TOC_RADAR_LOOP", [
        {"序号": str(i), "业务雷达标题": esc(item.get("title"))}
        for i, item in enumerate(business_radar, 1)
    ])
    html_text = loop(html_text, "ANALYSIS_ARTICLE_LOOP", section_items(analysis))
    html_text = loop(html_text, "SELECTED_ITEM_LOOP", section_items(selected))
    html_text = loop(html_text, "PEER_ORG_LOOP", peer_render_rows)
    html_text = loop(html_text, "RADAR_ADVISORY_LOOP", radar_rows([item for item in business_radar if item.get("radar_type") == "咨政建言"]))
    html_text = loop(html_text, "RADAR_BUSINESS_LOOP", radar_rows([item for item in business_radar if item.get("radar_type") == "业务拓展"]))
    html_text = loop(html_text, "RADAR_FORWARD_LOOP", radar_rows([item for item in business_radar if item.get("radar_type") == "前瞻研究"]))

    if tenders:
        html_text = loop(html_text, "TENDER_ROW_LOOP", [
            {
                "序号": str(i),
                "项目名称": esc(item.get("project_name")),
                "采购主体": esc(item.get("purchaser")),
                "地区": esc(item.get("region")),
                "城市": esc(item.get("city")),
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
        chart_script = heatmap_script(china_rows, zhejiang_rows)
        if "{{ECharts脚本}}" in html_text:
            simple["ECharts脚本"] = chart_script
        else:
            html_text = html_text.replace("</body>", chart_script + "\n</body>")
        html_text = re.sub(r"\n<!-- ═══════════════ STANDALONE COLOPHON ═══════════════ -->\s*<section class=\"standalone-colophon\">.*?</section>\n", "\n", html_text, flags=re.S)
    else:
        html_text = loop(html_text, "TENDER_ROW_LOOP", [])
        html_text = remove_optional_sections(html_text)

    for key, value in simple.items():
        html_text = html_text.replace("{{" + key + "}}", esc(value) if key not in {"全国招标热力图", "浙江招标热力图", "招标表格或空状态", "ECharts脚本"} else str(value))
    if simple["周次"]:
        html_text = re.sub(r"\d{4}年第\d+周", esc(simple["周次"]), html_text)
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
