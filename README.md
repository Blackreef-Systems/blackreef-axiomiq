# Blackreef AxiomIQ

![Smoke](https://github.com/Blackreef-Systems/blackreef-axiomiq/actions/workflows/smoke.yml/badge.svg)
![Quality](https://github.com/Blackreef-Systems/blackreef-axiomiq/actions/workflows/quality.yml/badge.svg)

Fleet drift analytics for marine diesel generator sets.

---

## Quickstart (Windows PowerShell)

```powershell
# from repo root
.\scripts\demo.ps1 -Reinstall -Open
```

---

## Quickstart (Manual Setup)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .

axiomiq-generate --out data/readings.csv --days 30 --profile healthy
axiomiq --input data/readings.csv --out outputs/report.pdf
```

---

## What It Does

- Generates realistic diesel generator telemetry
- Detects performance drift patterns
- Produces operational PDF reports
- Estimates time-to-limit for developing risk indicators
- Runs cross-platform in CI (Windows + Ubuntu)

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
```
