# scripts/demo.ps1

param(
  [switch]$Reinstall,     # re-run pip install -e .
  [switch]$Open,          # open PDF when done
  [switch]$InjectFailure  # inject correlated failure into DG3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Always run from repo root (even if launched elsewhere)
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

# ---- Activate venv (required) ----
$venvActivate = Join-Path $ROOT ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
  & $venvActivate
} else {
  throw ".venv not found at $venvActivate. Create/restore your venv first."
}

# ---- Ensure editable install so console scripts exist ----
if ($Reinstall) {
  python -m pip install -e . | Out-Null
}

# ---- Paths ----
$READINGS  = "data/readings.csv"
$REPORT    = "outputs/axiomiq_report.pdf"
$SNAPSHOT  = "outputs/last_snapshot.csv"
$JSON      = "outputs/axiomiq_report.json"

$ENGINES   = "DG1,DG2,DG3,DG4,DG5,DG6"
$START     = "2026-01-01T00:00:00"
$DAYS      = 90
$STEP_HRS  = 1
$PROFILE   = "demo"
$SEED      = 42

# Ensure dirs exist
New-Item -ItemType Directory -Force -Path "data"    | Out-Null
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

# ---- Ensure console entrypoints exist ----
$haveAxiomiq = Get-Command axiomiq -ErrorAction SilentlyContinue
$haveGen     = Get-Command axiomiq-generate -ErrorAction SilentlyContinue
$haveValidate= Get-Command axiomiq-validate-json -ErrorAction SilentlyContinue

if (-not $haveAxiomiq -or -not $haveGen -or -not $haveValidate) {
  Write-Host "Console commands missing. Running editable install..." -ForegroundColor Yellow
  python -m pip install -e . | Out-Null
}

# ---- Generate deterministic demo dataset ----
if ($InjectFailure) {
  axiomiq-generate `
    --out $READINGS `
    --start $START `
    --days $DAYS `
    --step-hours $STEP_HRS `
    --engines $ENGINES `
    --profile $PROFILE `
    --seed $SEED `
    --inject-failure `
    --failure-engine "DG3" `
    --failure-start-day 20 `
    --failure-ramp-days 14 `
    --failure-severity 0.8 `
    --failure-mode air_intake_restriction `
    --print-summary
}
else {
  axiomiq-generate `
    --out $READINGS `
    --start $START `
    --days $DAYS `
    --step-hours $STEP_HRS `
    --engines $ENGINES `
    --profile $PROFILE `
    --seed $SEED `
    --print-summary
}

# ---- Run analysis + PDF + JSON ----
axiomiq `
  --input $READINGS `
  --out $REPORT `
  --snapshot $SNAPSHOT `
  --json $JSON

# ---- Strict JSON validation (fail hard if invalid) ----
axiomiq-validate-json $JSON

Write-Host ""
Write-Host "PDF  -> $REPORT"
Write-Host "JSON -> $JSON"
Write-Host "SNAP -> $SNAPSHOT"

if ($Open) {
  Start-Process $REPORT
}
