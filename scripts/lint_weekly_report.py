#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


REQUIRED_PARTS = ("统计周期", "核心摘要", "本周焦点", "分类热点分析", "总体判断")
FORBIDDEN_PATTERNS = (
    r"来源明细表",
    r"候选统计",
    r"搜索入口统计",
    r"TODO|TBD",
    r"\[来源名称\]",
    r"\(原文链接\)",
    r"\{[^}\n]+\}",
)


def category_count(text: str) -> int:
    match = re.search(r"分类热点分析(?P<body>.*?)(?:\n#{1,3}\s*总体判断|\n总体判断|$)", text, re.S)
    if not match:
        return 0
    body = match.group("body")
    headings = re.findall(r"^#{3,4}\s+\S+", body, re.M)
    return len(headings)


def lint(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors = []
    for part in REQUIRED_PARTS:
        if part not in text:
            errors.append(f"missing section: {part}")
    if not re.search(r"统计周期[：:]\s*\d{4}-\d{2}-\d{2}\s*(?:至|-|到)\s*\d{4}-\d{2}-\d{2}", text):
        errors.append("missing concrete period range")
    count = category_count(text)
    if not 3 <= count <= 6:
        errors.append(f"category count must be 3-6, got {count}")
    source_lines = [line for line in text.splitlines() if "来源：" in line or "来源:" in line]
    if not source_lines:
        errors.append("missing item source lines")
    for line in source_lines:
        if not re.search(r"来源[：:]\s*\[[^\]]+\]\(https?://[^)]+\)", line):
            errors.append(f"source is not a markdown link: {line.strip()}")
        if not re.search(r"发布时间[：:]\s*\d{4}-\d{2}-\d{2}", line):
            errors.append(f"source line missing published date: {line.strip()}")
    if not re.search(r"AI摘要[：:]", text):
        errors.append("missing AI summaries")
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.I):
            errors.append(f"forbidden placeholder or debug output: {pattern}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a weekly hotspot Markdown report.")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    errors = lint(args.report)
    if errors:
        print("Weekly report lint failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
