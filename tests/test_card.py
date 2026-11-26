"""Registration of the Lovelace card of the HA Cup Component integration (card.py).

Seeded once by the template (with ``has_card``): the repository owns it, edit it or delete it.
"""

from collections.abc import Iterator
import hashlib
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.cup_component import DOMAIN, card
from custom_components.cup_component.card import CARD_PATH, CARD_URL_PATH, card_version
import pytest

from homeassistant.components.http import StaticPathConfig  # pyright: ignore[reportPrivateImportUsage]
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

CARD_LOGGER = "custom_components.cup_component.card"


@pytest.fixture(name="add_js")
def add_js_fixture() -> Iterator[MagicMock]:
    """Patch ``add_extra_js_url`` where the card calls it."""
    with patch.object(card, "add_extra_js_url") as mock:
        yield mock


@pytest.fixture(name="http")
def http_fixture(hass: HomeAssistant) -> AsyncMock:
    """Make Home Assistant look as if http and frontend were loaded, with a mocked http server."""
    hass.config.components.add("http")
    hass.config.components.add("frontend")
    register = AsyncMock()
    hass.http = MagicMock(async_register_static_paths=register)
    return register


def test_card_url_path() -> None:
    """The card is served under the integration's own namespace, and the file exists."""
    assert f"/{DOMAIN}/{CARD_PATH.name}" == CARD_URL_PATH
    assert CARD_PATH.is_file()


def test_card_version_is_the_content_hash(tmp_path: Path) -> None:
    """The version is the first 8 hex characters of the SHA-256 of the bytes, and follows the content."""
    assert card_version(CARD_PATH) == hashlib.sha256(CARD_PATH.read_bytes()).hexdigest()[:8]
    other = tmp_path / "other.js"
    other.write_bytes(b"export const other = 1;\n")
    assert card_version(other) != card_version(CARD_PATH)


async def test_registered_by_the_setup(hass: HomeAssistant, http: AsyncMock, add_js: MagicMock) -> None:
    """Setting the integration up serves the card and adds it as an extra module, once."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    version = card_version(CARD_PATH)
    http.assert_awaited_once_with([StaticPathConfig(CARD_URL_PATH, str(CARD_PATH), cache_headers=True)])
    add_js.assert_called_once_with(hass, f"{CARD_URL_PATH}?v={version}")


@pytest.mark.parametrize("missing", ["frontend", "http"])
async def test_without_frontend_or_http(
    hass: HomeAssistant,
    http: AsyncMock,
    add_js: MagicMock,
    caplog: pytest.LogCaptureFixture,
    missing: str,
) -> None:
    """Without one of the two components: nothing registered, one debug line, no error."""
    hass.config.components.remove(missing)

    with caplog.at_level(logging.DEBUG, logger=CARD_LOGGER):
        await card.async_register_card(hass)

    http.assert_not_awaited()
    add_js.assert_not_called()
    assert [record.levelno for record in caplog.records if record.name == CARD_LOGGER] == [logging.DEBUG]


async def test_missing_card_file(
    hass: HomeAssistant,
    http: AsyncMock,
    add_js: MagicMock,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """An unreadable card: one warning, nothing registered, no error."""
    with patch.object(card, "CARD_PATH", tmp_path / "missing.js"), caplog.at_level(logging.DEBUG, logger=CARD_LOGGER):
        await card.async_register_card(hass)

    http.assert_not_awaited()
    add_js.assert_not_called()
    assert [record.levelno for record in caplog.records if record.name == CARD_LOGGER] == [logging.WARNING]


async def test_path_already_registered(
    hass: HomeAssistant,
    http: AsyncMock,
    add_js: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A static path that is already registered: one warning, the module is still added, no error."""
    http.side_effect = RuntimeError("Path already registered")

    with caplog.at_level(logging.DEBUG, logger=CARD_LOGGER):
        await card.async_register_card(hass)

    add_js.assert_called_once()
    records = [record for record in caplog.records if record.name == CARD_LOGGER]
    assert [record.levelno for record in records] == [logging.WARNING]
    assert "already registered" in records[0].getMessage()
