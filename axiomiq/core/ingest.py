from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "timestamp",
    "engine_id",
    "load_kw",
    "rpm",
    "param",
    "value",
    "unit",
    "min",
    "max",
]


@dataclass(frozen=True)
class IngestResult:
    df: pd.DataFrame
    issues: list[str]


def load_readings_csv(path: str | Path) -> IngestResult:
    """
    Load long-format readings CSV and validate basic schema.

    Expected columns:
    timestamp, engine_id, load_kw, rpm, param, value, unit, min, max
    """
    path = Path(path)
    issues: list[str] = []

    if not path.exists():
        return IngestResult(df=pd.DataFrame(), issues=[f"File not found: {path}"])

    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {missing}")
        return IngestResult(df=pd.DataFrame(), issues=issues)

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = int(df["timestamp"].isna().sum())
    if bad_ts:
        issues.append(f"{bad_ts} rows have invalid timestamp")

    # Coerce numerics
    for col in ["load_kw", "rpm", "value", "min", "max"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad_nums = int(df[["load_kw", "rpm", "value"]].isna().any(axis=1).sum())
    if bad_nums:
        issues.append(f"{bad_nums} rows have invalid numeric values in load_kw/rpm/value")

    # Basic cleanup
    df["param"] = df["param"].astype(str).str.strip()
    df["engine_id"] = df["engine_id"].astype(str).str.strip()
    df["unit"] = df["unit"].astype(str).str.strip()

    # Drop rows missing essentials (strict for v1)
    df = df.dropna(subset=["timestamp", "engine_id", "param", "value", "load_kw", "rpm"]).copy()

    return IngestResult(df=df, issues=issues)