"""Sensor platform for GitHub Chatter."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .const import CONF_REPOSITORY
from .const import DOMAIN
from .const import OPTION_ENABLE_PULSE
from .coordinator import GitHubChatterCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType


@dataclass(frozen=True, kw_only=True)
class GitHubChatterSensorDescription(SensorEntityDescription):
    """Describe GitHub Chatter sensor."""

    value_fn: Callable[[dict[str, Any], str | None], StateType]
    attr_fn: Callable[[dict[str, Any], str | None], Mapping[str, Any] | None] = (
        lambda _data, _window: None
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up GitHub Chatter sensors from config entry."""
    coordinator = entry.runtime_data
    windows: list[str] = coordinator.data.get("windows", [])

    entities: list[GitHubChatterSensor] = []

    for window in windows:
        entities.extend(
            [
                GitHubChatterSensor(coordinator, ISSUE_COUNT_DESCRIPTION, window),
                GitHubChatterSensor(coordinator, COMMENT_COUNT_DESCRIPTION, window),
                GitHubChatterSensor(coordinator, COMMENT_HHI_DESCRIPTION, window),
                GitHubChatterSensor(coordinator, TOP_ISSUE_DESCRIPTION, window),
            ]
        )

    if entry.options.get(OPTION_ENABLE_PULSE, True):
        entities.append(GitHubChatterSensor(coordinator, PULSE_DESCRIPTION, None))

    async_add_entities(entities)


ISSUE_COUNT_DESCRIPTION = GitHubChatterSensorDescription(
    key="issue_creation_count",
    translation_key="issue_creation_count",
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data, window: data["issue_counts"].get(window, 0),
)

COMMENT_COUNT_DESCRIPTION = GitHubChatterSensorDescription(
    key="issue_comment_count",
    translation_key="issue_comment_count",
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data, window: data["comment_counts"].get(window, 0),
)

COMMENT_HHI_DESCRIPTION = GitHubChatterSensorDescription(
    key="comment_hhi",
    translation_key="comment_hhi",
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=lambda data, window: data["comment_hhi"].get(window, 0.0),
)

TOP_ISSUE_DESCRIPTION = GitHubChatterSensorDescription(
    key="top_commented_issue",
    translation_key="top_commented_issue",
    value_fn=lambda data, window: (data["top_issues"].get(window) or {}).get("title"),
    attr_fn=lambda data, window: data["top_issues"].get(window),
)

PULSE_DESCRIPTION = GitHubChatterSensorDescription(
    key="pulse_score",
    translation_key="pulse_score",
    native_unit_of_measurement="points",
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data, _window: data.get("pulse_score", 0.0),
)


class GitHubChatterSensor(CoordinatorEntity[GitHubChatterCoordinator], SensorEntity):
    """GitHub Chatter sensor entity."""

    entity_description: GitHubChatterSensorDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: GitHubChatterCoordinator,
        description: GitHubChatterSensorDescription,
        window: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._window = window

        repository = coordinator.entry.data[CONF_REPOSITORY]
        repo_slug = repository.replace("/", "_")
        window_suffix = f"_{window}" if window else ""

        self._attr_unique_id = f"{repo_slug}_{description.key}{window_suffix}"
        self._attr_translation_placeholders = {"window": window or "global"}

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, repository)},
            name=f"GitHub Chatter {repository}",
            manufacturer="GitHub",
            configuration_url=f"https://github.com/{repository}",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> StateType:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data, self._window)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return state attributes."""
        attributes = self.entity_description.attr_fn(
            self.coordinator.data, self._window
        )
        if attributes is None:
            return None
        base_attrs = {"window": self._window}
        base_attrs.update(attributes)
        return base_attrs
