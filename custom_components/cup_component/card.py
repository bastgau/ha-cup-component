"""Registration of the Lovelace card the integration ships (``frontend/cup-component-card.js``).

Seeded once by the template: the repository owns it from here on.
"""

import hashlib
import logging
from pathlib import Path
from typing import Final

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig  # pyright: ignore[reportPrivateImportUsage]
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME: Final = "cup-component-card.js"
CARD_URL_PATH: Final = f"/cup_component/{CARD_FILENAME}"
CARD_PATH: Final = Path(__file__).parent / "frontend" / CARD_FILENAME
VERSION_LENGTH: Final = 8


def card_version(path: Path) -> str:
    """Return a short content hash of the card, used to bust the browser cache.

    Blocking: call it in the executor.

    Args:
        path (Path): The card's file.

    Returns:
        str: The first 8 hexadecimal characters of the SHA-256 of the file's bytes.

    """
    return hashlib.sha256(path.read_bytes()).hexdigest()[:VERSION_LENGTH]


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it on every frontend page.

    Called once per Home Assistant run, from ``async_setup``. It never raises: the integration works without the
    card (an unreadable file, or a path that is already registered, is only a warning).

    Args:
        hass (HomeAssistant): The Home Assistant instance.

    """
    if "http" not in hass.config.components or "frontend" not in hass.config.components:
        _LOGGER.debug("The http or frontend component is not loaded: the card is not served")
        return

    try:
        version = await hass.async_add_executor_job(card_version, CARD_PATH)
    except OSError as err:
        _LOGGER.warning("The card %s cannot be read, it is not served: %s", CARD_PATH, err)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(CARD_PATH), cache_headers=True)]
        )
    except RuntimeError as err:
        # The path is already served (the same card registered by another run of this setup): keep going.
        _LOGGER.warning("The card path %s is already registered, it is not registered again: %s", CARD_URL_PATH, err)
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={version}")
