#!/usr/bin/env python3
"""Validate weekly hotspot analysis HTML.

Usage:
  python3 scripts/build.py report.html
  python3 scripts/build.py report.html --report-json report.json
  python3 scripts/build.py --check-placeholders report.html

This script only validates HTML. Export PDF from the browser preview.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


SCORE_FIELDS = (
    "tier1_source_authority",
    "tier1_info_density",
    "tier1_domain_relevance",
    "tier1_total",
    "tier2_timeliness",
    "tier2_influence",
    "tier2_scarcity",
    "tier2_total",
    "composite",
)


def check_placeholders(html_path: str) -> bool:
    """Scan HTML for residual {{...}} placeholders. Returns True if clean."""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all {{...}} patterns, excluding CSS custom properties (no spaces around var())
    placeholders = re.findall(r'\{\{[^}]+?\}\}', content)
    if placeholders:
        print(f"[FAIL] Found {len(placeholders)} residual placeholder(s):")
        for p in placeholders:
            print(f"  - {p}")
        return False
    print("[PASS] No residual placeholders found.")
    return True


def check_structure(html_path: str) -> bool:
    """Verify mandatory HTML sections exist."""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    required = [
        ('cover section', '.cover'),
        ('highlights section', '.highlights'),
        ('TOC section', '.toc'),
        ('analysis chapter', '分析专栏'),
        ('selected-info chapter', '优选信息'),
        ('source metadata', 'source-meta'),
        ('colophon', 'colophon'),
    ]
    all_ok = True
    for name, marker in required:
        if marker not in content:
            print(f"[FAIL] Missing required section: {name}")
            all_ok = False
        else:
            print(f"[PASS] Section '{name}' found.")
    return all_ok


def score_value(scores: dict, key: str) -> float | None:
    value = scores.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def close_enough(actual: float | None, expected: float, tolerance: float = 0.2) -> bool:
    return actual is not None and abs(actual - expected) <= tolerance


def check_report_json(report_path: str, html_path: str) -> bool:
    """Verify selected news scoring fields and formula."""
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    html_text = Path(html_path).read_text(encoding="utf-8")
    selected = data.get("selected") or data.get("highlights_news") or []
    if not selected:
        print("[WARN] No selected news found in report.json; scoring check skipped.")
        all_ok = True
    else:
        all_ok = True
        if len(selected) < 8 or len(selected) > 15:
            print(f"[FAIL] Selected news count must be 8 to 15 items; got {len(selected)}.")
            all_ok = False
        selected_domains = []
        source_names = []
        tender_like_count = 0
        source_types = []
        for index, item in enumerate(selected, 1):
            domain = urlparse(item.get("source_url", "")).netloc.lower()
            if domain:
                selected_domains.append(domain.removeprefix("www."))
            source_name = str(item.get("source_name", "")).strip()
            if source_name:
                source_names.append(source_name)
            source_type = str(item.get("source_type", "")).strip().lower()
            if source_type:
                source_types.append(source_type)
            if is_tender_like_selected(item):
                tender_like_count += 1

            scores = item.get("scores")
            title = item.get("title") or f"selected #{index}"
            if not isinstance(scores, dict):
                print(f"[FAIL] Missing scores for selected item {index}: {title}")
                all_ok = False
                continue

            missing = [field for field in SCORE_FIELDS if field not in scores]
            if missing:
                print(f"[FAIL] Incomplete scores for selected item {index}: {title}; missing {', '.join(missing)}")
                all_ok = False
                continue

            source = score_value(scores, "tier1_source_authority")
            density = score_value(scores, "tier1_info_density")
            relevance = score_value(scores, "tier1_domain_relevance")
            timeliness = score_value(scores, "tier2_timeliness")
            influence = score_value(scores, "tier2_influence")
            scarcity = score_value(scores, "tier2_scarcity")
            indicator_values = [source, density, relevance, timeliness, influence, scarcity]
            if any(value is None or value < 1 or value > 5 for value in indicator_values):
                print(f"[FAIL] Score indicators must be numbers from 1 to 5 for selected item {index}: {title}")
                all_ok = False
                continue

            tier1 = (source * 0.35 + density * 0.40 + relevance * 0.25) * 20
            tier2 = (timeliness * 0.30 + influence * 0.35 + scarcity * 0.35) * 20
            composite = tier1 * 0.40 + tier2 * 0.60
            if not close_enough(score_value(scores, "tier1_total"), tier1):
                print(f"[FAIL] tier1_total formula mismatch for selected item {index}: {title}")
                all_ok = False
            if not close_enough(score_value(scores, "tier2_total"), tier2):
                print(f"[FAIL] tier2_total formula mismatch for selected item {index}: {title}")
                all_ok = False
            if not close_enough(score_value(scores, "composite"), composite):
                print(f"[FAIL] composite formula mismatch for selected item {index}: {title}")
                all_ok = False

        domain_counts = Counter(selected_domains)
        if len(domain_counts) < 3:
            print("[FAIL] Selected news must cover at least 3 source domains.")
            all_ok = False
        if domain_counts:
            domain, count = domain_counts.most_common(1)[0]
            if count > 2:
                print(f"[FAIL] Selected news uses one source domain more than 2 times: {domain} ({count}/{len(selected)}).")
                all_ok = False
            if count / len(selected) > 0.60:
                print(f"[FAIL] Selected news is over-concentrated on one source domain: {domain} ({count}/{len(selected)}).")
                all_ok = False
        source_name_counts = Counter(source_names)
        if source_name_counts:
            source_name, count = source_name_counts.most_common(1)[0]
            if count > 2:
                print(f"[FAIL] Selected news uses one source more than 2 times: {source_name} ({count}/{len(selected)}).")
                all_ok = False
        source_type_counts = Counter(source_types)
        if source_type_counts:
            source_type, count = source_type_counts.most_common(1)[0]
            if count > len(selected) / 2:
                print(f"[FAIL] Selected news is over-concentrated on one source type: {source_type} ({count}/{len(selected)}).")
                all_ok = False
        if tender_like_count > len(selected) / 2:
            print(f"[FAIL] Tender/procurement-like items dominate selected news ({tender_like_count}/{len(selected)}).")
            all_ok = False

    tenders = data.get("tenders") or []
    tender_markers = ("tender-table", "本周招标信息", "地理空间热力图", "china-heatmap", "zhejiang-heatmap")
    if tenders:
        missing = [marker for marker in tender_markers if marker not in html_text]
        if missing:
            print(f"[FAIL] Tender data exists but HTML is missing: {', '.join(missing)}")
            all_ok = False
        else:
            print("[PASS] Tender table and China/Zhejiang heatmaps are present.")
    elif any(marker in html_text for marker in tender_markers):
        print("[FAIL] No tender data exists but tender/heatmap sections are present.")
        all_ok = False

    if all_ok:
        print("[PASS] Selected news scoring fields and formulas are valid.")
    return all_ok


def is_tender_like_selected(item: dict) -> bool:
    source_type = str(item.get("source_type", "")).lower()
    if source_type in {"tender", "procurement", "bid"}:
        return True
    text = " ".join(
        str(item.get(key, ""))
        for key in ("title", "source_name", "summary")
    )
    return any(word in text for word in ("招标", "采购", "投标", "中标", "竞价", "磋商", "谈判", "询价"))


def main():
    parser = argparse.ArgumentParser(description="Validate weekly hotspot analysis HTML")
    parser.add_argument("html", help="Path to filled HTML file")
    parser.add_argument("--report-json", help="Optional report.json path for selected-news scoring validation")
    parser.add_argument("--check-placeholders", action="store_true", help="Only check for residual {{...}}")

    args = parser.parse_args()

    html_path = args.html
    if not Path(html_path).exists():
        print(f"[FAIL] File not found: {html_path}")
        sys.exit(1)

    print(f"[INFO] Checking: {html_path}\n")

    # Always run placeholder check
    clean = check_placeholders(html_path)
    if not clean:
        sys.exit(1)

    if args.check_placeholders:
        sys.exit(0 if clean else 1)

    structure_ok = check_structure(html_path)
    if not structure_ok:
        sys.exit(1)

    if args.report_json and not check_report_json(args.report_json, html_path):
        sys.exit(1)

    print("\n[PASS] HTML is browser-ready. Export PDF from the browser if needed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
