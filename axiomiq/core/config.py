from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


# ----------------------------
# Primary config object
# ----------------------------

@dataclass(frozen=True)
class AxiomIQConfig:
    """
    Single, flattened config object used by the CLI/runtime.

    Supports config.sample.toml style:
      [axiomiq]
      input, out, snapshot, json_out, engine, health_drop, eta_compress

    Also supports structured style:
      [meta], [delta], [report], [scoring]
    """
    schema_version: str = "1.0"

    # IO
    input: str = "data/readings.csv"
    out: str = "outputs/axiomiq_report.pdf"
    snapshot: str = "outputs/last_snapshot.csv"
    json_out: str = "outputs/axiomiq_report.json"

    # analysis knobs
    engine: str | None = None
    health_drop: float = 2.0
    eta_compress: float = 7.0

    # report/scoring knobs
    top_risks: int = 5
    risk_weight: float = 1.0


# ----------------------------
# Helpers
# ----------------------------

def _as_dict(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _get(d: dict[str, Any], key: str, default: Any) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


def _coerce_float(x: Any, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _coerce_int(x: Any, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _coerce_str(x: Any, default: str) -> str:
    try:
        s = str(x)
        return s if s.strip() else default
    except Exception:
        return default


def _coerce_opt_str(x: Any) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return s or None


# ----------------------------
# Load + merge
# ----------------------------

def load_config(path: str | Path | None) -> AxiomIQConfig:
    """
    Load TOML config. If missing/None, returns safe defaults.
    Never raises for missing file (config is optional).
    """
    if not path:
        return AxiomIQConfig()

    p = Path(path)
    if not p.exists():
        return AxiomIQConfig()

    data = tomllib.loads(p.read_text(encoding="utf-8"))

    # Preferred simple table
    axi = _as_dict(data.get("axiomiq", {}))

    # Optional structured tables (future-proof)
    meta = _as_dict(data.get("meta", {}))
    delta = _as_dict(data.get("delta", {}))
    report = _as_dict(data.get("report", {}))
    scoring = _as_dict(data.get("scoring", {}))

    schema_version = _coerce_str(_get(meta, "schema_version", "1.0"), "1.0")

    # Read simple keys first, then fall back to structured
    input_path = _coerce_str(_get(axi, "input", AxiomIQConfig.input), AxiomIQConfig.input)
    out_pdf = _coerce_str(_get(axi, "out", AxiomIQConfig.out), AxiomIQConfig.out)
    snapshot = _coerce_str(_get(axi, "snapshot", AxiomIQConfig.snapshot), AxiomIQConfig.snapshot)
    json_out = _coerce_str(_get(axi, "json_out", AxiomIQConfig.json_out), AxiomIQConfig.json_out)

    engine = _coerce_opt_str(_get(axi, "engine", None))

    # analysis knobs: accept either simple or structured names
    health_drop = _coerce_float(
        _get(axi, "health_drop", _get(delta, "health_drop_points", AxiomIQConfig.health_drop)),
        AxiomIQConfig.health_drop,
    )
    eta_compress = _coerce_float(
        _get(axi, "eta_compress", _get(delta, "eta_compress_days", AxiomIQConfig.eta_compress)),
        AxiomIQConfig.eta_compress,
    )

    top_risks = _coerce_int(_get(axi, "top_risks", _get(report, "top_risks", AxiomIQConfig.top_risks)), AxiomIQConfig.top_risks)
    risk_weight = _coerce_float(_get(axi, "risk_weight", _get(scoring, "risk_weight", AxiomIQConfig.risk_weight)), AxiomIQConfig.risk_weight)

    return AxiomIQConfig(
        schema_version=schema_version,
        input=input_path,
        out=out_pdf,
        snapshot=snapshot,
        json_out=json_out,
        engine=engine,
        health_drop=health_drop,
        eta_compress=eta_compress,
        top_risks=top_risks,
        risk_weight=risk_weight,
    )


def merge_config(cfg: AxiomIQConfig, args: Any) -> AxiomIQConfig:
    """
    Merge CLI args over file config.
    Only applies fields if the arg exists AND is not None/empty.
    """
    def pick_str(name: str, cur: str) -> str:
        if hasattr(args, name):
            v = getattr(args, name)
            if v is not None and str(v).strip():
                return str(v).strip()
        return cur

    def pick_opt_str(name: str, cur: str | None) -> str | None:
        if hasattr(args, name):
            v = getattr(args, name)
            if v is None:
                return cur
            s = str(v).strip()
            return s or cur
        return cur

    def pick_float(name: str, cur: float) -> float:
        if hasattr(args, name):
            v = getattr(args, name)
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    return cur
        return cur

    def pick_int(name: str, cur: int) -> int:
        if hasattr(args, name):
            v = getattr(args, name)
            if v is not None:
                try:
                    return int(v)
                except Exception:
                    return cur
        return cur

    return AxiomIQConfig(
        schema_version=cfg.schema_version,
        input=pick_str("input", cfg.input),
        out=pick_str("out", cfg.out),
        snapshot=pick_str("snapshot", cfg.snapshot),
        json_out=pick_str("json", cfg.json_out) if hasattr(args, "json") else pick_str("json_out", cfg.json_out),

        engine=pick_opt_str("engine", cfg.engine),
        health_drop=pick_float("health_drop", cfg.health_drop),
        eta_compress=pick_float("eta_compress", cfg.eta_compress),

        top_risks=pick_int("top_risks", cfg.top_risks),
        risk_weight=pick_float("risk_weight", cfg.risk_weight),
    )