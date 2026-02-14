from __future__ import annotations

from axiomiq.core.contract import (
    AXIOMIQ_DECISION_VERSION,
    DEFAULT_ETA_COMPRESS_TRIGGER_DAYS,
    DEFAULT_HEALTH_DROP_TRIGGER_POINTS,
)

from importlib.metadata import version, PackageNotFoundError

try:
    AXIOMIQ_DECISION_VERSION = version("axiomiq")
except PackageNotFoundError:
    AXIOMIQ_DECISION_VERSION = "dev"

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from axiomiq.core.config import AxiomIQConfig, merge_config
from axiomiq.core.baseline import compute_baseline
from axiomiq.core.delta import DeltaConfig, compute_delta_lines, load_snapshot, save_snapshot, snapshot_from_fleet
from axiomiq.core.drift import add_limit_proximity, add_slope_per_day, compute_zscore
from axiomiq.core.fleet import fleet_summary, fleet_verdict
from axiomiq.core.ingest import load_readings_csv
from axiomiq.core.scoring import add_risk_score, health_score, top_risks
from axiomiq.report.pdf_report import write_pdf_report
from axiomiq.report.json_report import write_json_report


def _safe_trend_series(engine_slice: pd.DataFrame, param: str, n: int = 120) -> list[float]:
    """
    Returns the last N points for a param from any available proximity-like column.
    Sparkline normalizes defensively later, so raw-ish is OK.
    """
    if engine_slice.empty or "param" not in engine_slice.columns:
        return []

    s = engine_slice[engine_slice["param"] == param].copy()
    if s.empty:
        return []

    # Prefer time ordering if present
    if "timestamp" in s.columns:
        s = s.sort_values("timestamp")

    # Try a few likely column names (depending on your pipeline)
    candidates = [
        "limit_proximity",
        "proximity",
        "limit_prox",
        "distance_to_limit",
        "dist_to_limit",
        "risk_score",  # last resort (still shows “movement”)
        "z",
        "zscore",
    ]
    col = next((c for c in candidates if c in s.columns), None)
    if not col:
        return []

    vals = s[col].tail(n).tolist()
    return [float(v) for v in vals if isinstance(v, (int, float))]

def _console_safe(s: str) -> str:
    """
    Windows PowerShell can choke on certain Unicode chars (e.g., arrows).
    Keep console output ASCII-safe while leaving PDF output untouched.
    """
    return (
        str(s)
        .replace("→", "->")
        .replace("↓", "down")
        .replace("↑", "up")
        .replace("•", "-")
        .replace("⚠", "!")
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="axiomiq", description="Blackreef AxiomIQ — Fleet & engine drift analytics")

    # Config (optional)
    p.add_argument("--config", default=None, help="Path to config TOML (optional)")

    # I/O
    p.add_argument("--input", default=None, help="Path to readings CSV")
    p.add_argument("--out", default=None, help="Output PDF path")
    p.add_argument("--snapshot", default=None, help="Snapshot CSV path for change tracking")
    p.add_argument("--json-out", default=None, help="Optional JSON output path (structured results)")

    # Analysis
    p.add_argument("--engine", default=None, help="Force focus engine_id (e.g., DG1). Default: highest priority.")
    p.add_argument("--health-drop", type=float, default=None, help="Delta trigger: health drop points")
    p.add_argument("--eta-compress", type=float, default=None, help="Delta trigger: ETA compression in days")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    file_cfg = AxiomIQConfig.from_toml(args.config) if args.config else None
    
    # Build an "explicit CLI" dict (only set keys when user provided them)
    cli_explicit = {}
    if args.input is not None:
        cli_explicit["input"] = args.input
    if args.out is not None:
        cli_explicit["out"] = args.out
    if args.snapshot is not None:
        cli_explicit["snapshot"] = args.snapshot
    if args.json_out is not None:
        cli_explicit["json_out"] = args.json_out
    if args.engine is not None:
        cli_explicit["engine"] = args.engine
    if args.health_drop is not None:
        cli_explicit["health_drop"] = args.health_drop
    if args.eta_compress is not None:
        cli_explicit["eta_compress"] = args.eta_compress

    cfg = merge_config(cli_explicit, file_cfg)

    data_path = Path(cfg.input)
    out_pdf = Path(cfg.out)
    snapshot_path = Path(cfg.snapshot)
    json_out_path = Path(cfg.json_out) if cfg.json_out else None

    ingest = load_readings_csv(data_path)
    if ingest.df.empty:
        print("No data loaded.")
        return 1

    # Build full drift table (ALL engines)
    baseline = compute_baseline(ingest.df)
    drift = compute_zscore(baseline)
    drift = add_limit_proximity(drift)
    drift = add_slope_per_day(drift)
    drift = add_risk_score(drift)

    # Fleet summary from full drift table
    fleet_df = fleet_summary(drift)
    verdict = fleet_verdict(fleet_df)

    # Snapshot delta
    prev_snap = load_snapshot(snapshot_path)
    curr_snap = snapshot_from_fleet(fleet_df)

    cfg_delta = DeltaConfig(health_drop_points=cfg.health_drop, eta_compress_days=cfg.eta_compress)
    delta_lines = compute_delta_lines(prev_snap, curr_snap, cfg=cfg_delta)

    # Save snapshot AFTER computing delta (so "prev" truly means last run)
    save_snapshot(curr_snap, snapshot_path)

    # Choose focus engine
    if cfg.engine:
        focus_engine_id = str(cfg.engine)

    else:
        # Highest priority after sorting is first row
        if not fleet_df.empty and "engine_id" in fleet_df.columns:
            focus_engine_id = str(fleet_df.iloc[0]["engine_id"])
        else:
            focus_engine_id = str(drift["engine_id"].iloc[0])

    engine_slice = drift[drift["engine_id"] == focus_engine_id].copy()
    focus_score = float(health_score(engine_slice)) if not engine_slice.empty else 0.0
    focus_risks = top_risks(engine_slice, top_n=5) if not engine_slice.empty else pd.DataFrame()

    focus_trends: dict[str, list[float]] = {}
    if not engine_slice.empty and not focus_risks.empty:
        for p in focus_risks["param"].tolist():
            focus_trends[str(p)] = _safe_trend_series(engine_slice, str(p), n=120)
            

    # Report meta (polish)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Basic coverage: date range + row count
    ts = pd.to_datetime(ingest.df["timestamp"], errors="coerce") if "timestamp" in ingest.df.columns else pd.Series([])
    ts_min = ts.min() if not ts.empty else None
    ts_max = ts.max() if not ts.empty else None
    span = "N/A"
    if ts_min is not None and ts_max is not None and pd.notna(ts_min) and pd.notna(ts_max):
        span = f"{ts_min.date()} -> {ts_max.date()}"
    coverage = (
        f"Coverage: {span} | Samples: {len(ingest.df)} | Engines: "
        f"{ingest.df['engine_id'].nunique() if 'engine_id' in ingest.df.columns else 'N/A'}"
    )

    run_config = {
        "profile": str(getattr(args, "profile", "")) if hasattr(args, "profile") else "",
        "seed": str(getattr(args, "seed", "")) if hasattr(args, "seed") and args.seed is not None else "",
        "days": str(getattr(args, "days", "")) if hasattr(args, "days") else "",
        "step_hours": str(getattr(args, "step_hours", "")) if hasattr(args, "step_hours") else "",
        "engines": str(getattr(args, "engines", "")) if hasattr(args, "engines") else "",
        "failure": "on" if bool(getattr(args, "inject_failure", False)) else "",
        "version": AXIOMIQ_DECISION_VERSION,
    }

    write_pdf_report(
        out_path=out_pdf,
        fleet_df=fleet_df,
        verdict=verdict,
        delta_lines=delta_lines,
        generated_at=generated_at,
        coverage_line=coverage,
        focus_engine_id=focus_engine_id,
        focus_score=round(focus_score, 1),
        focus_risks=focus_risks,
        focus_trends=focus_trends,
        notes=ingest.issues,
        run_config=run_config,
    )
    
    if json_out_path:
        write_json_report(
            out_path=json_out_path,
            generated_at=generated_at,
            coverage_line=coverage,
            verdict=verdict,
            delta_lines=delta_lines,
            focus_engine_id=focus_engine_id,
            focus_score=round(focus_score, 1),
            fleet_df=fleet_df,
            focus_risks=focus_risks,
            notes=ingest.issues,
            run_config=run_config,
        )


    # Prints only at main (your preference)
    print(f"Report generated: {out_pdf.resolve()}")
    print(f"Snapshot saved:  {snapshot_path.resolve()}")
    print(f"Fleet Verdict:   {_console_safe(verdict)}")
    print(f"Focus engine:    {focus_engine_id} | Health Score: {round(focus_score, 1)}")
    
    if delta_lines:
        print("Key Changes:")
        for d in delta_lines:
            print(f" - {_console_safe(d)}")
            
    if json_out_path:
        print(f"JSON saved:      {json_out_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())