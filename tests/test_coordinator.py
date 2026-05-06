"""Tests for GitHub Chatter coordinator."""

from __future__ import annotations

import re
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.github_chatter.const import API_BASE_URL
from custom_components.github_chatter.const import DEFAULT_WINDOWS
from custom_components.github_chatter.const import ISSUE_NORMALIZATION_SCALE
from custom_components.github_chatter.const import OPTION_ENABLE_PULSE
from custom_components.github_chatter.const import OPTION_POLL_INTERVAL_SECONDS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_COMMENTS
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_CONCENTRATION
from custom_components.github_chatter.const import OPTION_PULSE_WEIGHT_ISSUES
from custom_components.github_chatter.const import OPTION_WINDOWS
from custom_components.github_chatter.coordinator import GitHubChatterCoordinator


def _response_context(
    *,
    status: int = 200,
    payload: Any = None,
    text: str = "error",
    links: dict[str, Any] | None = None,
) -> tuple[MagicMock, MagicMock]:
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=payload if payload is not None else {})
    response.text = AsyncMock(return_value=text)
    response.links = links or {}
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=None)
    return context, response


@patch(
    "custom_components.github_chatter.coordinator.DataUpdateCoordinator.__init__",
    return_value=None,
    autospec=True,
)
@patch(
    "custom_components.github_chatter.coordinator.async_get_clientsession",
    autospec=True,
)
def test_init_sets_repository_state(
    async_get_clientsession: MagicMock,
    data_update_coordinator_init: MagicMock,
    hass: MagicMock,
    entry: MagicMock,
) -> None:
    entry.options = {OPTION_POLL_INTERVAL_SECONDS: "120"}
    session = MagicMock()
    async_get_clientsession.return_value = session

    coordinator = GitHubChatterCoordinator(hass, entry)

    assert coordinator.entry is entry
    assert coordinator._session is session
    assert coordinator._token == "token"
    assert coordinator._owner == "owner"
    assert coordinator._repo == "repo"
    data_update_coordinator_init.assert_called_once()


def test_active_windows_returns_ordered_configured_windows(
    coordinator: Any, entry: MagicMock
) -> None:
    entry.options = {OPTION_WINDOWS: ["7d", "15m", "invalid"]}

    assert coordinator._active_windows == ["15m", "7d"]


def test_active_windows_falls_back_to_defaults(
    coordinator: Any, entry: MagicMock
) -> None:
    entry.options = {OPTION_WINDOWS: ["invalid"]}

    assert coordinator._active_windows == DEFAULT_WINDOWS


def test_headers_include_token(coordinator: Any) -> None:
    assert coordinator._headers() == {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer token",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@pytest.mark.asyncio
@patch.object(GitHubChatterCoordinator, "_fetch_paginated", autospec=True)
async def test_fetch_issues_since_filters_pull_requests(
    fetch_paginated: AsyncMock, coordinator: Any
) -> None:
    fetch_paginated.return_value = [{"number": 1}, {"number": 2, "pull_request": {}}]

    issues = await coordinator._fetch_issues_since(datetime(2026, 5, 6, tzinfo=UTC))

    assert issues == [{"number": 1}]
    fetch_paginated.assert_awaited_once_with(
        coordinator,
        f"{API_BASE_URL}/repos/owner/repo/issues",
        {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "since": "2026-05-06T00:00:00Z",
            "per_page": 100,
        },
    )


@pytest.mark.asyncio
@patch.object(GitHubChatterCoordinator, "_fetch_paginated", autospec=True)
async def test_fetch_comments_since_uses_comments_endpoint(
    fetch_paginated: AsyncMock, coordinator: Any
) -> None:
    fetch_paginated.return_value = [{"id": 1}]

    comments = await coordinator._fetch_comments_since(datetime(2026, 5, 6, tzinfo=UTC))

    assert comments == [{"id": 1}]
    fetch_paginated.assert_awaited_once_with(
        coordinator,
        f"{API_BASE_URL}/repos/owner/repo/issues/comments",
        {
            "sort": "created",
            "direction": "desc",
            "since": "2026-05-06T00:00:00Z",
            "per_page": 100,
        },
    )


@pytest.mark.asyncio
@patch.object(GitHubChatterCoordinator, "_fetch_json", autospec=True)
async def test_fetch_issue_details(fetch_json: AsyncMock, coordinator: Any) -> None:
    fetch_json.side_effect = [
        {"number": 2, "title": "second", "html_url": "https://example.com/2"},
        {"number": 5, "title": "fifth", "html_url": "https://example.com/5"},
    ]

    assert await coordinator._fetch_issue_details({5, 2}) == {
        2: {"number": 2, "title": "second", "url": "https://example.com/2"},
        5: {"number": 5, "title": "fifth", "url": "https://example.com/5"},
    }
    fetch_json.assert_has_awaits(
        [
            call(coordinator, f"{API_BASE_URL}/repos/owner/repo/issues/2"),
            call(coordinator, f"{API_BASE_URL}/repos/owner/repo/issues/5"),
        ]
    )


@pytest.mark.asyncio
async def test_fetch_json_returns_payload(
    coordinator: Any,
) -> None:
    context, _response = _response_context(payload={"ok": True})
    coordinator._session.get.return_value = context

    assert await coordinator._fetch_json("https://example.com", {"a": "b"}) == {
        "ok": True
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "message"),
    [
        pytest.param(401, "GitHub authentication failed (401).", id="auth"),
        pytest.param(
            403,
            "GitHub API returned 403 (rate limit or access denied).",
            id="forbidden",
        ),
        pytest.param(500, "GitHub API error 500: long error", id="server-error"),
    ],
)
async def test_fetch_json_raises_update_failed(
    status: int, message: str, coordinator: Any
) -> None:
    context, _response = _response_context(status=status, text="long error")
    coordinator._session.get.return_value = context

    with pytest.raises(UpdateFailed, match=re.escape(message)):
        await coordinator._fetch_json("https://example.com")


@pytest.mark.asyncio
async def test_fetch_json_maps_client_error(
    coordinator: Any,
) -> None:
    coordinator._session.get.side_effect = aiohttp.ClientError("boom")

    with pytest.raises(UpdateFailed, match="Error communicating with GitHub API: boom"):
        await coordinator._fetch_json("https://example.com")


@pytest.mark.asyncio
async def test_fetch_paginated_follows_next_link(
    coordinator: Any,
) -> None:
    first_context, _first_response = _response_context(
        payload=[{"id": 1}], links={"next": {"url": "https://example.com/next"}}
    )
    second_context, _second_response = _response_context(payload=[{"id": 2}])
    coordinator._session.get.side_effect = [first_context, second_context]

    assert await coordinator._fetch_paginated(
        "https://example.com/start", {"per_page": 100}
    ) == [{"id": 1}, {"id": 2}]
    assert coordinator._session.get.call_args_list[0].kwargs["params"] == {
        "per_page": 100
    }
    assert coordinator._session.get.call_args_list[1].kwargs["params"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "message"),
    [
        pytest.param(401, "GitHub authentication failed (401).", id="auth"),
        pytest.param(
            403,
            "GitHub API returned 403 (rate limit or access denied).",
            id="forbidden",
        ),
        pytest.param(500, "GitHub API error 500: long error", id="server-error"),
    ],
)
async def test_fetch_paginated_raises_update_failed(
    status: int, message: str, coordinator: Any
) -> None:
    context, _response = _response_context(status=status, payload=[], text="long error")
    coordinator._session.get.return_value = context

    with pytest.raises(UpdateFailed, match=re.escape(message)):
        await coordinator._fetch_paginated("https://example.com", {})


@pytest.mark.asyncio
async def test_fetch_paginated_rejects_unexpected_payload(
    coordinator: Any,
) -> None:
    context, _response = _response_context(payload={"items": []})
    coordinator._session.get.return_value = context

    with pytest.raises(UpdateFailed, match="unexpected payload"):
        await coordinator._fetch_paginated("https://example.com", {})


@pytest.mark.asyncio
async def test_fetch_paginated_maps_client_error(
    coordinator: Any,
) -> None:
    coordinator._session.get.side_effect = aiohttp.ClientError("boom")

    with pytest.raises(UpdateFailed, match="Error communicating with GitHub API: boom"):
        await coordinator._fetch_paginated("https://example.com", {})


def test_count_by_window(coordinator: Any) -> None:
    now = datetime(2026, 5, 6, 12, tzinfo=UTC)

    assert coordinator._count_by_window(
        ["2026-05-06T11:50:00Z", "2026-05-06T11:00:00Z", "not a date"],
        ["15m", "1h"],
        now,
    ) == {"15m": 1, "1h": 2}


def test_comment_issue_counts_by_window(coordinator: Any) -> None:
    now = datetime(2026, 5, 6, 12, tzinfo=UTC)
    comments: list[dict[str, Any]] = [
        {
            "created_at": "2026-05-06T11:50:00Z",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/3",
        },
        {
            "created_at": "2026-05-06T11:30:00Z",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/3",
        },
        {
            "created_at": "2026-05-06T11:40:00Z",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/not-int",
        },
        {
            "created_at": None,
            "issue_url": "https://api.github.com/repos/owner/repo/issues/4",
        },
        {
            "created_at": "not a date",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/4",
        },
        {"created_at": "2026-05-06T11:40:00Z", "issue_url": None},
    ]

    counts = coordinator._comment_issue_counts_by_window(comments, ["15m", "1h"], now)

    assert dict(counts["15m"]) == {3: 1}
    assert dict(counts["1h"]) == {3: 2}


@pytest.mark.parametrize(
    ("issue_url", "expected"),
    [
        pytest.param(
            "https://api.github.com/repos/owner/repo/issues/7", 7, id="valid-url"
        ),
        pytest.param(
            "https://api.github.com/repos/owner/repo/issues/7/", 7, id="trailing-slash"
        ),
        pytest.param("bad", None, id="bad-url"),
    ],
)
def test_issue_number_from_url(issue_url: str, expected: int | None) -> None:
    assert GitHubChatterCoordinator._issue_number_from_url(issue_url) == expected


@pytest.mark.parametrize(
    ("issue_counts", "expected"),
    [
        pytest.param({}, None, id="empty"),
        pytest.param({5: 2, 3: 2, 1: 1}, 3, id="ties-lowest-number"),
    ],
)
def test_top_issue_number(issue_counts: dict[int, int], expected: int | None) -> None:
    assert GitHubChatterCoordinator._top_issue_number(issue_counts) == expected


@pytest.mark.parametrize(
    ("issue_number", "issue_details", "expected"),
    [
        pytest.param(None, {}, None, id="none"),
        pytest.param(
            4,
            {},
            {"number": 4, "title": "Issue #4", "url": None, "comment_count": 3},
            id="fallback",
        ),
        pytest.param(
            4,
            {4: {"number": 4, "title": "Known", "url": "https://example.com/4"}},
            {
                "number": 4,
                "title": "Known",
                "url": "https://example.com/4",
                "comment_count": 3,
            },
            id="details",
        ),
    ],
)
def test_build_top_issue_payload(
    issue_number: int | None,
    issue_details: dict[int, dict[str, Any]],
    expected: dict[str, Any] | None,
) -> None:
    assert (
        GitHubChatterCoordinator._build_top_issue_payload(
            issue_number, {4: 3}, issue_details
        )
        == expected
    )


def test_window_weighted_signal() -> None:
    assert (
        GitHubChatterCoordinator._window_weighted_signal(
            {}, ISSUE_NORMALIZATION_SCALE, []
        )
        == 0.0
    )
    assert (
        GitHubChatterCoordinator._window_weighted_signal(
            {"15m": 99}, ISSUE_NORMALIZATION_SCALE, ["15m"]
        )
        == 1.0
    )


def test_window_weighted_hhi() -> None:
    assert GitHubChatterCoordinator._window_weighted_hhi({}, []) == 0.0
    assert GitHubChatterCoordinator._window_weighted_hhi({"15m": 0.5}, ["15m"]) == 0.5


def test_compute_pulse_score(coordinator: Any, entry: MagicMock) -> None:
    entry.options = {
        OPTION_PULSE_WEIGHT_ISSUES: 0.5,
        OPTION_PULSE_WEIGHT_COMMENTS: 0.5,
        OPTION_PULSE_WEIGHT_CONCENTRATION: 0.0,
    }

    assert (
        coordinator._compute_pulse_score({"15m": 3}, {"15m": 10}, {"15m": 0.0}, ["15m"])
        == 100.0
    )


def test_compute_pulse_score_returns_zero_when_disabled(
    coordinator: Any, entry: MagicMock
) -> None:
    entry.options = {OPTION_ENABLE_PULSE: False}

    assert (
        coordinator._compute_pulse_score({"15m": 3}, {"15m": 10}, {"15m": 1.0}, ["15m"])
        == 0.0
    )


def test_compute_pulse_score_returns_zero_when_weights_are_zero(
    coordinator: Any, entry: MagicMock
) -> None:
    entry.options = {
        OPTION_PULSE_WEIGHT_ISSUES: 0.0,
        OPTION_PULSE_WEIGHT_COMMENTS: 0.0,
        OPTION_PULSE_WEIGHT_CONCENTRATION: 0.0,
    }

    assert (
        coordinator._compute_pulse_score({"15m": 3}, {"15m": 10}, {"15m": 1.0}, ["15m"])
        == 0.0
    )


@pytest.mark.asyncio
@patch("custom_components.github_chatter.coordinator.dt_util.utcnow", autospec=True)
@patch.object(GitHubChatterCoordinator, "_fetch_issue_details", autospec=True)
@patch.object(GitHubChatterCoordinator, "_fetch_comments_since", autospec=True)
@patch.object(GitHubChatterCoordinator, "_fetch_issues_since", autospec=True)
async def test_async_update_data(
    fetch_issues_since: AsyncMock,
    fetch_comments_since: AsyncMock,
    fetch_issue_details: AsyncMock,
    utcnow: MagicMock,
    coordinator: Any,
    entry: MagicMock,
) -> None:
    now = datetime(2026, 5, 6, 12, tzinfo=UTC)
    entry.options = {OPTION_WINDOWS: ["15m"]}
    utcnow.return_value = now
    fetch_issues_since.return_value = [{"created_at": "2026-05-06T11:50:00Z"}]
    fetch_comments_since.return_value = [
        {
            "created_at": "2026-05-06T11:55:00Z",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/2",
        },
        {
            "created_at": "2026-05-06T11:54:00Z",
            "issue_url": "https://api.github.com/repos/owner/repo/issues/2",
        },
    ]
    fetch_issue_details.return_value = {
        2: {"number": 2, "title": "Busy issue", "url": "https://example.com/2"}
    }

    data = await coordinator._async_update_data()

    assert data == {
        "repository": "owner/repo",
        "windows": ["15m"],
        "fetched_at": "2026-05-06T12:00:00+00:00",
        "issue_counts": {"15m": 1},
        "comment_counts": {"15m": 2},
        "comment_hhi": {"15m": 1.0},
        "top_issues": {
            "15m": {
                "number": 2,
                "title": "Busy issue",
                "url": "https://example.com/2",
                "comment_count": 2,
            }
        },
        "pulse_score": 34.0,
    }
    fetch_issues_since.assert_awaited_once_with(
        coordinator, now - timedelta(minutes=15)
    )
    fetch_issue_details.assert_awaited_once_with(coordinator, {2})
