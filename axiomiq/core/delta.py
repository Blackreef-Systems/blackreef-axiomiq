from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class DeltaConfig:
    health_drop_points: float = 2.0
    eta_compress_days: float = 7.0


SNAPSHOT_COLUMNS = ["engine_id", "health", "top_risk", "eta_days", "priority"]


def snapshot_from_fleet(fleet_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract a stable snapshot from fleet summary.
    Expected columns in fleet_df: engine_id, health, top_risk, eta_days, priority
    """
    if fleet_df is None or fleet_df.empty:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    out = fleet_df.copy()

    # Only keep expected columns if present
    cols = [c for c in SNAPSHOT_COLUMNS if c in out.columns]
    out = out[cols].copy()

    # Normalize types
    out["engine_id"] = out["engine_id"].astype(str)
    if "priority" in out.columns:
        out["priority"] = out["priority"].astype(str)
    if "top_risk" in out.columns:
        out["top_risk"] = out["top_risk"].astype(str)

    # Make health / eta numeric if possible
    if "health" in out.columns:
        out["health"] = pd.to_numeric(out["health"], errors="coerce")
    if "eta_days" in out.columns:
        out["eta_days"] = pd.to_numeric(out["eta_days"], errors="coerce")

    # Sort for stability
    if "engine_id" in out.columns:
        out = out.sort_values("engine_id").reset_index(drop=True)

    return out


def load_snapshot(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    try:
        df = pd.read_csv(p)
    except Exception:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    # Ensure required columns exist (fill missing)
    for c in SNAPSHOT_COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA

    df = df[SNAPSHOT_COLUMNS].copy()
    df["engine_id"] = df["engine_id"].astype(str)
    df["health"] = pd.to_numeric(df["health"], errors="coerce")
    df["eta_days"] = pd.to_numeric(df["eta_days"], errors="coerce")
    df["top_risk"] = df["top_risk"].astype(str)
    df["priority"] = df["priority"].astype(str)

    return df.sort_values("engine_id").reset_index(drop=True)


def save_snapshot(snapshot_df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    out = snapshot_df.copy()
    for c in SNAPSHOT_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[SNAPSHOT_COLUMNS].copy()

    out.to_csv(p, index=False)


def _priority_rank(p: str) -> int:
    # Higher urgency = lower number
    order = {"HIGH": 0, "MED": 1, "LOW": 2}
    return order.get(str(p).upper(), 9)


def compute_delta_lines(
    prev_snapshot: pd.DataFrame,
    curr_snapshot: pd.DataFrame,
    cfg: DeltaConfig | None = None,
    max_lines: int = 8,
) -> list[str]:
    """
    Produce executive-friendly bullet lines describing what's changed.
    """
    cfg = cfg or DeltaConfig()

    prev = prev_snapshot.copy()
    curr = curr_snapshot.copy()

    if curr.empty and prev.empty:
        return ["No fleet data available yet."]

    if prev.empty and not curr.empty:
        return ["Baseline created (first run). Future reports will highlight changes."]

    # Index by engine_id for diffing
    prev_i = prev.set_index("engine_id", drop=False)
    curr_i = curr.set_index("engine_id", drop=False)

    engines = sorted(set(prev_i.index.tolist()) | set(curr_i.index.tolist()))
    lines: list[str] = []

    for eng in engines:
        was = prev_i.loc[eng] if eng in prev_i.index else None
        now = curr_i.loc[eng] if eng in curr_i.index else None

        if was is None and now is not None:
            lines.append(f"{eng} added to fleet monitoring (priority {now['priority']}).")
            continue

        if now is None and was is not None:
            lines.append(f"{eng} removed from fleet monitoring.")
            continue

        # Both exist
        was_pri = str(was["priority"])
        now_pri = str(now["priority"])

        was_rank = _priority_rank(was_pri)
        now_rank = _priority_rank(now_pri)

        # Priority escalation/de-escalation
        if now_rank < was_rank:
            lines.append(f"{eng} priority escalated {was_pri} → {now_pri}.")
        elif now_rank > was_rank:
            lines.append(f"{eng} priority reduced {was_pri} → {now_pri}.")

        # Health drop
        was_h = was["health"]
        now_h = now["health"]
        if pd.notna(was_h) and pd.notna(now_h):
            drop = float(was_h) - float(now_h)
            if drop >= cfg.health_drop_points:
                lines.append(f"{eng} health dropped {drop:.1f} points ({was_h:.1f} → {now_h:.1f}).")

        # ETA compression (if both present)
        was_eta = was["eta_days"]
        now_eta = now["eta_days"]
        if pd.notna(was_eta) and pd.notna(now_eta):
            compress = float(was_eta) - float(now_eta)
            if compress >= cfg.eta_compress_days:
                lines.append(f"{eng} time-to-limit compressed {was_eta:.1f}d → {now_eta:.1f}d.")

        # Top risk change
        was_r = str(was["top_risk"])
        now_r = str(now["top_risk"])
        if was_r and now_r and was_r != now_r and was_r != "nan" and now_r != "nan":
            lines.append(f"{eng} top risk changed {was_r} → {now_r}.")

        if len(lines) >= max_lines:
            break

    if not lines:
        return ["No material fleet changes detected since last report."]

    return lines[:max_lines]