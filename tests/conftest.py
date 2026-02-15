import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """
    Canonical schema matching the pipeline contracts.

    Required by compute_baseline():
      timestamp, engine_id, param, value, unit, min, max

    Required by compute_zscore()/scoring:
      baseline_mean, baseline_std (added here so scoring tests can run
      without needing to call compute_baseline in every test)
    """
    ts = pd.date_range("2024-01-01", periods=6, freq="D")

    df = pd.DataFrame(
        {
            "engine_id": ["DG1"] * 6,
            "timestamp": ts,
            "param": ["engine_lo_inlet_pressure_bar"] * 6,
            "value": np.array([4.0, 4.1, 4.2, 4.15, 4.05, 4.3], dtype=float),
            "unit": ["bar"] * 6,
            "min": np.array([3.5] * 6, dtype=float),
            "max": np.array([4.5] * 6, dtype=float),
            # for zscore/scoring tests:
            "baseline_mean": np.array([4.1] * 6, dtype=float),
            "baseline_std": np.array([0.1] * 6, dtype=float),  # must be > 0
        }
    )
    return df
