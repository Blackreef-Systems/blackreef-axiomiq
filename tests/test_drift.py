import pandas as pd
from axiomiq.core.drift import (
    add_limit_proximity,
    add_slope_per_day,
    compute_zscore,
)


def sample_df():
    return pd.DataFrame({
        "engine_id": ["DG1"] * 5,
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
        "engine_lo_inlet_pressure_bar": [4.0, 4.1, 4.2, 4.3, 4.4],
    })


def test_add_limit_proximity():
    df = sample_df()
    result = add_limit_proximity(df.copy())
    assert not result.empty


def test_add_slope_per_day():
    df = sample_df()
    result = add_slope_per_day(df.copy())
    assert not result.empty


def test_compute_zscore():
    df = sample_df()
    result = compute_zscore(df.copy())
    assert not result.empty
