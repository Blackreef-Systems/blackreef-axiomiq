from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from axiomiq.cli import main as cli_main
from axiomiq.tools.generate_readings import generate_csv
from axiomiq.tools.validate_json import validate_json


def test_cli_end_to_end_generates_pdf_json_snapshot(tmp_path: Path) -> None:
    # --- Arrange: generate a small deterministic dataset ---
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

    assert readings.exists()
    assert readings.stat().st_size > 0

    # --- Act: run CLI in-process ---
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

    # --- Assert: artifacts exist ---
    assert rc == 0
    assert pdf_out.exists() and pdf_out.stat().st_size > 0
    assert json_out.exists() and json_out.stat().st_size > 0
    assert snap_out.exists() and snap_out.stat().st_size > 0

    # --- Assert: strict JSON + required top-level keys ---
    validate_json(json_out)

    obj = json.loads(Path(json_out).read_text(encoding="utf-8"))
    assert isinstance(obj, dict)
    assert set(("meta", "fleet", "focus", "notes")).issubset(obj.keys())
    assert isinstance(obj["fleet"].get("table", []), list)