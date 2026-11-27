"""What the recorder keeps of the Cup sensors: the counts, never the image lists (sensor.py)."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

from custom_components.cup_component.const import DOMAIN
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.components.recorder.common import async_wait_recording_done

from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

IMAGE: dict[str, Any] = {
    "reference": "nginx:latest",
    "parts": {"registry": "registry-1.docker.io", "repository": "library/nginx", "tag": "latest"},
    "url": None,
    "result": {"has_update": False, "info": None, "error": None},
    "time": 10,
    "server": None,
    "in_use": True,
}
PAYLOAD: dict[str, Any] = {"metrics": {}, "images": [IMAGE], "last_updated": "2026-11-27T10:00:00.000000+00:00"}

# The sensors that carry an image list in their state attributes.
LIST_SENSORS = [
    "sensor.cup_monitored_images",
    "sensor.cup_updates_available",
    "sensor.cup_up_to_date",
    "sensor.cup_major_updates",
    "sensor.cup_excluded_images",
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Recorder, enable_custom_integrations: None) -> None:
    """Override conftest's: the recorder must start before the hass fixture that enabling custom integrations needs."""
    assert recorder_mock is not None
    assert enable_custom_integrations is None


@pytest.fixture(name="cup_server")
def cup_server_fixture(hass: HomeAssistant) -> Iterator[None]:
    """Answer the Cup API with one up-to-date image, and mark http and frontend loaded."""
    hass.config.components.add("http")
    hass.config.components.add("frontend")
    with (
        patch(
            "custom_components.cup_component.api.CupApi._call",
            AsyncMock(return_value={"code": 200, "reason": "OK", "data": PAYLOAD}),
        ),
        patch("custom_components.cup_component.async_register_card", AsyncMock()),
    ):
        yield


@pytest.mark.usefixtures("cup_server")
async def test_image_lists_are_not_recorded(hass: HomeAssistant) -> None:
    """The image lists stay in the live state but never reach the recorder's database."""
    start = dt_util.utcnow()
    entry = MockConfigEntry(domain=DOMAIN, title="Cup", data={CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    live = hass.states.get("sensor.cup_monitored_images")
    assert live is not None
    assert live.attributes["images_list"] == [IMAGE]

    history = await hass.async_add_executor_job(get_significant_states, hass, start, None, LIST_SENSORS)
    assert set(history) == set(LIST_SENSORS)
    for entity_id, states in history.items():
        for state in states:
            assert "images_list" not in state.attributes, entity_id
    assert history["sensor.cup_monitored_images"][-1].state == "1"
