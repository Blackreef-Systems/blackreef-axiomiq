from __future__ import annotations

import importlib.resources as resources

from axiomiq.schema_constants import SCHEMA_RESOURCE_NAME, SCHEMA_RESOURCE_PACKAGE


def test_schema_resource_is_bundled_and_readable() -> None:
    """
    Proves the JSON schema is actually shipped inside the package and readable via
    importlib.resources (works in editable installs AND wheels).
    """
    txt = (
        resources.files(SCHEMA_RESOURCE_PACKAGE)
        .joinpath(SCHEMA_RESOURCE_NAME)
        .read_text(encoding="utf-8")
    )
    assert isinstance(txt, str)
    assert len(txt) > 50
    assert '"$schema"' in txt