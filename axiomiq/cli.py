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

from axiomiq.core.baseline import compute_baseline
from axiomiq.core.delta import DeltaConfig, compute_delta_lines, load_snapshot, save_snapshot, snapshot_from_fleet
from axiomiq.core.drift import add_limit_proximity, add_slope_per_day, compute_zscore
from axiomiq.core.fleet import fleet_summary, fleet_verdict
from axiomiq.core.ingest import load_readings_csv
from axiomiq.core.scoring import add_risk_score, health_score, top_risks
from axiomiq.report.pdf_report import write_pdf_report


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
    p = argparse.ArgumentParser(
        prog="axiomiq",
        description="Blackreef AxiomIQ — Fleet & engine drift analytics",
    )

    p.add_argument(
        "--input",
        default="data/readings.csv",
        help="Path to readings CSV",
    )

    p.add_argument(
        "--out",
        default="outputs/axiomiq_report.pdf",
        help="Output PDF path",
    )

    p.add_argument(
        "--snapshot",
        default="outputs/last_snapshot.csv",
        help="Snapshot CSV path for change tracking",
    )

    p.add_argument(
        "--engine",
        default=None,
        help="Force focus engine_id (e.g., DG1). Default: highest priority.",
    )

    p.add_argument(
        "--health-drop",
        type=float,
        default=DEFAULT_HEALTH_DROP_TRIGGER_POINTS,
        help=f"Delta trigger: health drop points (default {DEFAULT_HEALTH_DROP_TRIGGER_POINTS})",
    )

    p.add_argument(
        "--eta-compress",
        type=float,
        default=DEFAULT_ETA_COMPRESS_TRIGGER_DAYS,
        help=f"Delta trigger: ETA compression in days (default {DEFAULT_ETA_COMPRESS_TRIGGER_DAYS})",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    data_path = Path(args.input)
    out_pdf = Path(args.out)
    snapshot_path = Path(args.snapshot)

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

    cfg = DeltaConfig(health_drop_points=args.health_drop, eta_compress_days=args.eta_compress)
    delta_lines = compute_delta_lines(prev_snap, curr_snap, cfg=cfg)

    # Save snapshot AFTER computing delta (so "prev" truly means last run)
    save_snapshot(curr_snap, snapshot_path)

    # Choose focus engine
    if args.engine:
        focus_engine_id = str(args.engine)
    else:
        # Highest priority after sorting is first row
        if not fleet_df.empty and "engine_id" in fleet_df.columns:
            focus_engine_id = str(fleet_df.iloc[0]["engine_id"])
        else:
            focus_engine_id = str(drift["engine_id"].iloc[0])

    engine_slice = drift[drift["engine_id"] == focus_engine_id].copy()
    focus_score = float(health_score(engine_slice)) if not engine_slice.empty else 0.0
    focus_risks = top_risks(engine_slice, top_n=5) if not engine_slice.empty else pd.DataFrame()

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())