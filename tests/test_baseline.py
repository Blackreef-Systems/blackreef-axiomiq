import pandas as pd
from axiomiq.core.baseline import compute_baseline


def test_compute_baseline_basic():
    df = pd.DataFrame({
        "engine_id": ["DG1", "DG1", "DG2", "DG2"],
        "engine_lo_inlet_pressure_bar": [4.0, 4.2, 4.1, 4.3],
        "tc_lo_inlet_pressure_bar": [1.5, 1.6, 1.7, 1.8],
    })

    baseline = compute_baseline(df)

    assert not baseline.empty
    assert "engine_lo_inlet_pressure_bar" in baseline.columns
    assert "tc_lo_inlet_pressure_bar" in baseline.columns
    assert set(baseline["engine_id"]) == {"DG1", "DG2"}
