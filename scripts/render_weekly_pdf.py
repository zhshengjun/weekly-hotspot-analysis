#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLE_PATH = ROOT / "references" / "pdf-style-template.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hex_color(value: str):
    return colors.HexColor(value)


def blend_color(start: str, end: str, amount: float):
    a = hex_color(start)
    b = hex_color(end)
    return colors.Color(
        a.red + (b.red - a.red) * amount,
        a.green + (b.green - a.green) * amount,
        a.blue + (b.blue - a.blue) * amount,
    )


def asym_round_rect(canvas, x, y, width, height, radii, fill=1, stroke=0):
    tl, tr, br, bl = radii
    k = 0.55228475
    p = canvas.beginPath()
    p.moveTo(x + tl, y + height)
    p.lineTo(x + width - tr, y + height)
    p.curveTo(x + width - tr + tr * k, y + height, x + width, y + height - tr + tr * k, x + width, y + height - tr)
    p.lineTo(x + width, y + br)
    p.curveTo(x + width, y + br - br * k, x + width - br + br * k, y, x + width - br, y)
    p.lineTo(x + bl, y)
    p.curveTo(x + bl - bl * k, y, x, y + bl - bl * k, x, y + bl)
    p.lineTo(x, y + height - tl)
    p.curveTo(x, y + height - tl + tl * k, x + tl - tl * k, y + height, x + tl, y + height)
    p.close()
    canvas.drawPath(p, stroke=stroke, fill=fill)


def text(value) -> str:
    return str(value or "").strip()


def pick(data: dict, *keys: str) -> str:
    for key in keys:
        value = text(data.get(key))
        if value:
            return value
    return ""


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._").lower()


def register_font(style: dict) -> str:
    font = style.get("font", {})
    name = font.get("name", "ReportFont")
    for candidate in font.get("candidates", []):
        path = Path(candidate).expanduser()
        if not path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
        except Exception:
            continue
    fallback = font.get("fallback_cid", "STSong-Light")
    pdfmetrics.registerFont(UnicodeCIDFont(fallback))
    return fallback


def mm_box(margins: dict) -> tuple[float, float, float, float]:
    return (
        float(margins.get("left", 14)) * mm,
        float(margins.get("right", 14)) * mm,
        float(margins.get("top", 14)) * mm,
        float(margins.get("bottom", 16)) * mm,
    )


def focus_items(report: dict) -> list[str]:
    raw = report.get("weekly_focus") or report.get("focuses") or report.get("focus") or []
    if isinstance(raw, str):
        return [raw]
    return [text(item.get("summary") or item.get("title") or item) if isinstance(item, dict) else text(item) for item in raw]


def date_parts(value: str) -> tuple[str, str]:
    value = text(value)
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
    if match:
        return match.group(3).zfill(2), f"{int(match.group(2))}月"
    match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", value)
    if match:
        return match.group(2).zfill(2), f"{int(match.group(1))}月"
    return value[:6] or "-", ""


def cn_number(index: int) -> str:
    nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    return nums[index - 1] if 1 <= index <= len(nums) else str(index)


def styles(font_name: str, palette: dict) -> dict:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName=font_name, fontSize=10.5,
            leading=17, textColor=hex_color(palette["text"]), alignment=TA_LEFT
        ),
        "analysis": ParagraphStyle(
            "Analysis", parent=base["Normal"], fontName=font_name, fontSize=10,
            leading=16, textColor=hex_color(palette["text"]), alignment=TA_LEFT
        ),
        "event_title": ParagraphStyle(
            "EventTitle", parent=base["Normal"], fontName=font_name, fontSize=12.2,
            leading=16, textColor=hex_color("#14233c"), alignment=TA_LEFT
        ),
        "event_desc": ParagraphStyle(
            "EventDesc", parent=base["Normal"], fontName=font_name, fontSize=10.5,
            leading=17, textColor=hex_color(palette["text"]), alignment=TA_LEFT
        ),
    }


def para(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text(value)), style)


class Hero(Flowable):
    def __init__(self, report: dict, font_name: str, style: dict):
        super().__init__()
        self.report = report
        self.font_name = font_name
        self.style = style
        self.height = float(style.get("hero", {}).get("height_mm", 62)) * mm

    def wrap(self, avail_width, _avail_height):
        self.width = avail_width
        return avail_width, self.height

    def draw(self):
        c = self.canv
        colors_cfg = self.style["colors"]
        title = pick(self.report, "title") or "本周热点分析"
        domain = pick(self.report, "domain", "field")
        period = pick(self.report, "period") or " 至 ".join(filter(None, [pick(self.report, "period_start"), pick(self.report, "period_end")]))
        meta = "  ·  ".join(part for part in [period, domain] if part)
        kicker = pick(self.report, "kicker") or self.style.get("hero", {}).get("kicker", "WEEKLY HOTSPOT REPORT")

        c.saveState()
        c.setFillColor(hex_color(colors_cfg["hero"]))
        c.roundRect(0, 0, self.width, self.height, 10, stroke=0, fill=1)
        c.setFillColor(hex_color(colors_cfg["hero_accent"]))
        c.roundRect(self.width * 0.55, 0, self.width * 0.45, self.height, 10, stroke=0, fill=1)
        c.setStrokeColor(hex_color("#6ca4df"))
        c.setLineWidth(2)
        c.circle(self.width * 0.88, self.height * 0.62, 60, stroke=1, fill=0)
        c.circle(self.width * 0.83, self.height * 0.28, 42, stroke=1, fill=0)

        c.setFillColor(hex_color("#476da6"))
        c.roundRect(24, self.height - 36, 230, 18, 9, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.font_name, 10)
        c.drawString(34, self.height - 31, kicker)

        c.setFont(self.font_name, 31)
        c.drawString(24, self.height - 72, title)
        c.setFont(self.font_name, 13)
        c.drawString(24, 24, meta)
        c.restoreState()


class SectionHeading(Flowable):
    def __init__(self, title: str, font_name: str, color: str):
        super().__init__()
        self.title = title
        self.font_name = font_name
        self.color = color
        self.height = 25

    def wrap(self, avail_width, _avail_height):
        self.width = avail_width
        return avail_width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(hex_color(self.color))
        pill_w = max(86, min(190, pdfmetrics.stringWidth(self.title, self.font_name, 12) + 28))
        asym_round_rect(c, 0, 1, pill_w, 22, (4, 12, 4, 12), stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.font_name, 12)
        c.drawString(13, 7, self.title)
        start_x = pill_w + 10
        end_x = self.width
        segments = 28
        for index in range(segments):
            t1 = index / segments
            t2 = (index + 1) / segments
            x1 = start_x + (end_x - start_x) * t1
            x2 = start_x + (end_x - start_x) * t2
            c.setStrokeColor(blend_color(self.color, "#ffffff", min(0.92, t1 * 1.05)))
            c.setLineWidth(2.2 - 1.8 * t1)
            c.line(x1, 12, x2, 12)


class BulletItem(Flowable):
    def __init__(self, value: str, st: dict, style: dict):
        super().__init__()
        self.value = value
        self.st = st
        self.style = style

    def wrap(self, avail_width, _avail_height):
        self.width = avail_width
        self.paragraph = para(self.value, self.st["body"])
        _, para_h = self.paragraph.wrap(avail_width - 16, 1000)
        self.height = para_h + 3
        return avail_width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(hex_color(self.style["colors"]["text"]))
        c.circle(4, self.height - 8, 1.6, stroke=0, fill=1)
        self.paragraph.drawOn(c, 16, self.height - self.paragraph.height)


class EventItem(Flowable):
    def __init__(self, item: dict, font_name: str, st: dict, style: dict):
        super().__init__()
        self.item = item
        self.font_name = font_name
        self.st = st
        self.style = style

    def wrap(self, avail_width, _avail_height):
        self.width = avail_width
        right_w = avail_width - 58
        source = pick(self.item, "source_name", "source")
        source_url = pick(self.item, "source_url", "url", "link")
        title = escape(pick(self.item, "title"))
        if source and source_url:
            source_html = f" <a href={quoteattr(source_url)}><font color='#9aa8b8'>{escape(source)}</font></a>"
        else:
            source_html = f" <font color='#9aa8b8'>{escape(source)}</font>" if source else ""
        self.title_p = Paragraph(f"<b>{title}</b>{source_html}", self.st["event_title"])
        _, title_h = self.title_p.wrap(right_w - (38 if self.is_highlight() else 0), 1000)
        summary = pick(self.item, "ai_summary", "summary")
        self.summary_p = para(summary, self.st["event_desc"]) if summary else None
        _, summary_h = self.summary_p.wrap(right_w, 1000) if self.summary_p else (0, 0)
        self.height = max(54, title_h + summary_h + 18)
        return avail_width, self.height

    def is_highlight(self) -> bool:
        return text(self.item.get("importance")) == "高" or bool(self.item.get("highlight"))

    def draw(self):
        c = self.canv
        day, month = date_parts(pick(self.item, "published_at", "date"))
        badge_w = 48
        badge_h = 42
        badge_y = (self.height - badge_h) / 2
        c.setFillColor(hex_color("#eef5fd"))
        c.setStrokeColor(hex_color("#d9e5f2"))
        c.roundRect(0, badge_y, badge_w, badge_h, 6, stroke=1, fill=1)
        c.setFillColor(hex_color("#1455a4"))
        c.setFont(self.font_name, 17)
        c.drawCentredString(badge_w / 2, badge_y + 23, day)
        c.setFillColor(hex_color("#6f8193"))
        c.setFont(self.font_name, 9)
        c.drawCentredString(badge_w / 2, badge_y + 9, month)

        x = 64
        title_top = self.height - 6
        title_x = x
        if self.is_highlight():
            badge_w = 28
            badge_h = 14
            line_h = self.st["event_title"].leading
            badge_y = title_top - line_h + (line_h - badge_h) / 2
            c.setFillColor(hex_color("#e04a4a"))
            c.roundRect(x, badge_y, badge_w, badge_h, 2, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont(self.font_name, 8)
            c.drawCentredString(x + badge_w / 2, badge_y + 4, "重点")
            title_x += 38
        y = title_top - self.title_p.height
        self.title_p.drawOn(c, title_x, y)
        y -= 5
        if self.summary_p:
            self.summary_p.drawOn(c, x, y - self.summary_p.height)
        c.setStrokeColor(hex_color("#dce7f3"))
        c.setDash(2, 2)
        c.line(0, 0, self.width, 0)
        c.setDash()


def build_story(report: dict, style: dict, font_name: str) -> list:
    st = styles(font_name, style["colors"])
    palette = style.get("section_palette") or ["#29549f"]
    story = [Hero(report, font_name, style), Spacer(1, 12)]

    summaries = [text(item) for item in report.get("core_summary", []) if text(item)]
    if summaries:
        story.extend([SectionHeading("核心摘要", font_name, palette[0]), Spacer(1, 5)])
        for item in summaries:
            story.append(BulletItem(item, st, style))
        story.append(Spacer(1, 10))

    focuses = [item for item in focus_items(report) if item]
    if focuses:
        story.extend([SectionHeading("本周焦点", font_name, palette[1 % len(palette)]), Spacer(1, 5)])
        for item in focuses:
            story.append(BulletItem(item, st, style))
        story.append(Spacer(1, 10))

    sections = report.get("sections") or []
    for index, section in enumerate(sections, 1):
        title = pick(section, "title", "category") or f"分类{index}"
        color = palette[(index - 1) % len(palette)]
        story.extend([SectionHeading(f"{cn_number(index)} · {title}", font_name, color), Spacer(1, 6)])
        analysis = pick(section, "analysis", "summary")
        if analysis:
            story.extend([para(analysis, st["analysis"]), Spacer(1, 6)])
        for item in section.get("items") or []:
            story.extend([EventItem(item, font_name, st, style), Spacer(1, 5)])
        story.append(Spacer(1, 8))

    judgement = pick(report, "overall_judgment", "overall_judgement", "judgement", "conclusion")
    if judgement:
        story.extend([SectionHeading("总体判断", font_name, palette[len(sections) % len(palette)]), Spacer(1, 5), para(judgement, st["body"])])
    return story


def render(report_path: Path, output_path: Path | None, style_path: Path) -> Path:
    report = load_json(report_path)
    style = load_json(style_path)
    font_name = register_font(style)
    output_name = slugify(pick(report, "title")) or slugify(report_path.stem) or "weekly-report"
    output_path = output_path or ROOT / "output" / "pdf" / f"{output_name}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    left, right, top, bottom = mm_box(style.get("page", {}).get("margin_mm", {}))
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title=pick(report, "title") or "本周热点分析",
    )
    doc.build(build_story(report, style, font_name))
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render weekly hotspot report JSON to PDF.")
    parser.add_argument("report_json", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE_PATH)
    args = parser.parse_args()
    print(render(args.report_json, args.output, args.style))


if __name__ == "__main__":
    main()
