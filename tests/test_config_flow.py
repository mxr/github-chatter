"""Tests for the GitHub Chatter config flow module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.const import DEFAULT_ENABLE_PULSE
from custom_components.github_chatter.const import DEFAULT_POLL_INTERVAL_SECONDS
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_COMMENTS
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_CONCENTRATION
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_ISSUES
from custom_components.github_chatter.const import DEFAULT_WINDOWS
from custom_components.github_chatter.const import DOMAIN
from custom_components.github_chatter.const import OPTION_ENABLE_PULSE
from custom_components.github_chatter.const import OPTION_POLL_INTERVAL_SECONDS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_COMMENTS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_CONCENTRATION
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_ISSUES
from custom_components.github_chatter.const import OPTION_WINDOWS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant


def _session_for_status(status: int) -> MagicMock:
    response = MagicMock()
    response.status = status
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.get.return_value = context
    return session


async def _start_user_flow(hass: HomeAssistant) -> ConfigFlowResult:
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})


@pytest.mark.asyncio
async def test_user_flow_shows_form_without_input(hass: HomeAssistant) -> None:
    result = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_user_flow_rejects_invalid_repository(hass: HomeAssistant) -> None:
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REPOSITORY: "owner", CONF_ACCESS_TOKEN: "token"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_REPOSITORY: "invalid_repository"}


@pytest.mark.asyncio
async def test_user_flow_creates_entry(
    hass: HomeAssistant,
    user_input: dict[str, str],
) -> None:
    result = await _start_user_flow(hass)

    with patch(
        "custom_components.github_chatter.config_flow.async_get_clientsession",
        return_value=_session_for_status(200),
        autospec=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OpenAI/ChatGPT"
    assert result["data"] == {
        CONF_REPOSITORY: "OpenAI/ChatGPT",
        CONF_ACCESS_TOKEN: "token",
    }
    assert result["options"] == {
        OPTION_POLL_INTERVAL_SECONDS: DEFAULT_POLL_INTERVAL_SECONDS,
        OPTION_WINDOWS: DEFAULT_WINDOWS,
        OPTION_ENABLE_PULSE: DEFAULT_ENABLE_PULSE,
        OPTION_PULSE_WEIGHT_ISSUES: DEFAULT_PULSE_WEIGHT_ISSUES,
        OPTION_PULSE_WEIGHT_COMMENTS: DEFAULT_PULSE_WEIGHT_COMMENTS,
        OPTION_PULSE_WEIGHT_CONCENTRATION: DEFAULT_PULSE_WEIGHT_CONCENTRATION,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("session", "expected_error"),
    [
        pytest.param(_session_for_status(401), "invalid_auth", id="invalid-auth"),
        pytest.param(_session_for_status(404), "repo_not_found", id="repo-not-found"),
        pytest.param(_session_for_status(500), "unknown", id="unknown-error"),
        pytest.param(None, "cannot_connect", id="client-error"),
    ],
)
async def test_user_flow_shows_validation_error(
    hass: HomeAssistant,
    user_input: dict[str, str],
    session: MagicMock | None,
    expected_error: str,
) -> None:
    result = await _start_user_flow(hass)

    patched_session = MagicMock()
    if session is None:
        patched_session.get.side_effect = aiohttp.ClientError("boom")
    else:
        patched_session = session

    with patch(
        "custom_components.github_chatter.config_flow.async_get_clientsession",
        return_value=patched_session,
        autospec=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}


@pytest.mark.asyncio
async def test_options_flow_shows_form_with_defaults(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_creates_options_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    user_input: dict[str, object] = {
        OPTION_POLL_INTERVAL_SECONDS: 600,
        OPTION_ENABLE_PULSE: False,
        OPTION_PULSE_WEIGHT_ISSUES: 0.2,
        OPTION_PULSE_WEIGHT_COMMENTS: 0.3,
        OPTION_PULSE_WEIGHT_CONCENTRATION: 0.5,
        "15m": True,
        "1h": False,
        "24h": True,
        "7d": False,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        OPTION_POLL_INTERVAL_SECONDS: 600,
        OPTION_WINDOWS: ["15m", "24h"],
        OPTION_ENABLE_PULSE: False,
        OPTION_PULSE_WEIGHT_ISSUES: 0.2,
        OPTION_PULSE_WEIGHT_COMMENTS: 0.3,
        OPTION_PULSE_WEIGHT_CONCENTRATION: 0.5,
    }


@pytest.mark.asyncio
async def test_options_flow_uses_default_windows_when_none_selected(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    user_input: dict[str, object] = {
        OPTION_POLL_INTERVAL_SECONDS: 600,
        OPTION_ENABLE_PULSE: True,
        OPTION_PULSE_WEIGHT_ISSUES: 0.2,
        OPTION_PULSE_WEIGHT_COMMENTS: 0.3,
        OPTION_PULSE_WEIGHT_CONCENTRATION: 0.5,
        "15m": False,
        "1h": False,
        "24h": False,
        "7d": False,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][OPTION_WINDOWS] == DEFAULT_WINDOWS
