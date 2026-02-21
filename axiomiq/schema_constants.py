"""
Central contract constants for AxiomIQ.

This module prevents circular imports and ensures schema version + schema filename
are derived from a single source of truth.
"""

SCHEMA_VERSION = "v1"

SCHEMA_RESOURCE_PACKAGE = "axiomiq.schemas"
SCHEMA_RESOURCE_NAME = f"axiomiq_report.schema.{SCHEMA_VERSION}.json"