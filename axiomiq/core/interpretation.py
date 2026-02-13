from __future__ import annotations


INTERPRETATION_RULES = {
    "charge_air_pressure_bar": {
        "system": "Air Intake / Turbocharging",
        "direction": "decreasing",
        "meaning": (
            "A sustained decline in charge air pressure may indicate intake restriction, "
            "air filter fouling, or reduced turbocharger efficiency."
        ),
        "risk_type": "Performance degradation leading to thermal stress"
    },
    "lo_inlet_temp_c": {
        "system": "Lubrication Oil",
        "direction": "increasing",
        "meaning": (
            "Rising lube oil inlet temperature can indicate reduced cooling efficiency, "
            "oil cooler fouling, or increased engine friction."
        ),
        "risk_type": "Accelerated wear and oil breakdown"
    },
    "tc_lo_inlet_pressure_bar": {
        "system": "Turbocharger Lubrication",
        "direction": "decreasing",
        "meaning": (
            "Declining turbocharger lube oil pressure may suggest filter restriction "
            "or pump performance issues."
        ),
        "risk_type": "Turbocharger bearing wear"
    },
    "htcw_engine_outlet_temp_c": {
        "system": "High Temperature Cooling Water",
        "direction": "increasing",
        "meaning": (
            "Increasing HT cooling water outlet temperature may indicate reduced heat transfer, "
            "cooler fouling, or elevated engine thermal load."
        ),
        "risk_type": "Thermal stress and reduced margin"
    },
    "engine_lo_inlet_pressure_bar": {
        "system": "Main Lubrication System",
        "direction": "decreasing",
        "meaning": (
            "A gradual drop in lube oil inlet pressure can indicate filter loading, "
            "pump wear, or internal leakage."
        ),
        "risk_type": "Loss of lubrication margin"
    }
}


def interpret_param(param: str) -> dict[str, str]:
    """
    Return interpretation metadata for a parameter.
    """
    return INTERPRETATION_RULES.get(
        param,
        {
            "system": "Unknown",
            "direction": "unknown",
            "meaning": "No interpretation rule defined for this parameter.",
            "risk_type": "Unclassified risk"
        }
    )