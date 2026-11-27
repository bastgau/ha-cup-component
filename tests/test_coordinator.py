"""Polling of the Cup server by the coordinator (async_update_data in __init__.py)."""

from collections.abc import Iterator
from datetime import timedelta
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientConnectionError
from custom_components.cup_component.const import DOMAIN
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_URL, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

PAYLOAD: dict[str, Any] = {
    "metrics": {},
    "images": [],
    "last_updated": "2026-11-27T10:00:00.000000+00:00",
}
SENSOR = "sensor.cup_monitored_images"


def _tracebacks(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the warning or error records carrying a traceback (Home Assistant's own debug ones are fine)."""
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING and r.exc_info]


def _response(status: int) -> MagicMock:
    """Return the parts of an aiohttp response the Cup client reads, with the given status."""
    return MagicMock(
        status=status, reason="OK" if status < 400 else "Error", content_length=1, json=AsyncMock(return_value=PAYLOAD)
    )


@pytest.fixture(name="dispatch")
def dispatch_fixture(hass: HomeAssistant) -> Iterator[AsyncMock]:
    """Patch the HTTP layer of the Cup client, and mark http and frontend loaded."""
    hass.config.components.add("http")
    hass.config.components.add("frontend")
    with (
        patch("custom_components.cup_component.api.CupApi._dispatch_request", AsyncMock()) as mock,
        patch("custom_components.cup_component.async_register_card", AsyncMock()),
    ):
        yield mock


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    """Add a Cup config entry and set it up."""
    entry = MockConfigEntry(domain=DOMAIN, title="Cup", data={CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize(
    "failure",
    [ClientConnectionError("refused"), TimeoutError()],
    ids=["connection-refused", "timeout"],
)
async def test_unreachable_server_retries_without_traceback(
    hass: HomeAssistant, dispatch: AsyncMock, failure: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    """An unreachable server at startup puts the entry in retry, with no "unexpected error" traceback."""
    dispatch.side_effect = failure

    entry = await _setup(hass)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert "not ready yet: Unable to fetch data from the Cup server" in caplog.text
    assert "Unexpected error fetching" not in caplog.text
    assert _tracebacks(caplog) == []


@pytest.mark.parametrize("status", [500, 404, 418], ids=["server-error", "not-found", "unmapped-status"])
async def test_error_status_after_success_marks_entities_unavailable(
    hass: HomeAssistant, dispatch: AsyncMock, status: int, caplog: pytest.LogCaptureFixture
) -> None:
    """An error answer after a successful start is logged once, plainly, and makes the entities unavailable."""
    dispatch.return_value = _response(200)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(SENSOR).state == "0"  # type: ignore[union-attr]

    dispatch.return_value = _response(status)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=301))
    await hass.async_block_till_done()

    assert hass.states.get(SENSOR).state == STATE_UNAVAILABLE  # type: ignore[union-attr]
    assert "Error fetching Cup data: Unable to fetch data from the Cup server" in caplog.text
    assert "Unexpected error fetching" not in caplog.text
    assert _tracebacks(caplog) == []
