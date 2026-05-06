"""Shared test fixtures."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from custom_components.github_chatter import config_flow
from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.coordinator import GitHubChatterCoordinator


@pytest.fixture
def hass() -> MagicMock:
    """Return a Home Assistant stand-in."""
    instance = MagicMock()
    instance.config_entries.async_forward_entry_setups = AsyncMock()
    instance.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return instance


@pytest.fixture
def entry() -> MagicMock:
    """Return a config entry stand-in."""
    config_entry = MagicMock()
    config_entry.data = {CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"}
    config_entry.options = {}
    return config_entry


@pytest.fixture
def user_input() -> dict[str, str]:
    """Return valid config flow input."""
    return {CONF_REPOSITORY: " OpenAI/ChatGPT ", CONF_ACCESS_TOKEN: " token "}


@pytest.fixture
def config_flow_instance(hass: MagicMock) -> Any:
    """Return a config flow instance with Home Assistant methods patched."""
    flow: Any = object.__new__(config_flow.GitHubChatterConfigFlow)
    flow.hass = hass
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


@pytest.fixture
def options_flow_instance() -> Any:
    """Return an options flow instance with Home Assistant methods patched."""
    flow: Any = object.__new__(config_flow.GitHubChatterOptionsFlow)
    flow.async_show_form = MagicMock(return_value={"type": "form"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
    config_entry = MagicMock()
    config_entry.options = {}
    flow.hass = MagicMock()
    flow.hass.config_entries.async_get_known_entry.return_value = config_entry
    flow.handler = "entry-id"
    return flow


@pytest.fixture
def coordinator(entry: MagicMock) -> Any:
    """Return a coordinator with initialized local attributes."""
    instance: Any = object.__new__(GitHubChatterCoordinator)
    instance.entry = entry
    instance._session = MagicMock()
    instance._token = "token"
    instance._repository = "owner/repo"
    instance._owner = "owner"
    instance._repo = "repo"
    return instance


@pytest.fixture
def sensor_coordinator() -> MagicMock:
    """Return a sensor coordinator stand-in."""
    instance = MagicMock()
    instance.entry.data = {CONF_REPOSITORY: "owner/repo"}
    instance.data = {
        "windows": ["15m", "1h"],
        "issue_counts": {"15m": 3},
        "comment_counts": {"15m": 5},
        "comment_hhi": {"15m": 0.75},
        "top_issues": {
            "15m": {
                "number": 4,
                "title": "Top issue",
                "url": "https://example.com/4",
                "comment_count": 5,
            }
        },
        "pulse_score": 42.5,
    }
    return instance
