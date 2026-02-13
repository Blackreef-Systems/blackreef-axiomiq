Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

# Activate venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
  & $venvActivate
} else {
  throw "Virtual environment not found"
}

# Editable install
python -m pip install -e . | Out-Null

# Smoke import (PowerShell-safe)
python -c "import axiomiq; import axiomiq.cli; print('Imports OK')" | Out-Null

# CLI availability
axiomiq --help | Out-Null
axiomiq-generate --help | Out-Null

# Fast smoke run (short window)
axiomiq-generate `
  --out data/_check.csv `
  --days 3 `
  --step-hours 6 `
  --seed 1 `
  --profile healthy | Out-Null

axiomiq `
  --input data/_check.csv `
  --out outputs/_check.pdf | Out-Null

Write-Host "CHECK PASSED ✔"