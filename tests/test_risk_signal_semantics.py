from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from axiomiq.cli import main as cli_main
from axiomiq.tools.generate_readings import generate_csv


def _fleet_min_health(tmp_path: Path, profile: str) -> float:
    data_dir = tmp_path / profile
    out_dir = tmp_path / f"{profile}_out"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    readings = data_dir / "case.csv"
    json_out = out_dir / "case.json"
    pdf_out = out_dir / "case.pdf"
    snap_out = out_dir / "case_snapshot.csv"

    generate_csv(
        out_path=readings,
        start=datetime.fromisoformat("2026-01-01T00:00:00"),
        days=3,
        step_hours=6,
        engines=["DG1", "DG2", "DG3"],
        seed=1,
        profile=profile,
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
        ]
    )
    assert rc == 0
    assert json_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    table = data["fleet"]["table"]
    assert isinstance(table, list) and table, "fleet.table must be a non-empty list"

    healths = [float(row["health"]) for row in table]
    return min(healths)


def test_degraded_profile_reduces_worst_engine_health(tmp_path: Path) -> None:
    healthy_min = _fleet_min_health(tmp_path, profile="healthy")
    degraded_min = _fleet_min_health(tmp_path, profile="failure")
    
    # Degraded should be strictly worse (lower health) than healthy.
    assert degraded_min < healthy_min