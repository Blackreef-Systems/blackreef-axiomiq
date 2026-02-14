from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    clean = df.copy()

    # Ensure JSON-safe values
    for col in clean.columns:
        clean[col] = clean[col].apply(_json_safe)

    return clean.to_dict(orient="records")


def _json_safe(x: Any) -> Any:
    # pandas/numpy scalars -> python
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    if isinstance(x, (pd.Timestamp,)):
        return x.isoformat()

    # lists of floats (sparklines) are already fine
    if isinstance(x, (list, tuple)):
        return [_json_safe(v) for v in x]

    # numbers/strings/bools ok
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x

    # fallback: stringify
    return str(x)


def write_json_report(
    out_path: str | Path,
    *,
    generated_at: str | None,
    coverage_line: str | None,
    verdict: str,
    delta_lines: list[str] | None,
    focus_engine_id: str,
    focus_score: float,
    fleet_df: pd.DataFrame,
    focus_risks: pd.DataFrame,
    notes: list[str] | None,
    run_config: dict[str, str] | None,
) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "meta": {
            "generated_at": generated_at,
            "coverage": coverage_line,
            "run_config": run_config or {},
        },
        "fleet": {
            "verdict": verdict,
            "delta": delta_lines or [],
            "table": _df_to_records(fleet_df),
        },
        "focus": {
            "engine_id": focus_engine_id,
            "health_score": focus_score,
            "risks": _df_to_records(focus_risks),
        },
        "notes": notes or [],
    }

    p.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    return p