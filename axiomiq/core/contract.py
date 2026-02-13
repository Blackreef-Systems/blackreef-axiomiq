# axiomiq/core/contract.py
"""
AxiomIQ Decision Contract

This module defines the locked decision thresholds and versioning for
how AxiomIQ maps analytics → operational actions.

If you change any constants in here, bump AXIOMIQ_DECISION_VERSION.
"""

AXIOMIQ_DECISION_VERSION = "0.1.0"

# Delta / change-detection triggers (used for "Key Changes Since Last Report")
DEFAULT_HEALTH_DROP_TRIGGER_POINTS = 2.0
DEFAULT_ETA_COMPRESS_TRIGGER_DAYS = 7.0

# Priority rules (fleet ranking)
# Note: ETA = time-to-limit (days). Lower is worse.
HIGH_PRIORITY_ETA_DAYS = 7.0
MED_PRIORITY_ETA_DAYS = 30.0

# Health fallback when ETA unavailable
MED_PRIORITY_HEALTH_BELOW = 80.0

# Action rules
ACTION_HIGH_ETA_DAYS = 3.0  # if ETA <= 3d, escalate to immediate inspection

ACTION_TEXT_HIGH = "Inspect <72h"
ACTION_TEXT_MED = "Sched next maint"
ACTION_TEXT_LOW = "Monitor (30d)"