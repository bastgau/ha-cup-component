"""The cup component."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import API as CupAPI
from .const import DOMAIN


class CupComponentEntity(CoordinatorEntity[DataUpdateCoordinator[None]]):
    """Representation of a Cup Component entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        api: CupAPI,
        coordinator: DataUpdateCoordinator[None],
        name: str,
        server_unique_id: str,
    ) -> None:
        """Initialize a Cup Component entity."""
        super().__init__(coordinator)
        self.api = api
        self._name = name
        self._server_unique_id = server_unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information of the entity."""

        config_url = self.api.url.split("/api/v3/json")[0]

        return DeviceInfo(
            identifiers={(DOMAIN, self._server_unique_id)},
            name=self._name,
            configuration_url=config_url,
            model="Cup",
        )
