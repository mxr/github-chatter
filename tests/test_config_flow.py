"""Tests for the GitHub Chatter config flow module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import aiohttp
import pytest

from custom_components.github_chatter import config_flow
from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.const import DEFAULT_ENABLE_PULSE
from custom_components.github_chatter.const import DEFAULT_POLL_INTERVAL_SECONDS
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_COMMENTS
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_CONCENTRATION
from custom_components.github_chatter.const import DEFAULT_PULSE_WEIGHT_ISSUES
from custom_components.github_chatter.const import DEFAULT_WINDOWS
from custom_components.github_chatter.const import OPTION_ENABLE_PULSE
from custom_components.github_chatter.const import OPTION_POLL_INTERVAL_SECONDS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_COMMENTS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_CONCENTRATION
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_ISSUES
from custom_components.github_chatter.const import OPTION_WINDOWS


@pytest.fixture
def hass() -> MagicMock:
    """Return a Home Assistant stand-in."""
    return MagicMock()


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


def _session_for_status(status: int) -> MagicMock:
    response = MagicMock()
    response.status = status
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.get.return_value = context
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(200, None, id="success"),
        pytest.param(401, "invalid_auth", id="invalid-auth"),
        pytest.param(404, "repo_not_found", id="repo-not-found"),
        pytest.param(500, "unknown", id="unknown-error"),
    ],
)
@patch(
    "custom_components.github_chatter.config_flow.async_get_clientsession",
    autospec=True,
)
async def test_validate_credentials_maps_statuses(
    async_get_clientsession: MagicMock,
    status: int,
    expected: str | None,
    hass: MagicMock,
) -> None:
    async_get_clientsession.return_value = _session_for_status(status)

    assert (
        await config_flow._validate_credentials(hass, "owner/repo", "token") == expected
    )


@pytest.mark.asyncio
@patch(
    "custom_components.github_chatter.config_flow.async_get_clientsession",
    autospec=True,
)
async def test_validate_credentials_maps_client_error(
    async_get_clientsession: MagicMock,
    hass: MagicMock,
) -> None:
    session = MagicMock()
    session.get.side_effect = aiohttp.ClientError("boom")
    async_get_clientsession.return_value = session

    assert (
        await config_flow._validate_credentials(hass, "owner/repo", "token")
        == "cannot_connect"
    )


@pytest.mark.asyncio
async def test_async_step_user_shows_form_without_input(
    config_flow_instance: Any,
) -> None:
    result = await config_flow_instance.async_step_user()

    assert result == {"type": "form"}
    config_flow_instance.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_async_step_user_rejects_invalid_repository(
    config_flow_instance: Any,
) -> None:
    result = await config_flow_instance.async_step_user(
        {CONF_REPOSITORY: "owner", CONF_ACCESS_TOKEN: "token"}
    )

    assert result == {"type": "form"}
    config_flow_instance.async_show_form.assert_called_once()
    assert config_flow_instance.async_show_form.call_args.kwargs["errors"] == {
        CONF_REPOSITORY: "invalid_repository"
    }


@pytest.mark.asyncio
@patch(
    "custom_components.github_chatter.config_flow._validate_credentials", autospec=True
)
async def test_async_step_user_creates_entry(
    validate_credentials: AsyncMock,
    config_flow_instance: Any,
    user_input: dict[str, str],
) -> None:
    validate_credentials.return_value = None

    result = await config_flow_instance.async_step_user(user_input)

    assert result == {"type": "create_entry"}
    config_flow_instance.async_set_unique_id.assert_awaited_once_with("openai/chatgpt")
    config_flow_instance._abort_if_unique_id_configured.assert_called_once_with()
    config_flow_instance.async_create_entry.assert_called_once_with(
        title="OpenAI/ChatGPT",
        data={CONF_REPOSITORY: "OpenAI/ChatGPT", CONF_ACCESS_TOKEN: "token"},
        options={
            OPTION_POLL_INTERVAL_SECONDS: DEFAULT_POLL_INTERVAL_SECONDS,
            OPTION_WINDOWS: DEFAULT_WINDOWS,
            OPTION_ENABLE_PULSE: DEFAULT_ENABLE_PULSE,
            OPTION_PULSE_WEIGHT_ISSUES: DEFAULT_PULSE_WEIGHT_ISSUES,
            OPTION_PULSE_WEIGHT_COMMENTS: DEFAULT_PULSE_WEIGHT_COMMENTS,
            OPTION_PULSE_WEIGHT_CONCENTRATION: DEFAULT_PULSE_WEIGHT_CONCENTRATION,
        },
    )


@pytest.mark.asyncio
@patch(
    "custom_components.github_chatter.config_flow._validate_credentials", autospec=True
)
async def test_async_step_user_shows_validation_error(
    validate_credentials: AsyncMock,
    config_flow_instance: Any,
    user_input: dict[str, str],
) -> None:
    validate_credentials.return_value = "invalid_auth"

    result = await config_flow_instance.async_step_user(user_input)

    assert result == {"type": "form"}
    assert config_flow_instance.async_show_form.call_args.kwargs["errors"] == {
        "base": "invalid_auth"
    }


def test_async_get_options_flow_returns_no_arg_options_flow() -> None:
    flow = config_flow.GitHubChatterConfigFlow.async_get_options_flow(MagicMock())

    assert isinstance(flow, config_flow.GitHubChatterOptionsFlow)


@pytest.mark.asyncio
async def test_async_step_init_shows_options_form_with_defaults(
    options_flow_instance: Any,
) -> None:
    result = await options_flow_instance.async_step_init()

    assert result == {"type": "form"}
    options_flow_instance.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_async_step_init_creates_options_entry(
    options_flow_instance: Any,
) -> None:
    user_input: dict[str, Any] = {
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

    result = await options_flow_instance.async_step_init(user_input)

    assert result == {"type": "create_entry"}
    options_flow_instance.async_create_entry.assert_called_once_with(
        title="",
        data={
            OPTION_POLL_INTERVAL_SECONDS: 600,
            OPTION_WINDOWS: ["15m", "24h"],
            OPTION_ENABLE_PULSE: False,
            OPTION_PULSE_WEIGHT_ISSUES: 0.2,
            OPTION_PULSE_WEIGHT_COMMENTS: 0.3,
            OPTION_PULSE_WEIGHT_CONCENTRATION: 0.5,
        },
    )


@pytest.mark.asyncio
async def test_async_step_init_uses_default_windows_when_none_selected(
    options_flow_instance: Any,
) -> None:
    user_input: dict[str, Any] = {
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

    await options_flow_instance.async_step_init(user_input)

    assert (
        options_flow_instance.async_create_entry.call_args.kwargs["data"][
            OPTION_WINDOWS
        ]
        == DEFAULT_WINDOWS
    )
