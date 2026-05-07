"""Test configuration."""

from __future__ import annotations

import pytest

pytest_plugins = ("testing.fixtures",)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for Home Assistant tests."""
