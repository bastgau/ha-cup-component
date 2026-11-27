"""Support for Cup Component update entities, one per monitored image."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.update import DOMAIN as UPDATE_DOMAIN, UpdateEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_UPDATE_ENTITIES, DEFAULT_UPDATE_ENTITIES, DOMAIN
from .entity import CupComponentEntity
from .helper import create_entity_id_name

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from . import CupComponentConfigEntry, CupComponentData
    from .api import CupApi

# Read-only entities fed by the coordinator: no parallel update limit is needed.
PARALLEL_UPDATES = 0
_LOGGER = logging.getLogger(__name__)

# Latest version shown when Cup reports an update without any comparable version or digest.
_UNKNOWN_NEW_VERSION = "update available"

# Same short digest as the Lovelace card: the 12 characters after the "sha256:" prefix.
_DIGEST_START = 7
_DIGEST_END = 19


def build_unique_id(server_unique_id: str, image_key: str) -> str:
    """Build the unique id of the update entity of an image.

    Args:
        server_unique_id (str): The unique identifier of the config entry.
        image_key (str): The image key, as built by ``CupApi.image_key``.

    Returns:
        str: The unique id of the entity.

    """

    return f"{server_unique_id}/update/{image_key}"


def _short_digest(digest: str | None) -> str | None:
    """Shorten an image digest for display.

    Args:
        digest (str | None): A digest such as ``sha256:0123...``, or None.

    Returns:
        str | None: The 12-character short digest, or None if no digest was given.

    """

    if not digest:
        return None

    return digest[_DIGEST_START:_DIGEST_END]


def get_image_versions(image: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return the installed and the latest version of an image, as shown by its update entity.

    Args:
        image (dict[str, Any]): An image object from the Cup API response.

    Returns:
        tuple[str | None, str | None]: The installed and the latest version; both are None when Cup does not know.

    """

    result: dict[str, Any] = image.get("result") or {}
    has_update: bool | None = result.get("has_update")

    if has_update is None:
        return None, None

    parts: dict[str, Any] = image.get("parts") or {}
    tag: str = parts.get("tag") or image.get("reference", "")

    if has_update is False:
        return tag, tag

    info: dict[str, Any] = result.get("info") or {}
    installed: str | None = None
    latest: str | None = None

    if info.get("type") == "digest":
        local_digests: list[str] = info.get("local_digests") or []
        installed = _short_digest(local_digests[0] if local_digests else None)
        latest = _short_digest(info.get("remote_digest"))
    else:
        installed = info.get("current_version")
        latest = info.get("new_version")

    # An update is pending: never let the entity look up to date or unknown.
    installed = installed or tag
    if not latest or latest == installed:
        latest = _UNKNOWN_NEW_VERSION

    return installed, latest


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CupComponentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one update entity per monitored image, and keep them in sync with the Cup server.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry for this integration.
        async_add_entities (AddConfigEntryEntitiesCallback): Callback to register new entities.

    """

    if not entry.data.get(CONF_UPDATE_ENTITIES, DEFAULT_UPDATE_ENTITIES):
        # The option is off: drop the entities a previous run may have created.
        async_remove_update_entities(hass, entry)
        return

    name: str = entry.data[CONF_NAME]
    cup_data: CupComponentData = entry.runtime_data
    entity_registry = er.async_get(hass)

    # Remove the entities of images that are gone or now excluded since the last run.
    expected_unique_ids: set[str] = {
        build_unique_id(entry.entry_id, key) for key in cup_data.api.cache_monitored_images
    }
    async_remove_update_entities(hass, entry, keep=expected_unique_ids)

    known_keys: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        """Add the entities of new images and remove those of images that disappeared."""

        current_keys: set[str] = set(cup_data.api.cache_monitored_images)

        if new_keys := current_keys - known_keys:
            known_keys.update(new_keys)
            async_add_entities(CupComponentUpdate(cup_data, name, entry.entry_id, key) for key in sorted(new_keys))

        for key in known_keys - current_keys:
            known_keys.discard(key)
            unique_id: str = build_unique_id(entry.entry_id, key)

            if entity_id := entity_registry.async_get_entity_id(UPDATE_DOMAIN, DOMAIN, unique_id):
                _LOGGER.debug("Image '%s' is no longer monitored, removing %s.", key, entity_id)
                entity_registry.async_remove(entity_id)

    _async_sync_entities()
    entry.async_on_unload(cup_data.coordinator.async_add_listener(_async_sync_entities))


@callback
def async_remove_update_entities(
    hass: HomeAssistant,
    entry: CupComponentConfigEntry,
    keep: set[str] | None = None,
) -> None:
    """Remove the update entities of a config entry from the entity registry.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (CupComponentConfigEntry): The config entry whose update entities are removed.
        keep (set[str] | None): Unique ids to keep; every update entity is removed when None.

    """

    entity_registry = er.async_get(hass)
    keep = keep or set()

    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.domain == UPDATE_DOMAIN and registry_entry.unique_id not in keep:
            _LOGGER.debug("Removing update entity %s.", registry_entry.entity_id)
            entity_registry.async_remove(registry_entry.entity_id)


class CupComponentUpdate(CupComponentEntity, UpdateEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Update entity telling whether a new version of a monitored image is available.

    Cup only checks for updates: the entity cannot install them.

    Attributes:
        _image_key (str): The key of the image this entity follows.
        _attr_unique_id (str): The unique id, built from the server id and the image key.
        _attr_name (str): The image reference (e.g. ``nginx:latest``).
        entity_id (str): The entity id derived from the server name, the agent and the image reference.

    """

    def __init__(
        self,
        cup_data: CupComponentData,
        name: str,
        server_unique_id: str,
        image_key: str,
    ) -> None:
        """Initialize a Cup Component update entity.

        Args:
            cup_data (CupComponentData): Runtime data containing the API client and coordinator.
            name (str): The human-readable name of the Cup server.
            server_unique_id (str): The unique identifier of the config entry.
            image_key (str): The key of the image this entity follows, as built by ``CupApi.image_key``.

        """

        api: CupApi = cup_data.api
        coordinator: DataUpdateCoordinator[None] = cup_data.coordinator

        super().__init__(api, coordinator, name, server_unique_id)
        self._image_key = image_key
        self._attr_unique_id = build_unique_id(server_unique_id, image_key)

        image: dict[str, Any] = api.cache_monitored_images.get(image_key, {})
        reference: str = image.get("reference", image_key)
        server: str | None = image.get("server")
        self._attr_name = reference if server is None else f"{reference} ({server})"

        raw_name: str = f"update.{name}_{reference}" if server is None else f"update.{name}_{server}_{reference}"
        self.entity_id = create_entity_id_name(raw_name)

    @property
    def _image(self) -> dict[str, Any] | None:
        """Return the image this entity follows, from the last response.

        Returns:
            dict[str, Any] | None: The image object, or None if it is no longer monitored.

        """

        return self.api.cache_monitored_images.get(self._image_key)

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return whether the image is still monitored and the coordinator is up.

        Returns:
            bool: True if the entity is available.

        """

        return super().available and self._image is not None

    @property
    def installed_version(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the version, or short digest, of the local image.

        Returns:
            str | None: The installed version, or None when unknown.

        """

        if (image := self._image) is None:
            return None

        return get_image_versions(image)[0]

    @property
    def latest_version(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the version, or short digest, of the latest remote image.

        Returns:
            str | None: The latest version, or None when unknown.

        """

        if (image := self._image) is None:
            return None

        return get_image_versions(image)[1]

    @property
    def release_url(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the project URL from the image's ``org.opencontainers.image.url`` label.

        Returns:
            str | None: The URL, or None if the image has no such label.

        """

        if (image := self._image) is None:
            return None

        return image.get("url") or None

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Trust Cup's verdict instead of comparing the version strings.

        Args:
            latest_version (str): The latest version (unused).
            installed_version (str): The installed version (unused).

        Returns:
            bool: True if Cup reports an update for the image.

        """

        if (image := self._image) is None:
            return False

        result: dict[str, Any] = image.get("result") or {}
        return result.get("has_update") is True
