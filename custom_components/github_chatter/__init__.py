"""The GitHub Chatter integration."""

from typing import TYPE_CHECKING
from typing import Any

from homeassistant.const import Platform

from .coordinator import GitHubChatterCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GitHub Chatter from a config entry."""
    coordinator = GitHubChatterCoordinator(hass=hass, entry=entry)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Sensors restore their last known value via RestoreSensor, so the first
    # refresh doesn't need to block entry setup; it runs in the background
    # and entities pick it up once it completes.
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), "github_chatter_first_refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry[Any]) -> bool:
    """Migrate old entry versions."""
    return True
