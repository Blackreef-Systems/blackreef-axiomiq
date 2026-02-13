# scripts/demo.ps1

param(
  [switch]$Reinstall,   # re-run pip install -e .
  [switch]$Open,        # open PDF when done
  [switch]$InjectFailure
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
$ENGINES   = "DG1,DG2,DG3,DG4,DG5,DG6"
$START     = "2026-01-01T00:00:00"
$DAYS      = 90
$STEP_HRS  = 1
$AxiomiqProfile   = "demo"
$SEED      = 42

# Ensure dirs exist
New-Item -ItemType Directory -Force -Path "data"    | Out-Null
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

# ---- Sanity: console entrypoints exist ----
# (If you didn't run -Reinstall after changes, these can disappear)
$haveAxiomiq = Get-Command axiomiq -ErrorAction SilentlyContinue
$haveGen     = Get-Command axiomiq-generate -ErrorAction SilentlyContinue
if (-not $haveAxiomiq -or -not $haveGen) {
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
    --profile $AxiomiqProfile `
    --seed $SEED `
    --inject-failure `
    --failure-engine "DG3" `
    --failure-start-day 20 `
    --failure-ramp-days 14 `
    --failure-severity 0.8 `
    --failure-mode air_intake_restriction `
    --print-summary
} else {
  axiomiq-generate `
    --out $READINGS `
    --start $START `
    --days $DAYS `
    --step-hours $STEP_HRS `
    --engines $ENGINES `
    --profile $AxiomiqProfile `
    --seed $SEED `
    --print-summary
}

# ---- Run analysis + PDF ----
axiomiq `
  --input $READINGS `
  --out $REPORT `
  --snapshot $SNAPSHOT

Write-Host ""
Write-Host "DONE -> $REPORT"
Write-Host "SNAP -> $SNAPSHOT"

if ($Open) {
  Start-Process $REPORT
}