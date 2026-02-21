from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from axiomiq.cli import main as cli_main
from axiomiq.tools.generate_readings import generate_csv

from tests.helpers.json_normalize import normalize_report_json


FIXTURE_DIR = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURE_DIR / "golden_report.v1.json"


def test_golden_json_regression(tmp_path: Path) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    data_dir = tmp_path / "data"
    out_dir = tmp_path / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    readings = data_dir / "check.csv"
    pdf_out = out_dir / "check.pdf"
    json_out = out_dir / "check.json"
    snap_out = out_dir / "check_snapshot.csv"

    generate_csv(
        out_path=readings,
        start=datetime.fromisoformat("2026-01-01T00:00:00"),
        days=3,
        step_hours=6,
        engines=["DG1", "DG2", "DG3"],
        seed=1,
        profile="healthy",
        noise_override=None,
        print_summary=False,
        failure_event=None,
    )

    rc = cli_main(
        [
            "--input",
            str(readings),
            "--out",
            str(pdf_out),
            "--snapshot",
            str(snap_out),
            "--json",
            str(json_out),
            "--top-risks",
            "3",
        ]
    )
    assert rc == 0
    assert json_out.exists()

    got = json.loads(json_out.read_text(encoding="utf-8"))
    got_n = normalize_report_json(got)

    if not GOLDEN.exists():
        # First run: materialize fixture intentionally
        GOLDEN.write_text(json.dumps(got_n, indent=2, sort_keys=True), encoding="utf-8")
        raise AssertionError(f"Golden fixture created at {GOLDEN}. Re-run tests.")

    exp = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert got_n == exp