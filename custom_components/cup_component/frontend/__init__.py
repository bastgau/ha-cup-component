"""JavaScript module registration for the cup_component Lovelace card."""

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import INTEGRATION_VERSION, LOVELACE_CARD_NAME, LOVELACE_MODULE_URL, URL_BASE

_LOGGER = logging.getLogger(__name__)


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
        """Register the static HTTP path and the Lovelace resources.

        Lovelace resource registration is skipped silently when HA is configured
        in YAML mode (resource_mode != MODE_STORAGE): resources must be declared
        manually in the YAML configuration in that case.

        Returns:
            None.

        """
        await self._async_register_path()
        lovelace = self._lovelace
        # Resource registration only works in Lovelace storage mode.
        # In YAML mode, the user must declare the resource manually.
        if lovelace and lovelace.resource_mode == MODE_STORAGE:
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Register the static HTTP path serving the www/ directory.

        The path is registered once per HA session. On subsequent calls (e.g.
        after an integration reload), the RuntimeError is caught and silently
        ignored — the existing registration remains valid.

        Returns:
            None.

        """
        www_dir = Path(__file__).parent.parent / "www"
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(www_dir), cache_headers=False)]
            )
            _LOGGER.debug("Registered static path %s -> %s", URL_BASE, www_dir)
        except RuntimeError:
            # Path already registered (e.g. after a reload) — safe to ignore.
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait until Lovelace resources are loaded before registering modules.

        Polls every 5 seconds indefinitely until resources are available.
        There is no retry limit: if Lovelace never loads, this will run forever.

        Returns:
            None.

        """

        async def _check_loaded(_now: Any) -> None:
            """Check if Lovelace resources are loaded and register modules or reschedule.

            Returns:
                None.

            """
            lovelace = self._lovelace
            if lovelace and lovelace.resources.loaded:
                await self._async_register_modules()
            else:
                _LOGGER.debug("Lovelace resources not yet loaded, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(None)

    async def _async_register_modules(self) -> None:
        """Add or update the JS module entry in Lovelace resources.

        This method is idempotent: if the module is already registered at the
        correct version, no changes are made.

        Returns:
            None.

        """
        _LOGGER.debug("Registering Lovelace JS module: %s", LOVELACE_CARD_NAME)
        lovelace = self._lovelace
        if not lovelace:
            return

        # Version is read from manifest.json at module load time.
        # If the version changes between HA restarts, the resource URL is updated automatically.
        # In dev environments, INTEGRATION_VERSION falls back to a Unix timestamp (see const.py),
        # which guarantees the resource is always refreshed.
        versioned_url: str = f"{LOVELACE_MODULE_URL}?v={INTEGRATION_VERSION}"

        for resource in lovelace.resources.async_items():
            if resource["url"].split("?")[0] == LOVELACE_MODULE_URL:
                # Module already registered — update URL if version has changed.
                if self._get_version(resource["url"]) != INTEGRATION_VERSION:
                    _LOGGER.info("Updating %s to version %s", LOVELACE_CARD_NAME, INTEGRATION_VERSION)
                    await lovelace.resources.async_update_item(
                        resource["id"],
                        {"res_type": "module", "url": versioned_url},
                    )
                return

        _LOGGER.info("Registering Lovelace resource: %s v%s", LOVELACE_MODULE_URL, INTEGRATION_VERSION)
        await lovelace.resources.async_create_item({"res_type": "module", "url": versioned_url})

    @staticmethod
    def _get_version(url: str) -> str:
        """Extract version from a versioned URL (e.g. /path/file.js?v=1.0.0)."""
        parts = url.split("?")
        if len(parts) > 1 and parts[1].startswith("v="):
            return parts[1].replace("v=", "")
        return "0"

    async def async_unregister(self) -> None:
        """Remove the cup_component resource from Lovelace.

        No-op if Lovelace is not in storage mode.

        Returns:
            None.

        """
        lovelace = self._lovelace
        if not lovelace or lovelace.resource_mode != MODE_STORAGE:
            return
        for resource in list(lovelace.resources.async_items()):
            if resource["url"].split("?")[0] == LOVELACE_MODULE_URL:
                await lovelace.resources.async_delete_item(resource["id"])
                return
