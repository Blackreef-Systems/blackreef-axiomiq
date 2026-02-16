from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path


def _run_module(module: str, argv: list[str]) -> int:
    """
    Run a module as if invoked via `python -m <module> ...` but in-process,
    so coverage counts. Returns the SystemExit code (0 for success).
    """
    old_argv = sys.argv[:]
    try:
        sys.argv = [module, *argv]
        try:
            runpy.run_module(module, run_name="__main__")
            return 0
        except SystemExit as e:
            # argparse / CLI typically exits via SystemExit
            return int(e.code) if e.code is not None else 0
    finally:
        sys.argv = old_argv


def test_tools_generate_readings_module_runs(tmp_path: Path) -> None:
    """
    Covers axiomiq.tools.generate_readings (currently 0%).
    """
    out_csv = tmp_path / "check.csv"

    rc = _run_module(
        "axiomiq.tools.generate_readings",
        [
            "--out",
            str(out_csv),
            "--days",
            "2",
            "--step-hours",
            "12",
            "--seed",
            "1",
            "--profile",
            "healthy",
        ],
    )
    assert rc == 0
    assert out_csv.exists()
    assert out_csv.stat().st_size > 0


def test_cli_module_generates_json_strict(tmp_path: Path) -> None:
    """
    Covers axiomiq.cli + json_report integration.
    Validates the JSON artifact is strict (no NaN/Infinity).
    """
    data_csv = tmp_path / "check.csv"
    out_pdf = tmp_path / "check.pdf"
    out_snapshot = tmp_path / "check_snapshot.csv"
    out_json = tmp_path / "check.json"

    # 1) Generate dataset (in-process, counts toward coverage)
    rc = _run_module(
        "axiomiq.tools.generate_readings",
        [
            "--out",
            str(data_csv),
            "--days",
            "2",
            "--step-hours",
            "12",
            "--seed",
            "1",
            "--profile",
            "healthy",
        ],
    )
    assert rc == 0
    assert data_csv.exists()

    # 2) Run main CLI (in-process, counts toward coverage)
    rc = _run_module(
        "axiomiq.cli",
        [
            "--input",
            str(data_csv),
            "--out",
            str(out_pdf),
            "--snapshot",
            str(out_snapshot),
            "--json-out",
            str(out_json),
        ],
    )
    assert rc == 0

    # artifacts exist
    assert out_pdf.exists()
    assert out_snapshot.exists()
    assert out_json.exists()
    assert out_json.stat().st_size > 0

    # strict JSON validation: reject NaN/Infinity by failing parse_constant
    raw = out_json.read_text(encoding="utf-8")

    def _reject_constants(x: str):
        raise ValueError(f"Non-JSON constant encountered: {x}")

    obj = json.loads(raw, parse_constant=_reject_constants)
    assert isinstance(obj, dict)
    # keep this loose to avoid schema churn, but ensure core keys exist if you have them
    # (optional) assert any(k in obj for k in ("meta", "fleet", "focus", "notes"))
