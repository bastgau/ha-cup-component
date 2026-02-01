"""Support for getting statistical data from a Cup server."""

from __future__ import annotations

import json
from typing import Any, List

from homeassistant.components.sensor import (
    EntityCategory,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import CupComponentConfigEntry
from .api import API as ClientAPI
from .entity import CupComponentEntity
from .helper import create_entity_id_name

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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Cup Component sensor."""
    name = entry.data[CONF_NAME]
    cup_data = entry.runtime_data
    sensors = [
        CupComponentSensor(
            cup_data.api,
            cup_data.coordinator,
            name,
            entry.entry_id,
            description,
        )
        for description in SENSOR_TYPES
    ]
    async_add_entities(sensors, True)


class CupComponentSensor(CupComponentEntity, SensorEntity):
    """Representation of a Cup Component sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        api: ClientAPI,
        coordinator: DataUpdateCoordinator[None],
        name: str,
        server_unique_id: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a Cup Component sensor."""
        super().__init__(api, coordinator, name, server_unique_id)
        self.entity_description = description
        self._attr_unique_id = f"{self._server_unique_id}/{description.key}"

        raw_name: str = f"sensor.{name}_{description.key}"
        self.entity_id = create_entity_id_name(raw_name)

    @property
    def native_value(self) -> StateType:
        """Return the state of the device."""

        possible_keys: List[str] = [
            "major_updates",
            "minor_updates",
            "monitored_images",
            "other_updates",
            "patch_updates",
            "unknown",
            "up_to_date",
            "updates_available",
        ]

        entity_description_key: str = self.entity_description.key

        if self.entity_description.key in possible_keys:
            return self.api.cache_metrics[entity_description_key]

        if self.entity_description.key == "last_checked":
            return self.api.cache_last_checked

        return ""

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        # Set the last start time attribute
        if isinstance(self.coordinator, DataUpdateCoordinator):
            if self.entity_description.key in self.api.cache_images:
                return {
                    "images_list": json.dumps(
                        self.api.cache_images[self.entity_description.key]
                    )
                }

        return None
