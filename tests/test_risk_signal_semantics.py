from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from axiomiq.cli import main as cli_main
from axiomiq.tools.generate_readings import generate_csv


def _fleet_min_health(tmp_path: Path, inject_failure: bool) -> float:
    data_dir = tmp_path / ("failure" if inject_failure else "healthy")
    out_dir = tmp_path / ("failure_out" if inject_failure else "healthy_out")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    readings = data_dir / "case.csv"
    json_out = out_dir / "case.json"
    pdf_out = out_dir / "case.pdf"
    snap_out = out_dir / "case_snapshot.csv"

    failure_event = {
        "engine_id": "DG1",
        "param": "charge_air_pressure_bar",
        "drift_per_step": -0.2,
        "start_step": 2,
    } if inject_failure else None

    generate_csv(
        out_path=readings,
        start=datetime.fromisoformat("2026-01-01T00:00:00"),
        days=3,
        step_hours=6,
        engines=["DG1", "DG2", "DG3"],
        seed=1,
        profile="healthy",  # always valid
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

    healths = [float(row["health"]) for row in table]
    return min(healths)


def test_injected_failure_reduces_worst_engine_health(tmp_path: Path) -> None:
    healthy_min = _fleet_min_health(tmp_path, inject_failure=False)
    failure_min = _fleet_min_health(tmp_path, inject_failure=True)

    assert failure_min < healthy_min