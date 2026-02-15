import pandas as pd

from axiomiq.core.delta import compute_delta_lines, snapshot_from_fleet


def test_snapshot_from_fleet_runs():
    fleet = pd.DataFrame(
        {
            "engine_id": ["DG1", "DG2"],
            "health": [90.0, 70.0],
            "priority": ["LOW", "MED"],
            "eta_days": [999.0, 14.0],
            "top_risk": ["engine_lo_inlet_pressure_bar", "tc_lo_inlet_pressure_bar"],
        }
    )

    snap = snapshot_from_fleet(fleet.copy())
    assert snap is not None
    assert not snap.empty
    assert "engine_id" in snap.columns
    assert "priority" in snap.columns
    assert "eta_days" in snap.columns


def test_compute_delta_lines_runs():
    fleet_now = pd.DataFrame(
        {
            "engine_id": ["DG1", "DG2"],
            "health": [90.0, 70.0],
            "priority": ["LOW", "MED"],
            "eta_days": [999.0, 10.0],
            "top_risk": ["engine_lo_inlet_pressure_bar", "tc_lo_inlet_pressure_bar"],
        }
    )

    snapshot_prev = pd.DataFrame(
        {
            "engine_id": ["DG1", "DG2"],
            "health": [92.0, 72.0],
            "priority": ["LOW", "LOW"],
            "eta_days": [999.0, 14.0],
            "top_risk": ["engine_lo_inlet_pressure_bar", "engine_lo_inlet_pressure_bar"],
        }
    )

    lines = compute_delta_lines(fleet_now.copy(), snapshot_prev.copy())
    assert lines is not None
    assert isinstance(lines, list)
