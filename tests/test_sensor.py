"""Tests for GitHub Chatter sensors."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.github_chatter.const import CONF_REPOSITORY
from custom_components.github_chatter.const import OPTION_ENABLE_PULSE
from custom_components.github_chatter.sensor import COMMENT_COUNT_DESCRIPTION
from custom_components.github_chatter.sensor import COMMENT_HHI_DESCRIPTION
from custom_components.github_chatter.sensor import ISSUE_COUNT_DESCRIPTION
from custom_components.github_chatter.sensor import PULSE_DESCRIPTION
from custom_components.github_chatter.sensor import TOP_ISSUE_DESCRIPTION
from custom_components.github_chatter.sensor import GitHubChatterSensor
from custom_components.github_chatter.sensor import async_setup_entry


@pytest.fixture
def coordinator() -> MagicMock:
    """Return a coordinator stand-in."""
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enable_pulse", "expected_count"),
    [
        pytest.param(True, 9, id="pulse-enabled"),
        pytest.param(False, 8, id="pulse-disabled"),
    ],
)
async def test_async_setup_entry_adds_window_entities(
    enable_pulse: bool, expected_count: int, coordinator: MagicMock
) -> None:
    entry = MagicMock()
    entry.runtime_data = coordinator
    entry.options = {OPTION_ENABLE_PULSE: enable_pulse}
    async_add_entities = MagicMock()

    await async_setup_entry(MagicMock(), entry, async_add_entities)

    entities = async_add_entities.call_args.args[0]
    assert len(entities) == expected_count


@pytest.mark.parametrize(
    ("description", "window", "expected"),
    [
        pytest.param(ISSUE_COUNT_DESCRIPTION, "15m", 3, id="issue-count"),
        pytest.param(COMMENT_COUNT_DESCRIPTION, "15m", 5, id="comment-count"),
        pytest.param(COMMENT_HHI_DESCRIPTION, "15m", 0.75, id="comment-hhi"),
        pytest.param(TOP_ISSUE_DESCRIPTION, "15m", "Top issue", id="top-issue"),
        pytest.param(PULSE_DESCRIPTION, None, 42.5, id="pulse"),
    ],
)
def test_sensor_native_value(
    description: Any, window: str | None, expected: Any, coordinator: MagicMock
) -> None:
    sensor = GitHubChatterSensor(coordinator, description, window)

    assert sensor.native_value == expected
    assert (
        sensor.unique_id
        == f"owner_repo_{description.key}{'_' + window if window else ''}"
    )


def test_sensor_extra_state_attributes_returns_none(coordinator: MagicMock) -> None:
    sensor = GitHubChatterSensor(coordinator, ISSUE_COUNT_DESCRIPTION, "15m")

    assert sensor.extra_state_attributes is None


def test_sensor_extra_state_attributes_includes_window(coordinator: MagicMock) -> None:
    sensor = GitHubChatterSensor(coordinator, TOP_ISSUE_DESCRIPTION, "15m")

    assert sensor.extra_state_attributes == {
        "window": "15m",
        "number": 4,
        "title": "Top issue",
        "url": "https://example.com/4",
        "comment_count": 5,
    }
