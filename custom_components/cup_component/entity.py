"""The cup component."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

from propcache.api import cached_property

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from .api import Api as ClientApi


class CupComponentEntity(CoordinatorEntity[DataUpdateCoordinator[None]]):
    """Representation of a Cup Component entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        api: ClientApi,
        coordinator: DataUpdateCoordinator[None],
        name: str,
        server_unique_id: str,
    ) -> None:
        """Initialize a Cup Component entity."""
        super().__init__(coordinator)
        self.api = api
        self._name = name
        self._server_unique_id = server_unique_id

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the device information of the entity."""

        # Build the base URL (scheme + netloc only) from the API URL
        parsed = urlparse(self.api.url)
        config_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

        return DeviceInfo(
            identifiers={(DOMAIN, self._server_unique_id)},
            name=self._name,
            configuration_url=config_url,
            model="Cup",
        )
