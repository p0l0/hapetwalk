"""Config flow for PetWALK integration."""
from __future__ import annotations

import logging
from typing import Any

from pypetwalk import PyPetWALK
from pypetwalk.exceptions import PyPetWALKClientAWSAuthenticationError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_INCLUDE_ALL_EVENTS, DEFAULT_INCLUDE_ALL_EVENTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_INCLUDE_ALL_EVENTS): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        api = PyPetWALK(
            host=data[CONF_IP_ADDRESS],
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
        )
        # Test REST API
        await api.get_system_state()
        # Test Websocket API
        device_name = await api.get_device_name()
        # Test AWS API
        await api.get_aws_update_info()
    except TimeoutError as err:
        _LOGGER.warning(err)
        raise CannotConnectTimeout from err
    except (IndexError, KeyError) as err:
        _LOGGER.warning(err)
        raise CannotConnect from err
    except ConnectionRefusedError as err:
        _LOGGER.warning(err)
        raise CannotConnect from err
    except PyPetWALKClientAWSAuthenticationError as err:
        _LOGGER.warning(err)
        raise InvalidAuth from err

    # Return info that you want to store in the config entry.
    return {"title": device_name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for PetWALK."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except CannotConnectTimeout:
                errors["base"] = "cannot_connect_timeout"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(OptionsFlow):
    """Handle PetWALK options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage PetWALK options."""
        if user_input is not None:
            # Save options also in config entry
            data = {**self.config_entry.data}
            for key, value in user_input.items():
                data[key] = value
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)

            return self.async_create_entry(
                title=self.config_entry.title, data=user_input
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_INCLUDE_ALL_EVENTS,
                        default=self.config_entry.options.get(
                            CONF_INCLUDE_ALL_EVENTS, DEFAULT_INCLUDE_ALL_EVENTS
                        ),
                    ): bool
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class CannotConnectTimeout(HomeAssistantError):
    """Error to indicate we cannot connect due to timeout."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
