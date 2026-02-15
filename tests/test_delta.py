import pandas as pd
from axiomiq.core.delta import (
    compute_delta_lines,
    snapshot_from_fleet,
)


def sample_df():
    return pd.DataFrame({
        "engine_id": ["DG1", "DG1"],
        "engine_lo_inlet_pressure_bar": [4.0, 4.2],
        "health_score": [95, 90],
    })


def test_compute_delta_lines_runs():
    df = sample_df()
    result = compute_delta_lines(df.copy(), None)
    assert result is not None


def test_snapshot_from_fleet_runs():
    df = sample_df()
    result = snapshot_from_fleet(df.copy())
    assert not result.empty
