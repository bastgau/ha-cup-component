"""Support for Cup Component button entities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import CupComponentConfigEntry
from .api import API as CupAPI
from .entity import CupComponentEntity
from .exceptions import ActionExecutionException
from .helper import create_entity_id_name

PARALLEL_UPDATES = 1
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class CupComponentButtonEntityDescription(ButtonEntityDescription):
    """Class describing Cup Component button entities."""


BUTTON_TYPES: tuple[CupComponentButtonEntityDescription, ...] = (
    CupComponentButtonEntityDescription(
        key="action_refresh",
        translation_key="action_refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    name = entry.data[CONF_NAME]
    cup_data = entry.runtime_data

    entities: list[CupComponentButton] = []

    for description in BUTTON_TYPES:
        entities.append(
            CupComponentButton(
                cup_data.api,
                cup_data.coordinator,
                name,
                entry.entry_id,
                description,
            )
        )

    async_add_entities(entities)


class CupComponentButton(CupComponentEntity, ButtonEntity):
    """Representation of a Cup Component button."""

    entity_description: CupComponentButtonEntityDescription

    def __init__(
        self,
        api: CupAPI,
        coordinator: DataUpdateCoordinator,
        name: str,
        server_unique_id: str,
        description: CupComponentButtonEntityDescription,
    ) -> None:
        """Initialize Cup Component button."""
        super().__init__(api, coordinator, name, server_unique_id)
        self.entity_description = description
        self._attr_unique_id = f"{self._server_unique_id}/{description.key}"

        raw_name: str = f"button.{name}_{description.key}"
        self.entity_id = create_entity_id_name(raw_name)

        self._is_enabled = True  # Initial state is enabled

    async def async_press(self) -> None:
        """Press the button."""

        action: str = self.entity_description.key

        try:
            result: dict[str, Any] = {"code": 200}

            match action:
                case "action_refresh":
                    result = await self.api.refresh()
                    await self.api.call_get_all_data()

            if result["code"] != 200:
                raise ActionExecutionException()

            _LOGGER.info(
                f"Action '{action}' just executed correctly for '{self._name}'."
            )

        except ActionExecutionException:
            _LOGGER.error(f"Unable to launch '{action}' action : %s", result["data"])

        self.coordinator.async_update_listeners()

    @property
    def is_enabled(self):
        """Return whether the button is enabled."""
        return self._is_enabled
