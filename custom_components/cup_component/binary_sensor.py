"""Support for Cup Component binary sensor entities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import CONF_NAME

from .entity import CupComponentEntity
from .helper import create_entity_id_name

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from . import CupComponentConfigEntry, CupComponentData
    from .api import CupApi

PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class CupComponentBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Cup Component binary sensor entities."""


BINARY_SENSOR_TYPES: tuple[CupComponentBinarySensorEntityDescription, ...] = (
    CupComponentBinarySensorEntityDescription(
        key="updates_available",
        translation_key="updates_available",
        device_class=BinarySensorDeviceClass.UPDATE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 # pylint: disable=unused-argument
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Cup Component binary sensor entities from a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry for this integration.
        async_add_entities (AddConfigEntryEntitiesCallback): Callback to register new entities.

    Returns:
        None.

    """
    name = entry.data[CONF_NAME]
    cup_data = entry.runtime_data

    entities: list[CupComponentBinarySensor] = [
        CupComponentBinarySensor(
            cup_data,
            name,
            entry.entry_id,
            description,
        )
        for description in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities, update_before_add=False)


class CupComponentBinarySensor(CupComponentEntity, BinarySensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Cup Component binary sensor."""

    entity_description: CupComponentBinarySensorEntityDescription

    def __init__(
        self,
        cup_data: CupComponentData,
        name: str,
        server_unique_id: str,
        description: CupComponentBinarySensorEntityDescription,
    ) -> None:
        """Initialize a Cup Component binary sensor.

        Args:
            cup_data (CupComponentData): Runtime data containing the API client and coordinator.
            name (str): The human-readable name of the Cup server.
            server_unique_id (str): The unique identifier of the config entry.
            description (CupComponentBinarySensorEntityDescription): The entity description for this binary sensor.

        """
        api: CupApi = cup_data.api
        coordinator: DataUpdateCoordinator[None] = cup_data.coordinator

        super().__init__(api, coordinator, name, server_unique_id)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]
        self._attr_unique_id = f"{self._server_unique_id}/{description.key}"

        raw_name: str = f"binary_sensor.{name}_{description.key}"
        self.entity_id = create_entity_id_name(raw_name)

    @property
    def is_on(self) -> bool | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return true if at least one update is available.

        Returns:
            bool | None: True if updates are available, False otherwise, or None if data is unavailable.

        """
        value = self.api.cache_metrics.get("updates_available")

        if value is None:
            return None

        return value > 0
