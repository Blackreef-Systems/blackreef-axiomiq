from __future__ import annotations

from pathlib import Path
import pandas as pd

from axiomiq.core.ingest import load_readings_csv
from axiomiq.core.baseline import compute_baseline
from axiomiq.core.drift import compute_zscore, add_limit_proximity, add_slope_per_day
from axiomiq.core.scoring import add_risk_score
from axiomiq.core.fleet import fleet_summary, fleet_verdict


def test_pipeline_smoke_load_to_verdict(tmp_path: Path) -> None:
    """
    Fast end-to-end sanity test:
    CSV -> ingest -> baseline -> drift -> scoring -> fleet summary -> verdict.
    """
    # Minimal synthetic dataset (2 engines, 2 timestamps, 2 params)
    rows = [
        ["2026-01-01 00:00:00", "DG1", 320, 1800, "charge_air_pressure_bar", "3.10", "bar", 0, 3.5],
        ["2026-01-01 00:00:00", "DG1", 320, 1800, "htcw_engine_outlet_temp_c", "82.00", "c", 0, 90],
        ["2026-01-01 01:00:00", "DG1", 320, 1800, "charge_air_pressure_bar", "3.05", "bar", 0, 3.5],
        ["2026-01-01 01:00:00", "DG1", 320, 1800, "htcw_engine_outlet_temp_c", "83.00", "c", 0, 90],
        ["2026-01-01 00:00:00", "DG2", 320, 1800, "charge_air_pressure_bar", "3.10", "bar", 0, 3.5],
        ["2026-01-01 00:00:00", "DG2", 320, 1800, "htcw_engine_outlet_temp_c", "82.00", "c", 0, 90],
        ["2026-01-01 01:00:00", "DG2", 320, 1800, "charge_air_pressure_bar", "3.10", "bar", 0, 3.5],
        ["2026-01-01 01:00:00", "DG2", 320, 1800, "htcw_engine_outlet_temp_c", "82.00", "c", 0, 90],
    ]
    df = pd.DataFrame(
        rows,
        columns=["timestamp", "engine_id", "load_kw", "rpm", "param", "value", "unit", "min", "max"],
    )

    csv_path = tmp_path / "readings.csv"
    df.to_csv(csv_path, index=False)

    ingest = load_readings_csv(csv_path)
    assert not ingest.df.empty

    baseline = compute_baseline(ingest.df)
    assert not baseline.empty

    drift = compute_zscore(baseline)
    drift = add_limit_proximity(drift)
    drift = add_slope_per_day(drift)
    drift = add_risk_score(drift)
    assert not drift.empty

    fleet_df = fleet_summary(drift)
    assert not fleet_df.empty
    assert "engine_id" in fleet_df.columns
    assert "priority" in fleet_df.columns

    verdict = fleet_verdict(fleet_df)
    assert isinstance(verdict, str)
    assert len(verdict) > 0