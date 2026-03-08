# axiomiq/report/signal_catalog.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class SignalMeta:
    long_name: str
    short_name: str
    unit: str | None = None

# Map internal telemetry keys -> human-readable metadata.
# Keep internal key in the report as a secondary label (small).
SIGNALS: dict[str, SignalMeta] = {
    "lo_inlet_pressure_bar": SignalMeta("Lube Oil Inlet Pressure", "LO Inlet Press", "bar"),
    "lo_inlet_temp_c": SignalMeta("Lube Oil Inlet Temperature", "LO Inlet Temp", "°C"),
    "htcw_engine_outlet_temp_c": SignalMeta("HT Cooling Water Outlet Temperature", "HTCW Outlet Temp", "°C"),
    "charge_air_pressure_bar": SignalMeta("Charge Air Pressure", "Charge Air Press", "bar"),
    "tc_lo_inlet_pressure_bar": SignalMeta("Turbocharger Lube Oil Inlet Pressure", "TC LO Inlet Press", "bar"),
    "engine_lo_inlet_pressure_bar": SignalMeta("Main Lube Oil Inlet Pressure", "Main LO Inlet Press", "bar"),
    # Add more as your models evolve.
}

def signal_display_name(key: str) -> tuple[str, str]:
    """Returns (primary label, secondary label)."""
    meta = SIGNALS.get(key)
    if meta:
        return meta.long_name, f"{meta.short_name} • {key}"
    return key.replace("_", " ").title(), key