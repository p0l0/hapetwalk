"""Coordinator for PetWALK integration."""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from pypetwalk import PyPetWALK
from pypetwalk.aws import Pet
from pypetwalk.exceptions import (
    PyPetWALKClientConnectionError,
    PyPetWALKInvalidResponseStatus,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow

from .const import (
    CONF_INCLUDE_ALL_EVENTS,
    COORDINATOR_KEY_API_DATA,
    COORDINATOR_KEY_PET_STATUS,
    DOMAIN,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=5)
UPDATE_INTERVAL_DEVICE_TRACKER = timedelta(seconds=120)


class PetwalkCoordinator(DataUpdateCoordinator):
    """PetWALK Coordinator."""

    last_update_pet_status: datetime | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize Coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self._config = hass.data[DOMAIN][config_entry.entry_id]

        self._api = PyPetWALK(
            host=self._config[CONF_IP_ADDRESS],
            username=self._config[CONF_USERNAME],
            password=self._config[CONF_PASSWORD],
        )
        self._device_name = ""
        self._device_id = 0
        self._sw_version = ""
        self._serial_number = ""
        self._pets: list[Pet] = []
        self._device_info: DeviceInfo = DeviceInfo()

    async def initialize(self):
        """Initialize the integration."""
        try:
            self.device_name = await self._api.get_device_name()
            self.device_id = await self._api.get_device_id()
            self.sw_version = await self._api.get_sw_version()
            self.serial_number = await self._api.get_serial_number()
            self.pets = await self._api.get_available_pets(
                self._config[CONF_INCLUDE_ALL_EVENTS]
            )
            self.device_info = DeviceInfo(
                identifiers={(DOMAIN, self.device_name)},
                name=self.device_name,
                manufacturer=MANUFACTURER,
                sw_version=self.sw_version,
                serial_number=self.serial_number,
            )
        except (PyPetWALKClientConnectionError, IndexError, KeyError) as err:
            raise ConfigEntryNotReady from err

        # Fetch initial data, so we have data when entities are subscribed
        await self.async_config_entry_first_refresh()

    @property
    def device_name(self) -> str:
        """Return the Device Name."""
        return self._device_name

    @device_name.setter
    def device_name(self, device_name: str) -> None:
        self._device_name = device_name

    @property
    def device_id(self) -> int:
        """Return the Device ID."""
        return self._device_id

    @device_id.setter
    def device_id(self, device_id: int) -> None:
        self._device_id = device_id

    @property
    def sw_version(self) -> str:
        """Return the Software Version."""
        return self._sw_version

    @sw_version.setter
    def sw_version(self, sw_version: str) -> None:
        self._sw_version = sw_version

    @property
    def serial_number(self) -> str:
        """Return the Serial Number."""
        return self._serial_number

    @serial_number.setter
    def serial_number(self, serial_number: str) -> None:
        self._serial_number = serial_number

    @property
    def pets(self) -> list[Pet]:
        """Return the event RFID Index."""
        return self._pets

    @pets.setter
    def pets(self, pets: list[Pet]) -> None:
        self._pets = pets

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Device Information."""
        return self._device_info

    @device_info.setter
    def device_info(self, device_info: DeviceInfo) -> None:
        self._device_info = device_info

    async def set_state(self, key: str, value: bool) -> None:
        """Set the state for given key."""
        await self._api.set_state(key, value)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            async with asyncio.timeout(10):
                data = self.data
                if data is None:
                    data = {}
                _LOGGER.debug("Fetching local API Data")
                data[COORDINATOR_KEY_API_DATA] = await self._api.get_api_data()

                # To avoid spamming AWS, we have a different update interval for it
                if not (last_update_pet_status := self.last_update_pet_status) or (
                    utcnow() - last_update_pet_status >= UPDATE_INTERVAL_DEVICE_TRACKER
                ):
                    _LOGGER.debug("Fetching Timeline Data from API")
                    data[COORDINATOR_KEY_PET_STATUS] = await self._api.get_pet_status(
                        self.device_id
                    )
                    self.last_update_pet_status = utcnow()

                return data
        except (
            PyPetWALKInvalidResponseStatus,
            PyPetWALKClientConnectionError,
        ) as err:
            raise UpdateFailed("Error communication with API") from err
