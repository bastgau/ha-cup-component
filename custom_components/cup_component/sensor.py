"""Support for getting statistical data from a Cup server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, EntityCategory

from .entity import CupComponentEntity
from .helper import create_entity_id_name

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from . import CupComponentConfigEntry, CupComponentData
    from .api import CupApi

# Keys corresponding to numeric metrics stored in cache_metrics
_METRIC_SENSOR_KEYS: tuple[str, ...] = (
    "major_updates",
    "minor_updates",
    "monitored_images",
    "other_updates",
    "patch_updates",
    "unknown",
    "up_to_date",
    "updates_available",
    "excluded_images",
)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="major_updates",
        translation_key="major_updates",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="minor_updates",
        translation_key="minor_updates",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="monitored_images",
        translation_key="monitored_images",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="other_updates",
        translation_key="other_updates",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="patch_updates",
        translation_key="patch_updates",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="unknown",
        translation_key="unknown",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="up_to_date",
        translation_key="up_to_date",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="updates_available",
        translation_key="updates_available",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="last_checked",
        translation_key="last_checked",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="excluded_images",
        translation_key="excluded_images",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 # pylint: disable=unused-argument
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Cup Component sensor entities from a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry for this integration.
        async_add_entities (AddConfigEntryEntitiesCallback): Callback to register new entities.

    Returns:
        None.

    """
    name = entry.data[CONF_NAME]
    cup_data = entry.runtime_data
    sensors = [
        CupComponentSensor(
            cup_data,
            name,
            entry.entry_id,
            description,
        )
        for description in SENSOR_TYPES
    ]
    async_add_entities(sensors, update_before_add=True)


class CupComponentSensor(CupComponentEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Cup Component sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        cup_component: CupComponentData,
        name: str,
        server_unique_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a Cup Component sensor.

        Args:
            cup_component (CupComponentData): Runtime data containing the API client and coordinator.
            name (str): The human-readable name of the Cup server.
            server_unique_id (str): The unique identifier of the config entry.
            description (SensorEntityDescription): The entity description for this sensor.

        """

        api: CupApi = cup_component.api
        coordinator: DataUpdateCoordinator[None] = cup_component.coordinator

        super().__init__(api, coordinator, name, server_unique_id)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]
        self._attr_unique_id = f"{self._server_unique_id}/{description.key}"

        raw_name: str = f"sensor.{name}_{description.key}"
        self.entity_id = create_entity_id_name(raw_name)

    @property
    def native_value(self) -> StateType | datetime | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state of the device.

        Returns:
            StateType | datetime | None: The current value of the sensor.

        """

        if self.entity_description.key in _METRIC_SENSOR_KEYS:
            return self.api.cache_metrics.get(self.entity_description.key)

        if self.entity_description.key == "last_checked":
            return self.api.cache_last_checked

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state attributes.

        Returns:
            dict[str, Any] | None: A dictionary of extra attributes, or None if not applicable.

        """
        if self.entity_description.key in self.api.cache_images:
            return {"images_list": self.api.cache_images[self.entity_description.key]}

        if self.entity_description.key == "monitored_images":
            # Compute the full list of monitored images on the fly (all buckets except excluded)
            all_images = [
                image
                for key, images in self.api.cache_images.items()
                if key != "excluded_images"
                for image in images
            ]
            return {"images_list": all_images}

        if self.entity_description.key == "updates_available":
            # Compute the full list of images with pending updates on the fly
            update_buckets = {"major_updates", "minor_updates", "patch_updates", "other_updates"}
            all_updates = [
                image
                for key, images in self.api.cache_images.items()
                if key in update_buckets
                for image in images
            ]
            return {"images_list": all_updates}

        return None
