"""Typed data models for GitHub Chatter."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopIssue:
    """Top commented issue for a window."""

    number: int
    title: str
    url: str | None
    comment_count: int


@dataclass(frozen=True, slots=True)
class GitHubChatterData:
    """Activity metrics produced by the coordinator."""

    repository: str
    windows: list[str]
    fetched_at: str
    issue_counts: dict[str, int]
    comment_counts: dict[str, int]
    comment_hhi: dict[str, float]
    top_issues: dict[str, TopIssue | None]
    pulse_score: float
