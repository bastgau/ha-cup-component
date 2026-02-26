"""The cup_component component."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    Platform,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import CupApi
from .const import CONF_EXCLUDE_PATTERNS, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.BUTTON]

type CupComponentConfigEntry = ConfigEntry[CupComponentData]


@dataclass
class CupComponentData:
    """Runtime data definition."""

    api: CupApi
    coordinator: DataUpdateCoordinator[None]


async def async_setup_entry(hass: HomeAssistant, entry: CupComponentConfigEntry) -> bool:
    """Set up Cup Component entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry for this integration.

    Returns:
        bool: True if the setup was successful.

    """

    name = str(entry.data[CONF_NAME])
    url = str(entry.data[CONF_URL])

    _LOGGER.debug("Setting up %s integration with host %s", DOMAIN, url)

    session = async_get_clientsession(hass, verify_ssl=False)
    exclude_patterns: list[str] = entry.data.get(CONF_EXCLUDE_PATTERNS, [])

    api_client = CupApi(
        session=session,
        url=url,
        logger=_LOGGER,
        exclude_patterns=exclude_patterns,
    )

    async def async_update_data() -> None:
        """Fetch data from API endpoint.

        Returns:
            None.

        """

        await api_client.call_get_all_data()

    conf_update_interval: int | None = entry.data.get(CONF_UPDATE_INTERVAL)

    if conf_update_interval is None:
        update_interval = DEFAULT_UPDATE_INTERVAL
    else:
        update_interval = timedelta(seconds=conf_update_interval)

    coordinator: DataUpdateCoordinator[None] = DataUpdateCoordinator(
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
    """Unload Cup Component entry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The config entry to unload.

    Returns:
        bool: True if the unload was successful.

    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
