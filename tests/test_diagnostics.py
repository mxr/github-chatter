"""Tests for GitHub Chatter diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.diagnostics import (
    async_get_config_entry_diagnostics,
)


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics() -> None:
    coordinator = MagicMock()
    coordinator.last_update_success = False
    coordinator.last_exception = RuntimeError("boom")
    coordinator.data = {"issue_counts": {"15m": 1}}
    entry = MagicMock()
    entry.data = {CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "secret"}
    entry.options = {"windows": ["15m"]}
    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(MagicMock(), entry)

    assert diagnostics == {
        "entry": {CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "**REDACTED**"},
        "options": {"windows": ["15m"]},
        "last_update_success": False,
        "last_exception": "boom",
        "data": {"issue_counts": {"15m": 1}},
    }
