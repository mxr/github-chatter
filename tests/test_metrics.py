"""Tests for GitHub Chatter metrics helpers."""

import pytest

from custom_components.github_chatter.coordinator import GitHubChatterCoordinator


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        pytest.param([], 0.0, id="no-comments"),
        pytest.param([10, 0, 0], 1.0, id="concentrated"),
        pytest.param([5, 5], 0.5, id="even-distribution"),
    ],
)
def test_hhi(counts: list[int], expected: float) -> None:
    assert GitHubChatterCoordinator._compute_hhi(counts) == expected
