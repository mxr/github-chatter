"""Diagnostics support for GitHub Chatter."""

from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_ACCESS_TOKEN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_ACCESS_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception)
        if coordinator.last_exception
        else None,
        "data": coordinator.data,
    }
