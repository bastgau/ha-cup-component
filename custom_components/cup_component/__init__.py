"""The cup_component component."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    Platform,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import Api as ClientApi
from .const import CONF_UPDATE_INTERVAL, DOMAIN, MIN_TIME_BETWEEN_UPDATES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

type CupComponentConfigEntry = ConfigEntry[CupComponentData]


@dataclass
class CupComponentData:
    """Runtime data definition."""

    api: ClientApi
    coordinator: DataUpdateCoordinator[None]


async def async_setup_entry(hass: HomeAssistant, entry: CupComponentConfigEntry) -> bool:
    """Set up Cup Component entry."""

    name = entry.data[CONF_NAME]
    url = entry.data[CONF_URL]

    _LOGGER.debug("Setting up %s integration with host %s", DOMAIN, url)

    session = async_get_clientsession(hass, verify_ssl=False)
    api_client = ClientApi(
        session=session,
        url=url,
        logger=_LOGGER,
    )

    async def async_update_data() -> None:
        """Fetch data from API endpoint."""

        result: Any = await api_client.call_get_all_data()

        if not isinstance(result, dict):
            raise ConfigEntryAuthFailed

    conf_update_interval: int | None = entry.data.get(CONF_UPDATE_INTERVAL)

    if conf_update_interval is None:
        update_interval = MIN_TIME_BETWEEN_UPDATES
    else:
        update_interval = timedelta(seconds=conf_update_interval)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=name,
        update_method=async_update_data,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = CupComponentData(api_client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Cup Component entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
