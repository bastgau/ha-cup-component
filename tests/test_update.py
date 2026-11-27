"""Update entities of the HA Cup Component integration, one per monitored image (update.py)."""

from collections.abc import Callable, Iterator
import copy
from datetime import timedelta
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from custom_components.cup_component.const import (
    CONF_EXCLUDE_PATTERNS,
    CONF_UPDATE_ENTITIES,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.cup_component.update import build_unique_id, get_image_versions
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from homeassistant.const import CONF_NAME, CONF_URL, STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

FIXTURE: dict[str, Any] = json.loads((Path(__file__).parent / "fixtures" / "images.json").read_text(encoding="utf-8"))

CUP_ENTITY = "update.cup_ghcr_io_sergi0g_cup_v3_5_0"
NGINX_ENTITY = "update.cup_nginx_latest"
NGINX_AGENT_ENTITY = "update.cup_agent1_nginx_latest"
REDIS_ENTITY = "update.cup_redis_7"
PRIVATE_ENTITY = "update.cup_private_app_1_0"
ODD_ENTITY = "update.cup_odd_image_2"


@pytest.fixture(name="payload")
def payload_fixture() -> dict[str, Any]:
    """Return a fresh copy of the Cup API response used by the tests."""
    return copy.deepcopy(FIXTURE)


@pytest.fixture(name="mock_call")
def mock_call_fixture(payload: dict[str, Any]) -> Iterator[AsyncMock]:
    """Answer every Cup API call with the current ``payload``, keeping the client's real parsing."""

    async def _call(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"code": 200, "reason": "OK", "data": copy.deepcopy(payload)}

    with (
        patch("custom_components.cup_component.api.CupApi._call", side_effect=_call) as mock,
        patch("custom_components.cup_component.async_register_card", AsyncMock()),
    ):
        yield mock


@pytest.fixture(name="setup_entry")
def setup_entry_fixture(hass: HomeAssistant, mock_call: AsyncMock) -> Callable[..., Any]:
    """Return a coroutine function that sets up a config entry with the given extra data."""

    # The integration depends on http and frontend: mark them loaded instead of starting them.
    hass.config.components.add("http")
    hass.config.components.add("frontend")

    async def _setup(**data: Any) -> MockConfigEntry:
        # The option is on unless a test says otherwise; its default is tested on its own.
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Cup",
            data={CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000", CONF_UPDATE_ENTITIES: True, **data},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


def _update_entity_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    """Return the update entity ids registered for a config entry."""
    registry = er.async_get(hass)
    return {e.entity_id for e in er.async_entries_for_config_entry(registry, entry.entry_id) if e.domain == "update"}


async def _refresh(hass: HomeAssistant) -> None:
    """Trigger the coordinator's next poll."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=301))
    await hass.async_block_till_done()


async def test_one_entity_per_monitored_image(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """Every image gets its own entity, and the same image on an agent gets a distinct one."""
    entry = await setup_entry()

    assert _update_entity_ids(hass, entry) == {
        CUP_ENTITY,
        NGINX_ENTITY,
        NGINX_AGENT_ENTITY,
        REDIS_ENTITY,
        PRIVATE_ENTITY,
        ODD_ENTITY,
    }
    registry = er.async_get(hass)
    assert registry.async_get(NGINX_AGENT_ENTITY).unique_id == build_unique_id(entry.entry_id, "agent1/nginx:latest")  # type: ignore[union-attr]


async def test_version_update(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """A version update shows both versions and the image's project URL."""
    await setup_entry()

    state = hass.states.get(CUP_ENTITY)
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "3.5.0"
    assert state.attributes["latest_version"] == "4.0.0"
    assert state.attributes["release_url"] == "https://github.com/sergi0g/cup"
    assert state.attributes["supported_features"] == 0


async def test_digest_update(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """A digest update shows the short local and remote digests."""
    await setup_entry()

    state = hass.states.get(NGINX_ENTITY)
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["installed_version"] == "aaaaaaaaaaaa"
    assert state.attributes["latest_version"] == "111111111111"
    assert state.attributes["release_url"] is None


async def test_up_to_date_unknown_and_no_info(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """Up-to-date images are off, unknown ones unknown, and an update without info is still on."""
    await setup_entry()

    redis = hass.states.get(REDIS_ENTITY)
    assert redis is not None
    assert redis.state == STATE_OFF
    assert redis.attributes["installed_version"] == "7"

    private = hass.states.get(PRIVATE_ENTITY)
    assert private is not None
    assert private.state == STATE_UNKNOWN

    odd = hass.states.get(ODD_ENTITY)
    assert odd is not None
    assert odd.state == STATE_ON
    assert odd.attributes["installed_version"] == "2"
    assert odd.attributes["latest_version"] == "update available"


async def test_excluded_images_have_no_entity(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """Images matching an exclusion pattern get no update entity."""
    entry = await setup_entry(**{CONF_EXCLUDE_PATTERNS: ["nginx:.*"]})

    ids = _update_entity_ids(hass, entry)
    assert NGINX_ENTITY not in ids
    assert NGINX_AGENT_ENTITY not in ids
    assert CUP_ENTITY in ids


async def test_newly_excluded_image_is_removed_on_reload(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """Excluding an image, which reloads the entry, removes its entity from the registry."""
    entry = await setup_entry()
    assert REDIS_ENTITY in _update_entity_ids(hass, entry)

    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_EXCLUDE_PATTERNS: ["redis:7"]})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert REDIS_ENTITY not in _update_entity_ids(hass, entry)
    assert hass.states.get(REDIS_ENTITY) is None


async def test_images_added_and_removed_between_polls(
    hass: HomeAssistant, setup_entry: Callable[..., Any], payload: dict[str, Any]
) -> None:
    """A new image gets an entity on the next poll, and a vanished image loses its entity."""
    entry = await setup_entry()

    payload["images"] = [image for image in payload["images"] if image["reference"] != "redis:7"]
    payload["images"].append(
        {
            "reference": "postgres:16",
            "parts": {"registry": "registry-1.docker.io", "repository": "library/postgres", "tag": "16"},
            "url": None,
            "result": {"has_update": False, "info": None, "error": None},
            "time": 10,
            "server": None,
            "in_use": True,
        }
    )
    await _refresh(hass)

    ids = _update_entity_ids(hass, entry)
    assert REDIS_ENTITY not in ids
    assert "update.cup_postgres_16" in ids
    assert hass.states.get("update.cup_postgres_16").state == STATE_OFF  # type: ignore[union-attr]


async def test_unavailable_when_server_fails(
    hass: HomeAssistant, setup_entry: Callable[..., Any], mock_call: AsyncMock
) -> None:
    """The entities become unavailable when the Cup server cannot be polled."""
    await setup_entry()

    mock_call.side_effect = TimeoutError
    await _refresh(hass)

    assert hass.states.get(CUP_ENTITY).state == STATE_UNAVAILABLE  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("image", "expected"),
    [
        (
            {
                "result": {"has_update": True, "info": {"type": "digest", "local_digests": [], "remote_digest": None}},
                "parts": {"tag": "x"},
            },
            ("x", "update available"),
        ),
        (
            {
                "result": {"has_update": True, "info": {"type": "version", "current_version": "1", "new_version": "1"}},
                "reference": "r",
            },
            ("1", "update available"),
        ),
        ({"result": {}, "reference": "r"}, (None, None)),
    ],
)
def test_get_image_versions_edge_cases(image: dict[str, Any], expected: tuple[str | None, str | None]) -> None:
    """Missing digests, equal versions and a missing result never produce a wrong state."""
    assert get_image_versions(image) == expected


@pytest.mark.usefixtures("setup_entry")  # marks http and frontend loaded
async def test_no_entity_by_default(hass: HomeAssistant) -> None:
    """An entry without the option, as every existing entry, creates no update entity."""
    entry = MockConfigEntry(domain=DOMAIN, title="Cup", data={CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert _update_entity_ids(hass, entry) == set()
    assert hass.states.async_entity_ids("update") == []


async def test_options_flow_default_and_toggle(hass: HomeAssistant, setup_entry: Callable[..., Any]) -> None:
    """The option is off in the options form by default; turning it on then off adds then removes the entities."""
    entry = await setup_entry(**{CONF_UPDATE_ENTITIES: False})
    assert _update_entity_ids(hass, entry) == set()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]
    assert schema is not None
    assert schema({CONF_URL: "http://cup.local:8000", CONF_UPDATE_INTERVAL: 300})[CONF_UPDATE_ENTITIES] is False

    async def _set_option(*, value: bool) -> None:
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        await hass.config_entries.options.async_configure(
            flow["flow_id"],
            {CONF_URL: "http://cup.local:8000", CONF_UPDATE_INTERVAL: 300, CONF_UPDATE_ENTITIES: value},
        )
        await hass.async_block_till_done()

    await _set_option(value=True)
    assert entry.data[CONF_UPDATE_ENTITIES] is True
    assert CUP_ENTITY in _update_entity_ids(hass, entry)
    assert hass.states.get(CUP_ENTITY).state == STATE_ON  # type: ignore[union-attr]

    await _set_option(value=False)
    assert _update_entity_ids(hass, entry) == set()
    assert hass.states.get(CUP_ENTITY) is None


@pytest.mark.usefixtures("setup_entry")  # marks http and frontend loaded
@pytest.mark.parametrize(("user_choice", "expected"), [(None, False), (False, False), (True, True)])
async def test_user_step_option(hass: HomeAssistant, user_choice: bool | None, expected: bool) -> None:
    """The setup form offers the option, off by default, and the new entry follows the choice."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["data_schema"] is not None
    assert result["data_schema"]({CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000"})[CONF_UPDATE_ENTITIES] is False

    user_input: dict[str, Any] = {CONF_NAME: "Cup", CONF_URL: "http://cup.local:8000"}
    if user_choice is not None:
        user_input[CONF_UPDATE_ENTITIES] = user_choice
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    await hass.async_block_till_done()

    entry = result["result"]
    assert entry.data[CONF_UPDATE_ENTITIES] is expected
    assert bool(_update_entity_ids(hass, entry)) is expected
