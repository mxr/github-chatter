"""Coordinator for GitHub Chatter data updates."""

from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from typing import TYPE_CHECKING
from typing import Any

import aiohttp
import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from .const import API_BASE_URL
from .const import COMMENT_NORMALIZATION_SCALE
from .const import CONF_ACCESS_TOKEN
from .const import CONF_REPOSITORY
from .const import DEFAULT_ENABLE_PULSE
from .const import DEFAULT_POLL_INTERVAL_SECONDS
from .const import DEFAULT_PULSE_WEIGHT_COMMENTS
from .const import DEFAULT_PULSE_WEIGHT_CONCENTRATION
from .const import DEFAULT_PULSE_WEIGHT_ISSUES
from .const import DEFAULT_WINDOWS
from .const import GITHUB_TIMEOUT_SECONDS
from .const import ISSUE_NORMALIZATION_SCALE
from .const import LOGGER
from .const import OPTION_ENABLE_PULSE
from .const import OPTION_POLL_INTERVAL_SECONDS
from .const import OPTION_PULSE_WEIGHT_COMMENTS
from .const import OPTION_PULSE_WEIGHT_CONCENTRATION
from .const import OPTION_PULSE_WEIGHT_ISSUES
from .const import OPTION_WINDOWS
from .const import WINDOW_ORDER
from .const import WINDOW_PULSE_WEIGHTS
from .const import WINDOW_TO_DELTA

if TYPE_CHECKING:
    from collections.abc import Iterable
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class GitHubChatterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage data fetching for GitHub Chatter."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._token: str = entry.data[CONF_ACCESS_TOKEN]
        self._repository: str = entry.data[CONF_REPOSITORY]
        self._owner, self._repo = self._repository.split("/", 1)

        poll_interval = int(
            entry.options.get(
                OPTION_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS
            )
        )

        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"github_chatter_{self._repository}",
            update_interval=timedelta(seconds=poll_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and calculate activity metrics."""
        windows = self._active_windows
        now = dt_util.utcnow()
        oldest_delta = WINDOW_TO_DELTA[windows[-1]]
        oldest_cutoff = now - oldest_delta

        issues = await self._fetch_issues_since(oldest_cutoff)
        comments = await self._fetch_comments_since(oldest_cutoff)

        issue_counts = self._count_by_window(
            (issue["created_at"] for issue in issues), windows, now
        )
        comment_counts = self._count_by_window(
            (comment["created_at"] for comment in comments), windows, now
        )

        comment_issue_counts_by_window = self._comment_issue_counts_by_window(
            comments, windows, now
        )
        comment_hhi = {
            window: self._compute_hhi(comment_issue_counts_by_window[window].values())
            for window in windows
        }

        top_issue_numbers = {
            window: self._top_issue_number(comment_issue_counts_by_window[window])
            for window in windows
        }

        issue_details = await self._fetch_issue_details(
            {n for n in top_issue_numbers.values() if n is not None}
        )
        top_issues = {
            window: self._build_top_issue_payload(
                top_issue_numbers[window],
                comment_issue_counts_by_window[window],
                issue_details,
            )
            for window in windows
        }

        pulse_score = self._compute_pulse_score(
            issue_counts, comment_counts, comment_hhi, windows
        )

        return {
            "repository": self._repository,
            "windows": windows,
            "fetched_at": now.isoformat(),
            "issue_counts": issue_counts,
            "comment_counts": comment_counts,
            "comment_hhi": comment_hhi,
            "top_issues": top_issues,
            "pulse_score": pulse_score,
        }

    @property
    def _active_windows(self) -> list[str]:
        raw_windows = self.entry.options.get(OPTION_WINDOWS, DEFAULT_WINDOWS)
        windows = [window for window in WINDOW_ORDER if window in raw_windows]
        return windows or list(DEFAULT_WINDOWS)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _fetch_issues_since(self, since_dt: datetime) -> list[dict[str, Any]]:
        url = f"{API_BASE_URL}/repos/{self._owner}/{self._repo}/issues"
        params = {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "since": since_dt.isoformat().replace("+00:00", "Z"),
            "per_page": 100,
        }
        items = await self._fetch_paginated(url, params)
        return [item for item in items if "pull_request" not in item]

    async def _fetch_comments_since(self, since_dt: datetime) -> list[dict[str, Any]]:
        url = f"{API_BASE_URL}/repos/{self._owner}/{self._repo}/issues/comments"
        params = {
            "sort": "created",
            "direction": "desc",
            "since": since_dt.isoformat().replace("+00:00", "Z"),
            "per_page": 100,
        }
        return await self._fetch_paginated(url, params)

    async def _fetch_issue_details(
        self, issue_numbers: set[int]
    ) -> dict[int, dict[str, Any]]:
        details: dict[int, dict[str, Any]] = {}
        for issue_number in sorted(issue_numbers):
            url = (
                f"{API_BASE_URL}/repos/{self._owner}/{self._repo}/issues/{issue_number}"
            )
            item = await self._fetch_json(url)
            details[issue_number] = {
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
            }
        return details

    async def _fetch_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            async with (
                async_timeout.timeout(GITHUB_TIMEOUT_SECONDS),
                self._session.get(
                    url, headers=self._headers(), params=params
                ) as response,
            ):
                if response.status == 401:
                    raise UpdateFailed("GitHub authentication failed (401).")
                if response.status == 403:
                    raise UpdateFailed(
                        "GitHub API returned 403 (rate limit or access denied)."
                    )
                if response.status >= 400:
                    text = await response.text()
                    raise UpdateFailed(
                        f"GitHub API error {response.status}: {text[:200]}"
                    )
                return await response.json()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Error communicating with GitHub API: {err}") from err

    async def _fetch_paginated(
        self, url: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        current_url = url
        current_params: dict[str, Any] | None = params

        while current_url:
            try:
                async with (
                    async_timeout.timeout(GITHUB_TIMEOUT_SECONDS),
                    self._session.get(
                        current_url, headers=self._headers(), params=current_params
                    ) as response,
                ):
                    if response.status == 401:
                        raise UpdateFailed("GitHub authentication failed (401).")
                    if response.status == 403:
                        raise UpdateFailed(
                            "GitHub API returned 403 (rate limit or access denied)."
                        )
                    if response.status >= 400:
                        text = await response.text()
                        raise UpdateFailed(
                            f"GitHub API error {response.status}: {text[:200]}"
                        )

                    page_data = await response.json()
                    if isinstance(page_data, list):
                        items.extend(page_data)
                    else:
                        raise UpdateFailed(
                            "GitHub API returned unexpected payload for paginated endpoint."
                        )

                    next_link = response.links.get("next") if response.links else None
                    current_url = next_link["url"] if next_link else ""
                    current_params = None
            except (TimeoutError, aiohttp.ClientError) as err:
                raise UpdateFailed(
                    f"Error communicating with GitHub API: {err}"
                ) from err

        return items

    def _count_by_window(
        self, created_ats: Iterable[str], windows: list[str], now: datetime
    ) -> dict[str, int]:
        cutoffs = {window: now - WINDOW_TO_DELTA[window] for window in windows}
        counts = dict.fromkeys(windows, 0)

        for created_at in created_ats:
            created = dt_util.parse_datetime(created_at)
            if created is None:
                continue
            created_utc = created.astimezone(UTC)
            for window in windows:
                if created_utc >= cutoffs[window]:
                    counts[window] += 1

        return counts

    def _comment_issue_counts_by_window(
        self, comments: list[dict[str, Any]], windows: list[str], now: datetime
    ) -> dict[str, dict[int, int]]:
        cutoffs = {window: now - WINDOW_TO_DELTA[window] for window in windows}
        per_window_counts: dict[str, dict[int, int]] = {
            window: defaultdict(int) for window in windows
        }

        for comment in comments:
            created = dt_util.parse_datetime(comment.get("created_at"))
            issue_url = comment.get("issue_url")
            if created is None or not issue_url:
                continue
            issue_number = self._issue_number_from_url(issue_url)
            if issue_number is None:
                continue

            created_utc = created.astimezone(UTC)
            for window in windows:
                if created_utc >= cutoffs[window]:
                    per_window_counts[window][issue_number] += 1

        return per_window_counts

    @staticmethod
    def _issue_number_from_url(issue_url: str) -> int | None:
        try:
            return int(issue_url.rstrip("/").split("/")[-1])
        except TypeError, ValueError:
            return None

    @staticmethod
    def _compute_hhi(issue_comment_counts: Iterable[int]) -> float:
        counts = [count for count in issue_comment_counts if count > 0]
        total = sum(counts)
        if total <= 0:
            return 0.0
        return round(sum((count / total) ** 2 for count in counts), 6)

    @staticmethod
    def _top_issue_number(issue_counts: dict[int, int]) -> int | None:
        if not issue_counts:
            return None
        return sorted(issue_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]

    @staticmethod
    def _build_top_issue_payload(
        issue_number: int | None,
        window_issue_counts: dict[int, int],
        issue_details: dict[int, dict[str, Any]],
    ) -> dict[str, Any] | None:
        if issue_number is None:
            return None
        details = issue_details.get(issue_number)
        if details is None:
            return {
                "number": issue_number,
                "title": f"Issue #{issue_number}",
                "url": None,
                "comment_count": window_issue_counts[issue_number],
            }
        return {
            "number": details["number"],
            "title": details["title"],
            "url": details["url"],
            "comment_count": window_issue_counts[issue_number],
        }

    def _compute_pulse_score(
        self,
        issue_counts: dict[str, int],
        comment_counts: dict[str, int],
        hhi: dict[str, float],
        windows: list[str],
    ) -> float:
        if not self.entry.options.get(OPTION_ENABLE_PULSE, DEFAULT_ENABLE_PULSE):
            return 0.0

        issue_signal = self._window_weighted_signal(
            issue_counts, ISSUE_NORMALIZATION_SCALE, windows
        )
        comment_signal = self._window_weighted_signal(
            comment_counts, COMMENT_NORMALIZATION_SCALE, windows
        )
        concentration_signal = self._window_weighted_hhi(hhi, windows)

        issue_weight = float(
            self.entry.options.get(
                OPTION_PULSE_WEIGHT_ISSUES, DEFAULT_PULSE_WEIGHT_ISSUES
            )
        )
        comment_weight = float(
            self.entry.options.get(
                OPTION_PULSE_WEIGHT_COMMENTS, DEFAULT_PULSE_WEIGHT_COMMENTS
            )
        )
        concentration_weight = float(
            self.entry.options.get(
                OPTION_PULSE_WEIGHT_CONCENTRATION, DEFAULT_PULSE_WEIGHT_CONCENTRATION
            )
        )

        total_weight = issue_weight + comment_weight + concentration_weight
        if total_weight <= 0:
            return 0.0

        score = (
            (issue_signal * issue_weight)
            + (comment_signal * comment_weight)
            + (concentration_signal * concentration_weight)
        ) / total_weight

        return round(max(0.0, min(score, 1.0)) * 100.0, 2)

    @staticmethod
    def _window_weighted_signal(
        counts: dict[str, int], scales: dict[str, float], windows: list[str]
    ) -> float:
        weighted_sum = 0.0
        total_weight = 0.0

        for window in windows:
            window_weight = WINDOW_PULSE_WEIGHTS[window]
            scale = scales[window]
            normalized = min(float(counts.get(window, 0)) / scale, 1.0)
            weighted_sum += normalized * window_weight
            total_weight += window_weight

        if total_weight <= 0:
            return 0.0
        return weighted_sum / total_weight

    @staticmethod
    def _window_weighted_hhi(hhi: dict[str, float], windows: list[str]) -> float:
        weighted_sum = 0.0
        total_weight = 0.0

        for window in windows:
            window_weight = WINDOW_PULSE_WEIGHTS[window]
            weighted_sum += float(hhi.get(window, 0.0)) * window_weight
            total_weight += window_weight

        if total_weight <= 0:
            return 0.0
        return weighted_sum / total_weight
