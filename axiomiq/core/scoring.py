from __future__ import annotations

import numpy as np
import pandas as pd


def add_risk_score(drift_df: pd.DataFrame) -> pd.DataFrame:
    if drift_df.empty:
        return pd.DataFrame()

    d = drift_df.copy()

    # Z-score risk (0–1 scale, 3-sigma ~= high)
    z_abs = d["z"].abs()
    z_risk = (z_abs / 3.0).clip(0.0, 1.0)

    # Limit proximity risk (closer to limit => higher risk)
    margin = d.get("margin_to_nearest_limit", pd.Series(np.nan, index=d.index))
    limit_risk = ((0.5 - margin) / 0.5).clip(0.0, 1.0)

    # Slope risk (rate-of-change), normalized per (engine, param)
    slope = d.get("slope_per_day", pd.Series(np.nan, index=d.index)).abs()
    slope_risk = pd.Series(0.0, index=d.index)

    for (engine_id, param), idx in d.groupby(["engine_id", "param"]).groups.items():
        s = slope.loc[idx].dropna()
        if s.empty:
            continue
        scale = float(np.median(s)) or 1.0
        slope_risk.loc[idx] = (slope.loc[idx] / (3.0 * scale)).clip(0.0, 1.0)

    d["risk_score"] = (
        0.55 * z_risk.fillna(0.0)
        + 0.30 * limit_risk.fillna(0.0)
        + 0.15 * slope_risk.fillna(0.0)
    )

    return d


def health_score(drift_df: pd.DataFrame) -> float:
    if drift_df.empty or "risk_score" not in drift_df.columns:
        return 100.0

    r = drift_df["risk_score"].dropna()
    if r.empty:
        return 100.0

    penalty = float(np.clip(r.mean() * 80.0, 0.0, 80.0))
    return round(100.0 - penalty, 1)


def _eta_days(value: float, limit: float, slope_per_day: float) -> float | None:
    """
    Estimated days to reach 'limit' assuming constant slope.
    Returns None if slope is zero/invalid or ETA is negative/unreasonable.
    """
    if slope_per_day is None or np.isnan(slope_per_day) or slope_per_day == 0:
        return None
    eta = (limit - value) / slope_per_day
    if np.isnan(eta) or eta < 0:
        return None
    # Guardrail: ignore absurd ETAs (e.g., years) in v1
    if eta > 365:
        return None
    return float(eta)


def top_risks(drift_df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Top parameters by max_risk, plus ETA to min/max limit based on latest slope.
    """
    if drift_df.empty or "risk_score" not in drift_df.columns:
        return pd.DataFrame(
            columns=["engine_id", "param", "max_risk", "direction", "eta_to_min_days", "eta_to_max_days"]
        )

    d = drift_df.copy()

    # Use the latest row per (engine,param) for ETA calcs
    d_latest = (
        d.sort_values("timestamp")
        .groupby(["engine_id", "param"], as_index=False)
        .tail(1)
        .copy()
    )

    # Aggregate risk per (engine,param)
    agg = (
        d.groupby(["engine_id", "param"], as_index=False)["risk_score"]
        .max()
        .rename(columns={"risk_score": "max_risk"})
    )

    merged = agg.merge(d_latest, on=["engine_id", "param"], how="left", suffixes=("", "_latest"))

    # Direction based on slope sign
    slope = merged.get("slope_per_day", pd.Series(np.nan, index=merged.index))
    merged["direction"] = np.where(slope > 0, "↑", np.where(slope < 0, "↓", "→"))

    # ETA calculations (only meaningful if min/max exist)
    merged["eta_to_min_days"] = [
        _eta_days(v, mn, s) if pd.notna(mn) else None
        for v, mn, s in zip(merged["value"], merged.get("min"), slope)
    ]
    merged["eta_to_max_days"] = [
        _eta_days(v, mx, s) if pd.notna(mx) else None
        for v, mx, s in zip(merged["value"], merged.get("max"), slope)
    ]

    merged = merged.sort_values("max_risk", ascending=False).head(top_n)

    return merged[["engine_id", "param", "max_risk", "direction", "eta_to_min_days", "eta_to_max_days"]]