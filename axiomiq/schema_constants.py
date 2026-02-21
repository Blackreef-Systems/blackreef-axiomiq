"""
Central contract constants for AxiomIQ.

This module exists to prevent circular imports between:
- report generation
- validation tooling
- CLI entrypoints
"""

SCHEMA_VERSION = "v1"
SCHEMA_RESOURCE_PACKAGE = "axiomiq.schemas"
SCHEMA_RESOURCE_NAME = "axiomiq_report.schema.v1.json"