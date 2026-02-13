from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

# ----------------------------
# Configuration / Param Catalog
# ----------------------------

# (param, unit, min, max, nominal)
PARAMS = [
    ("engine_lo_inlet_pressure_bar", "bar", 3.5, 4.5, 4.1),
    ("tc_lo_inlet_pressure_bar", "bar", 1.3, 2.0, 1.6),
    ("lo_inlet_temp_c", "c", 0, 65, 58),
    ("htcw_engine_outlet_temp_c", "c", 0, 90, 82),
    ("charge_air_pressure_bar", "bar", 0, 3.5, 3.1),
]


@dataclass(frozen=True)
class DriftConfig:
    # per-hour drifts (small numbers)
    temp_drift: float
    press_drift: float
    noise: float


@dataclass(frozen=True)
class FailureEvent:
    mode: str                 # e.g. "air_intake_restriction"
    engine_id: str            # e.g. "DG3"
    start_day: int            # day index when it begins (0..days-1)
    ramp_days: int            # how long to ramp to full effect
    severity: float           # 0.0..1.0


PROFILE_PRESETS: dict[str, dict[str, DriftConfig]] = {
    "demo": {
        "DG1": DriftConfig(temp_drift=0.000, press_drift=0.000, noise=0.020),
        "DG2": DriftConfig(temp_drift=0.006, press_drift=-0.003, noise=0.025),
        "DG3": DriftConfig(temp_drift=0.010, press_drift=0.000, noise=0.030),
        "DG4": DriftConfig(temp_drift=0.015, press_drift=-0.004, noise=0.030),
        "DG5": DriftConfig(temp_drift=0.000, press_drift=-0.006, noise=0.030),
        "DG6": DriftConfig(temp_drift=0.020, press_drift=-0.010, noise=0.035),
    },
    "healthy": {
        "DG1": DriftConfig(0.000, 0.000, 0.015),
        "DG2": DriftConfig(0.000, 0.000, 0.015),
        "DG3": DriftConfig(0.000, 0.000, 0.015),
        "DG4": DriftConfig(0.000, 0.000, 0.015),
        "DG5": DriftConfig(0.000, 0.000, 0.015),
        "DG6": DriftConfig(0.000, 0.000, 0.015),
    },
    "degrading": {
        "DG1": DriftConfig(0.006, -0.002, 0.020),
        "DG2": DriftConfig(0.008, -0.003, 0.022),
        "DG3": DriftConfig(0.010, -0.004, 0.025),
        "DG4": DriftConfig(0.012, -0.005, 0.028),
        "DG5": DriftConfig(0.014, -0.006, 0.030),
        "DG6": DriftConfig(0.016, -0.008, 0.032),
    },
    "mixed": {},
}


# ----------------------------
# Helpers
# ----------------------------

def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def make_load_kw(rng: random.Random) -> int:
    return rng.choice([160, 240, 320, 480, 640])


def make_rpm(load_kw: int) -> int:
    return 1800 if load_kw >= 240 else 1500


def iter_timestamps(start: datetime, days: int, step_hours: int) -> Iterable[datetime]:
    total_steps = int((days * 24) / step_hours)
    for i in range(total_steps):
        yield start + timedelta(hours=i * step_hours)


def engine_configs(
    engines: list[str],
    profile: str,
    rng: random.Random,
    noise_override: float | None,
) -> dict[str, DriftConfig]:
    if profile not in PROFILE_PRESETS:
        raise ValueError(f"Unknown profile: {profile}")

    if profile == "mixed":
        cfg: dict[str, DriftConfig] = {}
        for e in engines:
            temp = rng.uniform(0.000, 0.020)
            press = rng.uniform(-0.012, 0.004)
            noise = rng.uniform(0.015, 0.040)
            cfg[e] = DriftConfig(temp, press, noise_override if noise_override is not None else noise)
        return cfg

    base = PROFILE_PRESETS[profile]
    cfg: dict[str, DriftConfig] = {}
    for e in engines:
        c = base.get(e, DriftConfig(0.000, 0.000, 0.020))
        if noise_override is not None:
            c = DriftConfig(c.temp_drift, c.press_drift, noise_override)
        cfg[e] = c
    return cfg


def failure_multiplier(day_index: int, event: FailureEvent) -> float:
    """0..1 ramp after start_day over ramp_days."""
    if day_index < event.start_day:
        return 0.0
    if event.ramp_days <= 0:
        return float(event.severity)
    t = (day_index - event.start_day) / float(event.ramp_days)
    t = max(0.0, min(1.0, t))
    return float(event.severity) * t


def apply_failure_effect(
    *,
    param: str,
    base_value: float,
    load_kw: int,
    day_index: int,
    event: FailureEvent | None,
) -> float:
    """Apply correlated failure effects (slow ramp)."""
    if event is None:
        return base_value

    m = failure_multiplier(day_index, event)
    if m <= 0.0:
        return base_value

    load_factor = max(0.0, min(1.0, (load_kw - 160) / (640 - 160)))

    if event.mode == "air_intake_restriction":
        if param == "charge_air_pressure_bar":
            return base_value - (0.20 + 0.15 * load_factor) * m
        if param == "htcw_engine_outlet_temp_c":
            return base_value + (4.0 + 3.0 * load_factor) * m
        if param == "tc_lo_inlet_pressure_bar":
            return base_value - 0.12 * m

    return base_value


# ----------------------------
# Core generation
# ----------------------------

def generate_csv(
    out_path: Path,
    start: datetime,
    days: int,
    step_hours: int,
    engines: list[str],
    seed: int | None,
    profile: str,
    noise_override: float | None,
    print_summary: bool,
    failure_event: FailureEvent | None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    cfg = engine_configs(engines, profile, rng, noise_override)

    temp_offset = {e: 0.0 for e in engines}
    press_offset = {e: 0.0 for e in engines}

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "engine_id", "load_kw", "rpm", "param", "value", "unit", "min", "max"])

        rows = 0
        for ts in iter_timestamps(start, days, step_hours):
            # Day index = 0..days-1 based on elapsed time from start
            elapsed_days = int((ts - start).total_seconds() // (24 * 3600))
            day_index = max(0, min(days - 1, elapsed_days))

            for e in engines:
                load_kw = make_load_kw(rng)
                rpm = make_rpm(load_kw)

                temp_offset[e] += cfg[e].temp_drift * step_hours
                press_offset[e] += cfg[e].press_drift * step_hours

                for (param, unit, vmin, vmax, nominal) in PARAMS:
                    eps = rng.gauss(0.0, cfg[e].noise)

                    if "temp" in param:
                        value = nominal + temp_offset[e] + eps
                    elif "pressure" in param:
                        value = nominal + press_offset[e] + eps
                    else:
                        value = nominal + eps

                    if param == "charge_air_pressure_bar":
                        value += (load_kw - 320) / 3200.0
                    if param == "htcw_engine_outlet_temp_c":
                        value += (load_kw - 320) / 800.0

                    # Apply failure ONLY for the target engine
                    active_event = None
                    if failure_event is not None and failure_event.engine_id == e:
                        active_event = failure_event

                    value = apply_failure_effect(
                        param=param,
                        base_value=value,
                        load_kw=load_kw,
                        day_index=day_index,
                        event=active_event,
                    )

                    value = clamp(value, float(vmin), float(vmax))

                    w.writerow([
                        ts.strftime("%Y-%m-%d %H:%M:%S"),
                        e,
                        load_kw,
                        rpm,
                        param,
                        f"{value:.2f}",
                        unit,
                        vmin,
                        vmax,
                    ])
                    rows += 1

    if print_summary:
        print(f"Generated {out_path} with ~{rows:,} rows")
        print(f"Engines: {', '.join(engines)} | Days: {days} | Step: {step_hours}h | Profile: {profile} | Seed: {seed}")
        if failure_event is not None:
            print(
                f"Injected failure: mode={failure_event.mode} engine={failure_event.engine_id} "
                f"start_day={failure_event.start_day} ramp_days={failure_event.ramp_days} severity={failure_event.severity}"
            )


# ----------------------------
# CLI
# ----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate_readings.py",
        description="Generate synthetic DG readings.csv for AxiomIQ demo/testing.",
    )

    p.add_argument("--out", default="data/readings.csv",
                   help="Output CSV path (default: data/readings.csv)")
    p.add_argument("--start", default="2026-01-01T00:00:00",
                   help="Start datetime (ISO format)")
    p.add_argument("--days", type=int, default=90,
                   help="Number of days to generate")
    p.add_argument("--step-hours", type=int, default=1,
                   help="Sampling interval in hours (e.g., 1, 2, 6)")
    p.add_argument("--engines", default="DG1,DG2,DG3,DG4,DG5,DG6",
                   help="Comma-separated engine IDs (default: DG1..DG6)")
    p.add_argument("--seed", type=int, default=None,
                   help="Random seed for reproducible output")
    p.add_argument("--profile", choices=["demo", "healthy", "degrading", "mixed"],
                   default="demo",
                   help="Drift profile preset")
    p.add_argument("--noise", type=float, default=None,
                   help="Override noise sigma for all engines (e.g., 0.02)")
    p.add_argument("--print-summary", action="store_true",
                   help="Print generation summary to console")

    # Failure injection (optional)
    p.add_argument("--inject-failure", action="store_true",
                   help="Inject one correlated failure mode into a single engine")
    p.add_argument("--failure-engine", default="DG3",
                   help="Engine to apply failure to (default: DG3)")
    p.add_argument("--failure-start-day", type=int, default=20,
                   help="Day index when failure begins (default: 20)")
    p.add_argument("--failure-ramp-days", type=int, default=14,
                   help="Days to ramp to full failure severity (default: 14)")
    p.add_argument("--failure-severity", type=float, default=0.8,
                   help="Failure severity 0..1 (default: 0.8)")
    p.add_argument("--failure-mode", choices=["air_intake_restriction"],
                   default="air_intake_restriction",
                   help="Failure mode to inject")

    return p


def main() -> None:
    args = build_parser().parse_args()

    out_path = Path(args.out)
    start = parse_dt(args.start)
    engines = [e.strip() for e in str(args.engines).split(",") if e.strip()]

    if args.days <= 0:
        raise SystemExit("--days must be > 0")
    if args.step_hours <= 0:
        raise SystemExit("--step-hours must be > 0")
    if not engines:
        raise SystemExit("--engines cannot be empty")

    failure_event: FailureEvent | None = None
    if args.inject_failure:
        failure_event = FailureEvent(
            mode=str(args.failure_mode),
            engine_id=str(args.failure_engine),
            start_day=int(args.failure_start_day),
            ramp_days=int(args.failure_ramp_days),
            severity=float(args.failure_severity),
        )

    generate_csv(
        out_path=out_path,
        start=start,
        days=args.days,
        step_hours=args.step_hours,
        engines=engines,
        seed=args.seed,
        profile=args.profile,
        noise_override=args.noise,
        print_summary=args.print_summary,
        failure_event=failure_event,
    )


if __name__ == "__main__":
    main()