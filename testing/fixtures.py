"""Shared test fixtures."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.coordinator import GitHubChatterCoordinator


@pytest.fixture
def entry() -> MockConfigEntry:
    """Return a config entry."""
    return MockConfigEntry(
        domain="github_chatter",
        data={CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"},
        options={},
    )


@pytest.fixture
def user_input() -> dict[str, str]:
    """Return valid config flow input."""
    return {CONF_REPOSITORY: " OpenAI/ChatGPT ", CONF_ACCESS_TOKEN: " token "}


@pytest.fixture
def github_chatter_data() -> dict[str, Any]:
    """Return coordinator data."""
    return {
        "windows": ["15m", "1h"],
        "issue_counts": {"15m": 3, "1h": 7},
        "comment_counts": {"15m": 5, "1h": 11},
        "comment_hhi": {"15m": 0.75, "1h": 0.35},
        "top_issues": {
            "15m": {
                "number": 4,
                "title": "Top issue",
                "url": "https://example.com/4",
                "comment_count": 5,
            },
            "1h": {
                "number": 8,
                "title": "Other issue",
                "url": "https://example.com/8",
                "comment_count": 3,
            },
        },
        "pulse_score": 42.5,
    }


@pytest.fixture
def coordinator(entry: MockConfigEntry) -> GitHubChatterCoordinator:
    """Return a coordinator with initialized local attributes."""
    instance = object.__new__(GitHubChatterCoordinator)
    instance.entry = entry
    instance._session = MagicMock()
    instance._token = "token"
    instance._repository = "owner/repo"
    instance._owner = "owner"
    instance._repo = "repo"
    return instance
