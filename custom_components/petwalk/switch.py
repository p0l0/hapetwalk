"""Platform for PetWALK switch."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Final

from homeassistant import config_entries
from homeassistant.components.switch import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from pypetwalk import PyPetWALK
from pypetwalk.const import (
    API_STATE_BRIGHTNESS_SENSOR,
    API_STATE_DOOR,
    API_STATE_MOTION_IN,
    API_STATE_MOTION_OUT,
    API_STATE_RFID,
    API_STATE_SYSTEM,
    API_STATE_TIME,
)
from pypetwalk.exceptions import (
    PyPetWALKClientConnectionError,
    PyPetWALKInvalidResponseStatus,
)
import voluptuous as vol

from .const import DOMAIN

UPDATE_INTERVAL = timedelta(seconds=15)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA: Final = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    api = PyPetWALK(
        host=config[CONF_IP_ADDRESS],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
    )
    coordinator = SwitchCoordinator(hass, api)

    try:
        device_name = await api.get_device_name()
    except (PyPetWALKClientConnectionError, IndexError, KeyError) as err:
        raise ConfigEntryNotReady from err

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    switches = [
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="Brightness Sensor",
            entity_id="brightness_sensor",
            api_data_key=API_STATE_BRIGHTNESS_SENSOR,
            icon="mdi:brightness-6",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="Motion IN",
            entity_id="motion_in",
            api_data_key=API_STATE_MOTION_IN,
            icon="mdi:account-arrow-left",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="Motion OUT",
            entity_id="motion_out",
            api_data_key=API_STATE_MOTION_OUT,
            icon="mdi:account-arrow-right",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="RFID",
            entity_id="rfid",
            api_data_key=API_STATE_RFID,
            icon="mdi:nfc-variant",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="Time",
            entity_id="time",
            api_data_key=API_STATE_TIME,
            icon="mdi:clock-time-eight",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="Door",
            entity_id="door",
            api_data_key=API_STATE_DOOR,
            icon="mdi:door",
        ),
        PetWALKSwitch(
            api,
            coordinator,
            device_name=device_name,
            entity_name="System",
            entity_id="system",
            api_data_key=API_STATE_SYSTEM,
            icon="mdi:power",
        ),
    ]

    add_entities(switches)


class SwitchCoordinator(DataUpdateCoordinator):  # type: ignore[misc]
    """PetWALK Switch Coordinator."""

    def __init__(self, hass: HomeAssistant, api: PyPetWALK) -> None:
        """Initialize Coordinator."""
        super().__init__(hass, _LOGGER, name="PetWALK", update_interval=UPDATE_INTERVAL)
        self._api = api

    async def _async_update_data(self) -> dict[str, bool]:
        """Fetch data from API."""
        try:
            async with asyncio.timeout(10):
                _LOGGER.info("Fetching API Data")
                return await self._api.get_api_data()
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError) as err:
            raise UpdateFailed("Error communication with API") from err


class PetWALKSwitch(CoordinatorEntity, SwitchEntity):  # type: ignore[misc]
    """PetWALK Switch Entity."""

    _attr_available = False
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        api: PyPetWALK,
        coordinator: SwitchCoordinator,
        device_name: str,
        entity_name: str,
        entity_id: str,
        api_data_key: str,
        icon: str | None = None,
    ):
        """Initialize the Switch."""
        super().__init__(coordinator)

        self._api = api
        self._state = False
        self._device_name = device_name
        self._name = entity_name
        self._entity_id = entity_id
        self._api_data_key = api_data_key
        # self._last_call = datetime.fromtimestamp(0)

        if icon is not None:
            self._attr_icon = icon

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"petwalk_{self._device_name}_{self._entity_id}"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"PetWALK {self._device_name} {self._name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={("petwalk", self._device_name)},
            name=self._device_name,
            manufacturer="Petwalk Solutions GmbH",
        )

    @property
    def is_on(self) -> bool:
        """Return the current entity state."""
        return self._state

    @callback  # type: ignore[misc]
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # if self._last_call < datetime.now():  # PetWALK API is slow, changes take
        # some seconds to be in the response
        data = self.coordinator.data

        if self._api_data_key not in data:
            raise UpdateFailed(
                f"Unknown response value {data} for key {self._api_data_key}"
            )

        self._state = data[self._api_data_key]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        try:
            await self._api.set_state(self._api_data_key, True)

            # self._last_call = datetime.now() + timedelta(seconds=10)
            self._state = True
            self._attr_available = True
            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        try:
            await self._api.set_state(self._api_data_key, False)

            # self._last_call = datetime.now() + timedelta(seconds=10)
            self._state = False
            self._attr_available = True
            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False
