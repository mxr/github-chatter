"""Tests for GitHub Chatter metrics helpers."""

from __future__ import annotations

from custom_components.github_chatter.coordinator import GitHubChatterCoordinator


def test_hhi_zero_for_no_comments() -> None:
    assert GitHubChatterCoordinator._compute_hhi([]) == 0.0


def test_hhi_for_concentrated_comments() -> None:
    assert GitHubChatterCoordinator._compute_hhi([10, 0, 0]) == 1.0


def test_hhi_for_even_distribution() -> None:
    assert GitHubChatterCoordinator._compute_hhi([5, 5]) == 0.5
