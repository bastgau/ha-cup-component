"""Config flow to configure the HA Cup Component."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CupApi
from .const import (
    CONF_EXCLUDE_PATTERNS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MIN_SELECTED_UPDATE_INTERVAL,
)
from .exceptions import (
    ClientConnectorError,
    ContentApiTypeError,
    MethodNotAllowedError,
    NotFoundError,
)

_LOGGER = logging.getLogger(__name__)


async def async_try_connect(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, str]:
    """Attempt to connect to the Cup API and return any connection errors.

    Returns:
        dict[str, str]: A dictionary mapping field names to error keys, or an empty dict if successful.

    """

    session = async_get_clientsession(hass, verify_ssl=False)

    api_client = CupApi(
        session=session,
        url=config[CONF_URL],
        logger=_LOGGER,
    )

    try:
        await api_client.call_get_all_data()
    except ClientConnectorError as err:
        _LOGGER.debug("Connection failed: %s", err)
        return {CONF_URL: "cannot_connect"}
    except (
        NotFoundError,
        ContentApiTypeError,
        MethodNotAllowedError,
    ) as err:
        _LOGGER.debug("Connection failed: %s", err)
        return {CONF_URL: "invalid_path"}
    # broad-exception-caught: Intentional: all unexpected errors are caught here to return a user-friendly error in the config flow UI
    except Exception:  # pylint: disable=broad-exception-caught # ai: ignore
        _LOGGER.exception("Unexpected exception during connection attempt to %s", config[CONF_URL])
        return {CONF_URL: "unknown_error"}

    return {}


class CupComponentFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Cup Component config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle a flow initiated by the user.

        Args:
            user_input (dict[str, Any] | None): The data submitted by the user, or None on first load.

        Returns:
            ConfigFlowResult: The result of the config flow step.

        """
        errors = {}

        if user_input is not None:
            self._config = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_URL: user_input[CONF_URL],
            }

            await self.async_set_unique_id(user_input[CONF_URL].lower())
            self._abort_if_unique_id_configured()

            if not (errors := await async_try_connect(self.hass, self._config)):
                return self.async_create_entry(title=user_input[CONF_NAME], data=self._config)

        raw_user_input: dict[str, Any] = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=raw_user_input.get(CONF_NAME, DEFAULT_NAME),
                    ): str,
                    vol.Required(
                        CONF_URL,
                        default=raw_user_input.get(CONF_URL, DEFAULT_URL),
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:  # noqa: ARG004
        """Get the options flow for this handler.

        Args:
            config_entry (ConfigEntry): The current config entry.

        Returns:
            OptionsFlowHandler: The options flow handler instance.

        """
        return OptionsFlowHandler()


def _get_data_option_schema() -> vol.Schema:
    """Build and return the voluptuous schema for the options flow form.

    Returns:
        vol.Schema: The schema used to validate and display the options form.

    """
    return vol.Schema(
        {
            vol.Required(
                CONF_URL,
            ): str,
            vol.Required(
                CONF_UPDATE_INTERVAL,
            ): vol.All(
                selector.NumberSelector(  # pyright: ignore[reportUnknownMemberType]
                    selector.NumberSelectorConfig(
                        min=MIN_SELECTED_UPDATE_INTERVAL.seconds,
                        max=3600,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Optional(
                CONF_EXCLUDE_PATTERNS,
            ): selector.TextSelector(  # pyright: ignore[reportUnknownMemberType]
                selector.TextSelectorConfig(
                    multiple=True,
                )
            ),
        }
    )


async def _async_validate_input(
    user_input: dict[str, Any],
) -> dict[str, str]:
    """Validate user input from the options flow form.

    Args:
        user_input (dict[str, Any]): The data submitted by the user in the options form.

    Returns:
        dict[str, str]: A dictionary mapping field names to error keys if validation fails, or an empty dict if valid.

    """
    if user_input[CONF_UPDATE_INTERVAL] < MIN_SELECTED_UPDATE_INTERVAL.seconds:
        return {CONF_UPDATE_INTERVAL: "invalid_update_interval"}

    patterns: list[str] = [p.strip() for p in user_input.get(CONF_EXCLUDE_PATTERNS, [])]
    user_input[CONF_EXCLUDE_PATTERNS] = patterns
    if len(patterns) != len(set(patterns)):
        return {CONF_EXCLUDE_PATTERNS: "duplicate_exclude_pattern"}

    return {}


class OptionsFlowHandler(OptionsFlow):
    """Options flow used to change configuration (options) of existing instance of integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step of the options flow.

        Args:
            user_input (dict[str, Any] | None): The data submitted by the user, or None on first load.

        Returns:
            ConfigFlowResult: The result of the options flow step.

        """
        if user_input is not None:  # we asked to validate values entered by user
            errors = await _async_validate_input(user_input)

            if len(errors) == 0:
                config = {
                    CONF_URL: user_input.get(CONF_URL),
                }

                errors = await async_try_connect(self.hass, config)

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data={**self.config_entry.data, **user_input}
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    _get_data_option_schema(),
                    user_input,
                ),
                errors=dict(errors),
            )

        return self._async_show_init_form()

    def _async_show_init_form(self) -> ConfigFlowResult:
        """Initialise the default update interval if missing and display the options form.

        If the update interval is not yet set in the config entry data, it is initialised
        with the default value before the form is displayed.

        Returns:
            ConfigFlowResult: The form result with pre-filled default values.

        """

        update_interval = self.config_entry.data.get(CONF_UPDATE_INTERVAL, None)

        if update_interval is None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL.seconds,
                },
            )

        # we asked to provide default values for the form
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _get_data_option_schema(),
                self.config_entry.data,
            ),
        )
