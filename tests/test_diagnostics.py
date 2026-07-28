"""Tests for GitHub Chatter diagnostics."""

from unittest.mock import MagicMock

import pytest

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.github_chatter.models import GitHubChatterData


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics() -> None:
    coordinator = MagicMock()
    coordinator.last_update_success = False
    coordinator.last_exception = RuntimeError("boom")
    coordinator.data = GitHubChatterData(
        repository="owner/repo",
        windows=["15m"],
        fetched_at="2026-05-06T00:00:00+00:00",
        issue_counts={"15m": 1},
        comment_counts={},
        comment_hhi={},
        top_issues={},
        pulse_score=0.0,
    )
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
        "data": {
            "repository": "owner/repo",
            "windows": ["15m"],
            "fetched_at": "2026-05-06T00:00:00+00:00",
            "issue_counts": {"15m": 1},
            "comment_counts": {},
            "comment_hhi": {},
            "top_issues": {},
            "pulse_score": 0.0,
        },
    }
