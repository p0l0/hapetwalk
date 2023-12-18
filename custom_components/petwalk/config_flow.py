"""Config flow for PetWALK integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pypetwalk import PyPetWALK
from pypetwalk.exceptions import PyPetWALKClientAWSAuthenticationError
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
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
        raise CannotConnectTimeout
    except (IndexError, KeyError) as err:
        _LOGGER.warning(err)
        raise CannotConnect
    except ConnectionRefusedError as err:
        _LOGGER.warning(err)
        raise CannotConnect
    except PyPetWALKClientAWSAuthenticationError as err:
        _LOGGER.warning(err)
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": device_name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PetWALK."""

    VERSION = 1

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


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class CannotConnectTimeout(HomeAssistantError):
    """Error to indicate we cannot connect due to timeout."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
