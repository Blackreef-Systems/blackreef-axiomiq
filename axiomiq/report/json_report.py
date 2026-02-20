from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


def _json_safe(x: Any) -> Any:
    """
    Convert values into strict JSON-safe Python types.

    Guarantees:
    - No NaN / Infinity (converted to None)
    - pandas/numpy NA -> None
    - numpy scalars -> python primitives
    - Recurses through dict/list/tuple
    """
    # Dicts (recursive)
    if isinstance(x, dict):
        return {str(k): _json_safe(v) for k, v in x.items()}

    # Lists / tuples (recursive)
    if isinstance(x, (list, tuple)):
        return [_json_safe(v) for v in x]

    # pandas/numpy NA handling
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass

    # Floats (NaN/Inf)
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return x

    # Numpy scalars (float/int) -> python primitives
    if hasattr(x, "item") and callable(x.item):
        try:
            return _json_safe(x.item())
        except Exception:
            pass

    # Timestamps
    if isinstance(x, pd.Timestamp):
        return x.isoformat()

    # Primitive safe types
    if isinstance(x, (str, int, bool)) or x is None:
        return x

    # Fallback: stringify unknown types
    return str(x)


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    clean = df.copy()
    for col in clean.columns:
        clean[col] = clean[col].apply(_json_safe)
    return clean.to_dict(orient="records")


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
    """
    Writes the canonical AxiomIQ JSON report.

    IMPORTANT:
    - `meta` must remain schema-stable and NOT include extra keys.
      (No `run_config`, no `contract` inside `meta`.)
    """
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    decision_version = run_config.get("version") if run_config else None
    schema_version = run_config.get("schema") if run_config else None

    payload: dict[str, Any] = {
        "meta": {
            "generated_at": generated_at,
            "coverage": coverage_line,
            "decision_version": decision_version,
            "schema_version": schema_version,
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

    # Sanitize *entire* payload recursively
    payload = _json_safe(payload)

    # STRICT JSON — no NaN allowed
    p.write_text(
        json.dumps(payload, indent=2, sort_keys=False, allow_nan=False),
        encoding="utf-8",
    )
    return p