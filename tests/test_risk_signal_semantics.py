from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from axiomiq.cli import main as cli_main
from axiomiq.tools.generate_readings import FailureEvent, generate_csv


def _engine_health(tmp_path: Path, inject_failure: bool, engine_id: str) -> float:
    data_dir = tmp_path / ("failure" if inject_failure else "healthy")
    out_dir = tmp_path / ("failure_out" if inject_failure else "healthy_out")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    readings = data_dir / "case.csv"
    json_out = out_dir / "case.json"
    pdf_out = out_dir / "case.pdf"
    snap_out = out_dir / "case_snapshot.csv"

    failure_event = (
        FailureEvent(
            mode="air_intake_restriction",
            engine_id="DG1",
            start_day=0,
            ramp_days=1,
            severity=0.9,
        )
        if inject_failure
        else None
    )

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
        failure_event=failure_event,
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
        ]
    )
    assert rc == 0
    assert json_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    table = data["fleet"]["table"]

    for row in table:
        if row["engine_id"] == engine_id:
            return float(row["health"])

    raise AssertionError(f"Engine {engine_id} not found in output")


def test_injected_failure_reduces_target_engine_health(tmp_path: Path) -> None:
    healthy_health = _engine_health(tmp_path, inject_failure=False, engine_id="DG1")
    failure_health = _engine_health(tmp_path, inject_failure=True, engine_id="DG1")

    assert failure_health < healthy_health