"""Tests for GitHub Chatter integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from custom_components.github_chatter import PLATFORMS
from custom_components.github_chatter import async_migrate_entry
from custom_components.github_chatter import async_setup_entry
from custom_components.github_chatter import async_unload_entry


@pytest.mark.asyncio
@patch("custom_components.github_chatter.GitHubChatterCoordinator", autospec=True)
async def test_async_setup_entry_sets_runtime_data(
    coordinator_cls: MagicMock,
    hass: MagicMock,
    entry: MagicMock,
) -> None:
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator_cls.return_value = coordinator

    assert await async_setup_entry(hass, entry) is True
    coordinator_cls.assert_called_once_with(hass=hass, entry=entry)
    coordinator.async_config_entry_first_refresh.assert_awaited_once_with()
    assert entry.runtime_data is coordinator
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )


@pytest.mark.asyncio
async def test_async_unload_entry(hass: MagicMock, entry: MagicMock) -> None:
    assert await async_unload_entry(hass, entry) is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        entry, PLATFORMS
    )


@pytest.mark.asyncio
async def test_async_migrate_entry(hass: MagicMock, entry: MagicMock) -> None:
    assert await async_migrate_entry(hass, entry) is True
