from __future__ import annotations

import pandas as pd

from axiomiq.core.scoring import health_score, top_risks

from axiomiq.core.contract import (
    ACTION_HIGH_ETA_DAYS,
    ACTION_TEXT_HIGH,
    ACTION_TEXT_LOW,
    ACTION_TEXT_MED,
    HIGH_PRIORITY_ETA_DAYS,
    MED_PRIORITY_ETA_DAYS,
    MED_PRIORITY_HEALTH_BELOW,
)

def _distance_to_limit_series(
    engine_slice: pd.DataFrame,
    param: str,
    n_points: int = 120,
) -> list[float]:
    """
    Build a normalized 0..1 series representing *distance-to-nearest-limit* over time.
    1.0 = far from limits (healthy margin), 0.0 = at/over a limit.

    Expects engine_slice columns: timestamp, param, value, min, max
    """
    if engine_slice.empty:
        return []

    s = engine_slice[engine_slice["param"] == param].copy()
    if s.empty:
        return []

    # ensure time ordering
    if "timestamp" in s.columns:
        s["timestamp"] = pd.to_datetime(s["timestamp"], errors="coerce")
        s = s.sort_values("timestamp")

    # take last N points
    s = s.tail(int(n_points))

    # numeric coercion
    v = pd.to_numeric(s["value"], errors="coerce")
    vmin = pd.to_numeric(s["min"], errors="coerce")
    vmax = pd.to_numeric(s["max"], errors="coerce")
    span = (vmax - vmin).replace(0, pd.NA)

    # distance to nearest limit (in engineering units), then normalize by span
    dist_to_min = (v - vmin).abs()
    dist_to_max = (vmax - v).abs()
    dist = pd.concat([dist_to_min, dist_to_max], axis=1).min(axis=1)

    # normalized distance (0..1). Clip in case of noise / bounds issues.
    norm = (dist / span).astype("float")
    norm = norm.clip(lower=0.0, upper=1.0)

    # drop NaNs
    out = [float(x) for x in norm.dropna().tolist()]
    return out


def fleet_verdict(fleet_df: pd.DataFrame) -> str:
    if fleet_df.empty:
        return "No fleet data available."

    high = fleet_df.loc[fleet_df["priority"] == "HIGH", "engine_id"].tolist()
    med = fleet_df.loc[fleet_df["priority"] == "MED", "engine_id"].tolist()
    low = fleet_df.loc[fleet_df["priority"] == "LOW", "engine_id"].tolist()

    parts: list[str] = []
    if high:
        parts.append(f"{', '.join(map(str, high))} requires inspection within 72 hours due to near-term drift")
    if med:
        parts.append(f"{', '.join(map(str, med))} shows degradation and should be scheduled for inspection")
    if low:
        parts.append(f"{', '.join(map(str, low))} remains healthy")

    return ". ".join(parts) + "."


def nearest_eta(row) -> float | None:
    etas: list[float] = []
    for key in ("eta_to_min_days", "eta_to_max_days"):
        v = row.get(key)
        if v is None:
            continue
        try:
            if pd.isna(v):
                continue
            etas.append(float(v))
        except Exception:
            continue
    return min(etas) if etas else None


def priority_label(health: float, eta_days: float | None) -> str:
    if eta_days is not None:
        if eta_days <= HIGH_PRIORITY_ETA_DAYS:
            return "HIGH"
        if eta_days <= MED_PRIORITY_ETA_DAYS:
            return "MED"
        return "LOW"
    # ETA unavailable: fall back to health
    if health < MED_PRIORITY_HEALTH_BELOW:
        return "MED"
    return "LOW"

def _priority_reason(health: float, eta_days: float | None, top_risk: str) -> str:
    if eta_days is not None:
        if eta_days <= 7:
            return f"ETA {eta_days:.1f}d to limit ({top_risk})."
        if eta_days <= 30:
            return f"ETA {eta_days:.1f}d to limit ({top_risk})."
        return f"ETA {eta_days:.1f}d to limit ({top_risk})."

    if health < 80:
        return f"Health {health:.1f} (<80) and ETA unavailable; schedule inspection ({top_risk})."
    return f"ETA unavailable; monitor ({top_risk})."

def recommended_action(priority: str, eta_days: float | None) -> str:
    # Tightest rule first: ETA <= ACTION_HIGH_ETA_DAYS is always urgent
    if eta_days is not None and eta_days <= ACTION_HIGH_ETA_DAYS:
        return ACTION_TEXT_HIGH

    if priority == "HIGH":
        return ACTION_TEXT_HIGH
    if priority == "MED":
        return ACTION_TEXT_MED
    return ACTION_TEXT_LOW

def fleet_summary(drift_df: pd.DataFrame) -> pd.DataFrame:
    if drift_df.empty:
        return pd.DataFrame(
            columns=[
                "engine_id",
                "health",
                "top_risk",
                "eta_days",
                "priority",
                "reason",
                "action",
                "trend",
            ]
        )

    rows = []

    for engine_id, g in drift_df.groupby("engine_id"):
        engine_slice = g.copy()

        health = float(health_score(engine_slice))

        risks = top_risks(engine_slice, top_n=1)
        if not risks.empty:
            top_row = risks.iloc[0]
            top_risk = str(top_row["param"])
            eta = nearest_eta(top_row)
        else:
            top_risk = "N/A"
            eta = None

        priority = priority_label(health, eta)
        reason = _priority_reason(health, eta, top_risk)
        action = recommended_action(priority, eta)

        trend = _distance_to_limit_series(
            engine_slice,
            top_risk,
            n_points=120,
        )

        rows.append(
            {
                "engine_id": str(engine_id),
                "health": round(health, 1),
                "top_risk": top_risk,
                "eta_days": None if eta is None else round(float(eta), 1),
                "priority": priority,
                "reason": reason,
                "action": action,
                "trend": trend,
            }
        )

    df = pd.DataFrame(rows)

    priority_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    df["_p"] = df["priority"].map(priority_order).fillna(9)
    df = (
        df.sort_values(["_p", "health"], ascending=[True, True])
          .drop(columns="_p")
          .reset_index(drop=True)
    )

    return df
