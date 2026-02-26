"""Support for Cup Component button entities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import CONF_NAME

from .entity import CupComponentEntity
from .exceptions import ActionExecutionError
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
class CupComponentButtonEntityDescription(ButtonEntityDescription):
    """Class describing Cup Component button entities."""


BUTTON_TYPES: tuple[CupComponentButtonEntityDescription, ...] = (
    CupComponentButtonEntityDescription(
        key="action_refresh",
        translation_key="action_refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 # pylint: disable=unused-argument
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Cup Component button entities from a config entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry for this integration.
        async_add_entities (AddConfigEntryEntitiesCallback): Callback to register new entities.

    Returns:
        None.

    """
    name = entry.data[CONF_NAME]
    cup_data = entry.runtime_data

    entities: list[CupComponentButton] = [
        CupComponentButton(
            cup_data,
            name,
            entry.entry_id,
            description,
        )
        for description in BUTTON_TYPES
    ]

    async_add_entities(entities)


class CupComponentButton(CupComponentEntity, ButtonEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Cup Component button."""

    entity_description: CupComponentButtonEntityDescription

    def __init__(
        self,
        cup_data: CupComponentData,
        name: str,
        server_unique_id: str,
        description: CupComponentButtonEntityDescription,
    ) -> None:
        """Initialize Cup Component button.

        Args:
            cup_data (CupComponentData): Runtime data containing the API client and coordinator.
            name (str): The human-readable name of the Cup server.
            server_unique_id (str): The unique identifier of the config entry.
            description (CupComponentButtonEntityDescription): The entity description for this button.

        """

        api: CupApi = cup_data.api
        coordinator: DataUpdateCoordinator[None] = cup_data.coordinator

        super().__init__(api, coordinator, name, server_unique_id)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]
        self._attr_unique_id = f"{self._server_unique_id}/{description.key}"

        raw_name: str = f"button.{name}_{description.key}"
        self.entity_id = create_entity_id_name(raw_name)

    async def async_press(self) -> None:
        """Press the button.

        Returns:
            None.

        Raises:
            ActionExecutionError: If the action is unknown or if the API returns a non-200 status code.

        """

        action: str = self.entity_description.key
        result: dict[str, Any] = {"code": 200, "data": None}

        try:
            match action:
                case "action_refresh":
                    result = await self.api.refresh()
                    await self.api.call_get_all_data()
                case _:
                    raise ActionExecutionError  # noqa: TRY301

            if result["code"] != 200:
                raise ActionExecutionError  # noqa: TRY301

            _LOGGER.info("Action '%s' just executed correctly for '%s'.", action, self._name)

        except ActionExecutionError:
            _LOGGER.exception("Unable to launch '%s' action: %s", action, result.get("data", {}))  # ai: ignore
        else:
            self.coordinator.async_update_listeners()
