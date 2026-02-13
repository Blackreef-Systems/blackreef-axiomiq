from __future__ import annotations

import pandas as pd


def compute_baseline(df: pd.DataFrame, window: str = "14D") -> pd.DataFrame:
    """
    Build rolling baseline statistics while preserving engineering limits.
    """
    if df.empty:
        return pd.DataFrame()

    d = df.sort_values("timestamp").copy()
    out = []

    for (engine_id, param), g in d.groupby(["engine_id", "param"], sort=False):
        g = g.set_index("timestamp").sort_index()

        rolling_mean = g["value"].rolling(window=window, min_periods=10).mean()
        rolling_std = g["value"].rolling(window=window, min_periods=10).std()

        tmp = g.reset_index()[
            ["timestamp", "engine_id", "param", "value", "unit", "min", "max"]
        ].copy()

        tmp["baseline_mean"] = rolling_mean.reset_index(drop=True)
        tmp["baseline_std"] = rolling_std.reset_index(drop=True)

        out.append(tmp)

    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()