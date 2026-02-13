from __future__ import annotations

import numpy as np
import pandas as pd


def compute_zscore(baseline_df: pd.DataFrame) -> pd.DataFrame:
    if baseline_df.empty:
        return pd.DataFrame()

    d = baseline_df.copy()
    d["baseline_std"] = d["baseline_std"].replace(0, np.nan)
    d["z"] = (d["value"] - d["baseline_mean"]) / d["baseline_std"]
    return d


def add_limit_proximity(drift_df: pd.DataFrame) -> pd.DataFrame:
    if drift_df.empty:
        return pd.DataFrame()

    d = drift_df.copy()

    # If limits are missing, skip gracefully
    if "min" not in d.columns or "max" not in d.columns:
        d["limit_pos"] = None
        d["margin_to_nearest_limit"] = None
        return d

    span = (d["max"] - d["min"]).replace(0, np.nan)

    d["limit_pos"] = (d["value"] - d["min"]) / span
    d["margin_to_nearest_limit"] = (0.5 - (d["limit_pos"] - 0.5).abs()).clip(0, 0.5)

    return d


def add_slope_per_day(drift_df: pd.DataFrame, window_points: int = 3) -> pd.DataFrame:
    if drift_df.empty:
        return pd.DataFrame()

    d = drift_df.sort_values("timestamp").copy()
    out = []

    for (engine_id, param), g in d.groupby(["engine_id", "param"], sort=False):
        g = g.sort_values("timestamp").copy()

        g["value_prev"] = g["value"].shift(window_points - 1)
        g["t_prev"] = g["timestamp"].shift(window_points - 1)

        days = (g["timestamp"] - g["t_prev"]).dt.total_seconds() / 86400.0
        g["slope_per_day"] = (g["value"] - g["value_prev"]) / days.replace(0, np.nan)

        out.append(g.drop(columns=["value_prev", "t_prev"]))

    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()