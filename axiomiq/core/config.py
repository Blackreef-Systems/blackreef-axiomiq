from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib


@dataclass(frozen=True)
class AxiomIQConfig:
    # I/O
    input: str = "data/readings.csv"
    out: str = "outputs/axiomiq_report.pdf"
    snapshot: str = "outputs/last_snapshot.csv"
    json_out: str | None = None

    # Analysis
    engine: str | None = None
    health_drop: float = 2.0
    eta_compress: float = 7.0

    @staticmethod
    def from_toml(path: str | Path) -> "AxiomIQConfig":
        p = Path(path)
        data = tomllib.loads(p.read_text(encoding="utf-8"))

        # Allow either:
        #   [axiomiq] ...
        # or top-level keys
        cfg: dict[str, Any] = data.get("axiomiq", data) if isinstance(data, dict) else {}

        def _get(key: str, default):
            v = cfg.get(key, default)
            return default if v is None else v

        return AxiomIQConfig(
            input=str(_get("input", "data/readings.csv")),
            out=str(_get("out", "outputs/axiomiq_report.pdf")),
            snapshot=str(_get("snapshot", "outputs/last_snapshot.csv")),
            json_out=_get("json_out", None),
            engine=_get("engine", None),
            health_drop=float(_get("health_drop", 2.0)),
            eta_compress=float(_get("eta_compress", 7.0)),
        )


def merge_config(cli: dict[str, Any], file_cfg: AxiomIQConfig | None) -> AxiomIQConfig:
    """
    Precedence: CLI (explicit) > file config > defaults
    CLI dict should include keys when user explicitly passed them.
    """
    base = file_cfg or AxiomIQConfig()

    def pick(name: str):
        return cli[name] if name in cli and cli[name] is not None else getattr(base, name)

    return AxiomIQConfig(
        input=pick("input"),
        out=pick("out"),
        snapshot=pick("snapshot"),
        json_out=pick("json_out"),
        engine=pick("engine"),
        health_drop=float(pick("health_drop")),
        eta_compress=float(pick("eta_compress")),
    )