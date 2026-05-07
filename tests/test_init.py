"""Tests for GitHub Chatter integration setup."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.const import DOMAIN
from custom_components.github_chatter.coordinator import GitHubChatterCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_config_entry_setup_loads_integration(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch.object(
        GitHubChatterCoordinator, "_async_update_data", return_value=github_chatter_data
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.github_chatter_owner_repo_pulse_score") is not None


@pytest.mark.asyncio
async def test_config_entry_unload_unloads_integration(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch.object(
        GitHubChatterCoordinator, "_async_update_data", return_value=github_chatter_data
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.asyncio
async def test_old_config_entry_migrates_during_setup(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"},
        options={},
        version=0,
    )
    entry.add_to_hass(hass)

    with patch.object(
        GitHubChatterCoordinator, "_async_update_data", return_value=github_chatter_data
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
