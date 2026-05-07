"""Tests for GitHub Chatter sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.github_chatter.const import CONF_ACCESS_TOKEN
from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.const import DOMAIN
from custom_components.github_chatter.const import OPTION_ENABLE_PULSE
from custom_components.github_chatter.coordinator import GitHubChatterCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _setup_entry(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
    *,
    options: dict[str, object] | None = None,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REPOSITORY: "owner/repo", CONF_ACCESS_TOKEN: "token"},
        options=options or {},
    )
    entry.add_to_hass(hass)

    with patch.object(
        GitHubChatterCoordinator, "_async_update_data", return_value=github_chatter_data
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    return entry


def _entity_id(hass: HomeAssistant, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


@pytest.mark.asyncio
async def test_sensors_expose_coordinator_data_through_state_machine(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    await _setup_entry(hass, github_chatter_data)

    states = {
        "owner_repo_issue_creation_count_15m": "3",
        "owner_repo_issue_comment_count_15m": "5",
        "owner_repo_comment_hhi_15m": "0.75",
        "owner_repo_top_commented_issue_15m": "Top issue",
        "owner_repo_pulse_score": "42.5",
    }

    for unique_id, expected_state in states.items():
        state = hass.states.get(_entity_id(hass, unique_id))
        assert state is not None
        assert state.state == expected_state

    top_issue_state = hass.states.get(
        _entity_id(hass, "owner_repo_top_commented_issue_15m")
    )
    assert top_issue_state is not None
    assert top_issue_state.attributes["window"] == "15m"
    assert top_issue_state.attributes["number"] == 4
    assert top_issue_state.attributes["url"] == "https://example.com/4"
    assert top_issue_state.attributes["comment_count"] == 5


@pytest.mark.asyncio
async def test_sensor_setup_respects_pulse_option(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    await _setup_entry(hass, github_chatter_data, options={OPTION_ENABLE_PULSE: False})

    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, "owner_repo_pulse_score"
        )
        is None
    )
    assert (
        hass.states.get(_entity_id(hass, "owner_repo_issue_creation_count_15m"))
        is not None
    )


@pytest.mark.asyncio
async def test_sensors_create_entity_and_device_registry_entries(
    hass: HomeAssistant,
    github_chatter_data: dict[str, object],
) -> None:
    await _setup_entry(hass, github_chatter_data)

    entity_entry = er.async_get(hass).async_get(
        _entity_id(hass, "owner_repo_issue_creation_count_15m")
    )
    assert entity_entry is not None
    assert entity_entry.unique_id == "owner_repo_issue_creation_count_15m"
    assert entity_entry.platform == DOMAIN

    device_entry = dr.async_get(hass).async_get_device({(DOMAIN, "owner/repo")})
    assert device_entry is not None
    assert device_entry.name == "GitHub Chatter owner/repo"
    assert device_entry.manufacturer == "GitHub"
    assert device_entry.configuration_url == "https://github.com/owner/repo"
