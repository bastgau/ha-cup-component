"""Diagnostics support for Cup Component."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data  # pyright: ignore[reportUnknownVariableType]
from homeassistant.const import CONF_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import CupComponentConfigEntry

# Fields to redact from diagnostics output to avoid exposing sensitive data.
_DIAGNOSTICS_REDACT: frozenset[str] = frozenset({CONF_URL})


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001 # pylint: disable=unused-argument
    entry: CupComponentConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Sensitive fields (URL) are redacted from the output.

    Args:
        hass (HomeAssistant): The Home Assistant instance (unused).
        entry (CupComponentConfigEntry): The config entry to diagnose.

    Returns:
        dict[str, Any]: A dictionary containing redacted config and current runtime data.

    """
    return {
        "config": async_redact_data(dict(entry.data), _DIAGNOSTICS_REDACT),
        "data": {
            "metrics": entry.runtime_data.api.cache_metrics,
            "last_checked": str(entry.runtime_data.api.cache_last_checked),
            "images": entry.runtime_data.api.cache_images,
        },
    }
