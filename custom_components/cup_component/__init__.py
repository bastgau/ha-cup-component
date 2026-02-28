"""The cup_component component."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import CoreState, Event
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import CupApi
from .const import CONF_EXCLUDE_PATTERNS, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .frontend import JSModuleRegistration

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

# This integration is configured exclusively via config entries (no YAML configuration).
CONFIG_SCHEMA: Final[Any] = cv.config_entry_only_config_schema(DOMAIN)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.BUTTON]

type CupComponentConfigEntry = ConfigEntry[CupComponentData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # pyright: ignore[reportUnknownParameterType, reportMissingTypeArgument] # pylint: disable=unused-argument  # noqa: ARG001
    """Register the static HTTP path and the Lovelace card resource.

    This function is called once when the integration is loaded, before any
    config entry setup. Registration is deferred until HA is fully started
    to ensure hass.data[LOVELACE_DATA] is available.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        config (ConfigType): The full HA configuration (unused).

    Returns:
        bool: Always True.

    """

    async def _register_frontend(_event: Event | None = None) -> None:
        """Register frontend resources once HA is running.

        Returns:
            None.

        """
        registrar = JSModuleRegistration(hass)
        await registrar.async_register()

    if hass.state == CoreState.running:
        # HA is already running (e.g. integration reloaded at runtime): register immediately
        # without waiting for EVENT_HOMEASSISTANT_STARTED, which will never fire again.
        await _register_frontend()
    else:
        # Defer until HA has fully started to ensure hass.data[LOVELACE_DATA] is available.
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    return True


@dataclass
class CupComponentData:
    """Holds runtime data for the cup_component integration.

    Attributes:
        api (CupApi): The API client used to fetch data from the Cup server.
        coordinator (DataUpdateCoordinator[None]): The update coordinator managing polling.

    """

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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:  # noqa: ARG001 # pylint: disable=unused-argument
    """Remove Cup Component entry and clean up Lovelace resources.

    Called when the integration is permanently removed by the user.
    Unregisters the Lovelace card resource from storage.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The config entry being removed (unused).

    Returns:
        None.

    """
    registrar = JSModuleRegistration(hass)
    await registrar.async_unregister()
    # Note: the static HTTP path (URL_BASE) cannot be deregistered at runtime —
    # HA provides no public API for this. It remains active until the next HA restart.
