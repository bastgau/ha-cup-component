"""JavaScript module registration for the cup_component Lovelace card."""

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import LOVELACE_CARD_JS, URL_BASE

_LOGGER = logging.getLogger(__name__)

# JS modules to register as Lovelace resources.
_JS_MODULES = [
    {"name": "Cup Images Card", "filename": LOVELACE_CARD_JS},
]


class JSModuleRegistration:
    """Registers the cup_component JS card as a Lovelace resource."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the registrar."""
        self.hass = hass

    @property
    def _lovelace(self) -> Any:
        """Return the LovelaceData object from hass.data."""
        return self.hass.data.get(LOVELACE_DATA)

    async def async_register(self) -> None:
        """Register the static HTTP path and the Lovelace resource."""
        await self._async_register_path()
        lovelace = self._lovelace
        # Resource auto-registration only works in Lovelace storage mode.
        if lovelace and lovelace.resource_mode == MODE_STORAGE:
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Register the static HTTP path serving the www/ directory."""
        www_dir = Path(__file__).parent.parent / "www"
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(www_dir), cache_headers=False)]
            )
            _LOGGER.debug("Registered static path %s -> %s", URL_BASE, www_dir)
        except RuntimeError:
            # Path already registered (e.g. after a reload).
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait until Lovelace resources are loaded before registering modules."""

        async def _check_loaded(_now: Any) -> None:
            lovelace = self._lovelace
            if lovelace and lovelace.resources.loaded:
                await self._async_register_modules()
            else:
                _LOGGER.debug("Lovelace resources not yet loaded, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(None)

    async def _async_register_modules(self) -> None:
        """Add JS module entries in Lovelace resources if not already present."""
        _LOGGER.debug("Registering Lovelace JS modules")
        lovelace = self._lovelace
        if not lovelace:
            return

        existing = [
            r for r in lovelace.resources.async_items()
            if r["url"].startswith(URL_BASE)
        ]

        for module in _JS_MODULES:
            url = f"{URL_BASE}/{module['filename']}"
            already_registered = any(
                r["url"].split("?")[0] == url for r in existing
            )
            if not already_registered:
                _LOGGER.info("Registering Lovelace resource: %s", url)
                await lovelace.resources.async_create_item(
                    {"res_type": "module", "url": url}
                )

    async def async_unregister(self) -> None:
        """Remove cup_component resources from Lovelace."""
        lovelace = self._lovelace
        if not lovelace or lovelace.resource_mode != MODE_STORAGE:
            return
        for module in _JS_MODULES:
            url = f"{URL_BASE}/{module['filename']}"
            for resource in list(lovelace.resources.async_items()):
                if resource["url"].split("?")[0] == url:
                    await lovelace.resources.async_delete_item(resource["id"])
