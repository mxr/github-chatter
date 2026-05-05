"""Constants for GitHub Chatter."""

from datetime import timedelta
from logging import Logger
from logging import getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "github_chatter"
ATTRIBUTION = "Data provided by the GitHub API"
API_BASE_URL = "https://api.github.com"

CONF_ACCESS_TOKEN = "access_token"
CONF_REPOSITORY = "repository"

OPTION_POLL_INTERVAL_SECONDS = "poll_interval_seconds"
OPTION_WINDOWS = "windows"
OPTION_ENABLE_PULSE = "enable_pulse_score"
OPTION_PULSE_WEIGHT_ISSUES = "pulse_weight_issues"
OPTION_PULSE_WEIGHT_COMMENTS = "pulse_weight_comments"
OPTION_PULSE_WEIGHT_CONCENTRATION = "pulse_weight_concentration"

DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_WINDOWS = ["15m", "1h", "24h", "7d"]
DEFAULT_ENABLE_PULSE = True
DEFAULT_PULSE_WEIGHT_ISSUES = 0.45
DEFAULT_PULSE_WEIGHT_COMMENTS = 0.45
DEFAULT_PULSE_WEIGHT_CONCENTRATION = 0.10

WINDOW_TO_DELTA = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}
WINDOW_ORDER = ["15m", "1h", "24h", "7d"]

ISSUE_NORMALIZATION_SCALE = {
    "15m": 3.0,
    "1h": 8.0,
    "24h": 30.0,
    "7d": 100.0,
}
COMMENT_NORMALIZATION_SCALE = {
    "15m": 10.0,
    "1h": 30.0,
    "24h": 120.0,
    "7d": 500.0,
}
WINDOW_PULSE_WEIGHTS = {
    "15m": 0.50,
    "1h": 0.30,
    "24h": 0.15,
    "7d": 0.05,
}

PLATFORMS = ["sensor"]

GITHUB_TIMEOUT_SECONDS = 30
