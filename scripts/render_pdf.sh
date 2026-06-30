#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_JSON="${1:-examples/sample-weekly-report.json}"
OUTPUT_PDF="${2:-output/pdf/report.pdf}"

find_python() {
  candidates="
${WEEKLY_PDF_PYTHON:-}
${CODEX_PYTHON:-}
$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
python3
python
"
  for candidate in $candidates; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import reportlab" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  echo "No Python runtime with reportlab found. Deliver Markdown instead of claiming PDF output." >&2
  exit 2
fi

RENDERED="$("$PYTHON" "$ROOT/scripts/render_weekly_pdf.py" "$REPORT_JSON" -o "$OUTPUT_PDF")"
test -f "$OUTPUT_PDF"

if "$PYTHON" -c "import pdfplumber" >/dev/null 2>&1; then
  "$PYTHON" -c '
import json
import sys
import pdfplumber

report_path, pdf_path = sys.argv[1], sys.argv[2]
report = json.load(open(report_path, encoding="utf-8"))
text = "\n".join(page.extract_text() or "" for page in pdfplumber.open(pdf_path).pages)
if text.strip():
    checks = [
        report.get("title", ""),
        (report.get("sections") or [{}])[0].get("title", ""),
        report.get("overall_judgment", "")[:12],
        ((report.get("sections") or [{}])[0].get("items") or [{}])[0].get("source_name", ""),
    ]
    missing = [value for value in checks if value and value not in text]
    if missing:
        raise SystemExit("PDF text check failed: " + ", ".join(missing))
' "$REPORT_JSON" "$OUTPUT_PDF"
fi

printf '%s\n' "$OUTPUT_PDF"
