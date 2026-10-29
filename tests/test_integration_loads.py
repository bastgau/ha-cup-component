"""Check that Home Assistant finds the HA Cup Component integration and imports it.

A first test to start from, seeded once by the template: the repository owns it, edit it or delete it.
"""

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

DOMAIN = "cup_component"


async def test_integration_loads(hass: HomeAssistant, enable_custom_integrations: None) -> None:
    """Home Assistant finds the integration through its manifest and imports its package."""
    integration = await async_get_integration(hass, DOMAIN)
    component = await integration.async_get_component()

    assert integration.domain == DOMAIN
    assert component.__name__ == f"custom_components.{DOMAIN}"
