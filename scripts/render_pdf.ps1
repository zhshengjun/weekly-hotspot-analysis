param(
  [string]$ReportJson = "examples/sample-weekly-report.json",
  [string]$OutputPdf = "output/pdf/report.pdf"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Test-ReportLab($Python) {
  try {
    & $Python -c "import reportlab" *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Find-Python {
  $homeDir = [Environment]::GetFolderPath("UserProfile")
  $candidates = @(
    $env:WEEKLY_PDF_PYTHON,
    $env:CODEX_PYTHON,
    (Join-Path $homeDir ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    (Join-Path $homeDir ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\bin\python3"),
    "python",
    "python3"
  ) | Where-Object { $_ }

  foreach ($candidate in $candidates) {
    if (Test-ReportLab $candidate) {
      return $candidate
    }
  }
  return $null
}

$Python = Find-Python
if (-not $Python) {
  Write-Error "No Python runtime with reportlab found. Deliver Markdown instead of claiming PDF output."
  exit 2
}

$Rendered = & $Python (Join-Path $Root "scripts/render_weekly_pdf.py") $ReportJson -o $OutputPdf
if (-not (Test-Path $OutputPdf)) {
  Write-Error "PDF was not created: $OutputPdf"
  exit 1
}

& $Python -c "import pdfplumber" *> $null
if ($LASTEXITCODE -eq 0) {
  $checkScript = @'
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
'@
  & $Python -c $checkScript $ReportJson $OutputPdf
}

Write-Output $OutputPdf
