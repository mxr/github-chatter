"""Config flow for GitHub Chatter."""

import asyncio
import re
from typing import TYPE_CHECKING
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL
from .const import CONF_ACCESS_TOKEN
from .const import CONF_REPOSITORY
from .const import DEFAULT_ENABLE_PULSE
from .const import DEFAULT_POLL_INTERVAL_SECONDS
from .const import DEFAULT_PULSE_WEIGHT_COMMENTS
from .const import DEFAULT_PULSE_WEIGHT_CONCENTRATION
from .const import DEFAULT_PULSE_WEIGHT_ISSUES
from .const import DEFAULT_WINDOWS
from .const import DOMAIN
from .const import GITHUB_TIMEOUT_SECONDS
from .const import OPTION_ENABLE_PULSE
from .const import OPTION_POLL_INTERVAL_SECONDS
from .const import OPTION_PULSE_WEIGHT_COMMENTS
from .const import OPTION_PULSE_WEIGHT_CONCENTRATION
from .const import OPTION_PULSE_WEIGHT_ISSUES
from .const import OPTION_WINDOWS
from .const import WINDOW_ORDER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


async def _validate_credentials(
    hass: HomeAssistant, repository: str, token: str
) -> str | None:
    owner, repo = repository.split("/", 1)
    url = f"{API_BASE_URL}/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    session = async_get_clientsession(hass)
    try:
        async with (
            asyncio.timeout(GITHUB_TIMEOUT_SECONDS),
            session.get(url, headers=headers) as response,
        ):
            if response.status == 401:
                return "invalid_auth"
            if response.status == 404:
                return "repo_not_found"
            if response.status >= 400:
                return "unknown"
    except TimeoutError, aiohttp.ClientError:
        return "cannot_connect"

    return None


class GitHubChatterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GitHub Chatter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            repository = user_input[CONF_REPOSITORY].strip()
            token = user_input[CONF_ACCESS_TOKEN].strip()

            if not REPO_PATTERN.match(repository):
                errors[CONF_REPOSITORY] = "invalid_repository"
            else:
                unique_id = repository.casefold()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                validation_error = await _validate_credentials(
                    self.hass, repository, token
                )
                if validation_error is None:
                    return self.async_create_entry(
                        title=repository,
                        data={
                            CONF_REPOSITORY: repository,
                            CONF_ACCESS_TOKEN: token,
                        },
                        options={
                            OPTION_POLL_INTERVAL_SECONDS: DEFAULT_POLL_INTERVAL_SECONDS,
                            OPTION_WINDOWS: DEFAULT_WINDOWS,
                            OPTION_ENABLE_PULSE: DEFAULT_ENABLE_PULSE,
                            OPTION_PULSE_WEIGHT_ISSUES: DEFAULT_PULSE_WEIGHT_ISSUES,
                            OPTION_PULSE_WEIGHT_COMMENTS: DEFAULT_PULSE_WEIGHT_COMMENTS,
                            OPTION_PULSE_WEIGHT_CONCENTRATION: DEFAULT_PULSE_WEIGHT_CONCENTRATION,
                        },
                    )

                errors["base"] = validation_error

        data_schema = vol.Schema(
            {
                vol.Required(CONF_REPOSITORY): str,
                vol.Required(CONF_ACCESS_TOKEN): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: ConfigEntry) -> GitHubChatterOptionsFlow:
        """Get options flow handler."""
        return GitHubChatterOptionsFlow()


class GitHubChatterOptionsFlow(OptionsFlowWithReload):
    """Handle options for GitHub Chatter."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            windows = [window for window in WINDOW_ORDER if user_input.get(window)]
            if not windows:
                windows = list(DEFAULT_WINDOWS)

            return self.async_create_entry(
                title="",
                data={
                    OPTION_POLL_INTERVAL_SECONDS: user_input[
                        OPTION_POLL_INTERVAL_SECONDS
                    ],
                    OPTION_WINDOWS: windows,
                    OPTION_ENABLE_PULSE: user_input[OPTION_ENABLE_PULSE],
                    OPTION_PULSE_WEIGHT_ISSUES: user_input[OPTION_PULSE_WEIGHT_ISSUES],
                    OPTION_PULSE_WEIGHT_COMMENTS: user_input[
                        OPTION_PULSE_WEIGHT_COMMENTS
                    ],
                    OPTION_PULSE_WEIGHT_CONCENTRATION: user_input[
                        OPTION_PULSE_WEIGHT_CONCENTRATION
                    ],
                },
            )

        configured_windows = self.config_entry.options.get(
            OPTION_WINDOWS, DEFAULT_WINDOWS
        )

        schema = vol.Schema(
            {
                vol.Required(
                    OPTION_POLL_INTERVAL_SECONDS,
                    default=self.config_entry.options.get(
                        OPTION_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                vol.Required(
                    OPTION_ENABLE_PULSE,
                    default=self.config_entry.options.get(
                        OPTION_ENABLE_PULSE, DEFAULT_ENABLE_PULSE
                    ),
                ): bool,
                vol.Required(
                    OPTION_PULSE_WEIGHT_ISSUES,
                    default=self.config_entry.options.get(
                        OPTION_PULSE_WEIGHT_ISSUES, DEFAULT_PULSE_WEIGHT_ISSUES
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    OPTION_PULSE_WEIGHT_COMMENTS,
                    default=self.config_entry.options.get(
                        OPTION_PULSE_WEIGHT_COMMENTS, DEFAULT_PULSE_WEIGHT_COMMENTS
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required(
                    OPTION_PULSE_WEIGHT_CONCENTRATION,
                    default=self.config_entry.options.get(
                        OPTION_PULSE_WEIGHT_CONCENTRATION,
                        DEFAULT_PULSE_WEIGHT_CONCENTRATION,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
                vol.Required("15m", default="15m" in configured_windows): bool,
                vol.Required("1h", default="1h" in configured_windows): bool,
                vol.Required("24h", default="24h" in configured_windows): bool,
                vol.Required("7d", default="7d" in configured_windows): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
