"""Platform for PetWALK switch."""
from __future__ import annotations

import logging
from typing import Any

from pypetwalk.const import (
    API_STATE_BRIGHTNESS_SENSOR,
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

from homeassistant import config_entries
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, UpdateFailed

from .const import COORDINATOR, COORDINATOR_KEY_API_DATA, DOMAIN, NAME
from .coordinator import PetwalkCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    coordinator: PetwalkCoordinator = hass.data[DOMAIN][COORDINATOR]

    switches = [
        PetWALKSwitch(
            coordinator,
            entity_name="Brightness Sensor",
            entity_id="brightness_sensor",
            api_data_key=API_STATE_BRIGHTNESS_SENSOR,
            icon="mdi:brightness-6",
        ),
        PetWALKSwitch(
            coordinator,
            entity_name="Motion IN",
            entity_id="motion_in",
            api_data_key=API_STATE_MOTION_IN,
            icon="mdi:account-arrow-left",
        ),
        PetWALKSwitch(
            coordinator,
            entity_name="Motion OUT",
            entity_id="motion_out",
            api_data_key=API_STATE_MOTION_OUT,
            icon="mdi:account-arrow-right",
        ),
        PetWALKSwitch(
            coordinator,
            entity_name="RFID",
            entity_id="rfid",
            api_data_key=API_STATE_RFID,
            icon="mdi:nfc-variant",
        ),
        PetWALKSwitch(
            coordinator,
            entity_name="Time",
            entity_id="time",
            api_data_key=API_STATE_TIME,
            icon="mdi:clock-time-eight",
        ),
        PetWALKSwitch(
            coordinator,
            entity_name="System",
            entity_id="system",
            api_data_key=API_STATE_SYSTEM,
            icon="mdi:power",
        ),
    ]

    add_entities(switches)


class PetWALKSwitch(CoordinatorEntity, SwitchEntity):
    """PetWALK Switch Entity."""

    _attr_available = False
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: PetwalkCoordinator,
        entity_name: str,
        entity_id: str,
        api_data_key: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the Switch."""
        super().__init__(coordinator)

        self._state = False
        self._device_name = coordinator.device_name
        self._name = entity_name
        self._entity_id = entity_id
        self._api_data_key = api_data_key

        if icon is not None:
            self._attr_icon = icon

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_name}_{self._entity_id}"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{NAME} {self._device_name} {self._name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return the current entity state."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if COORDINATOR_KEY_API_DATA in self.coordinator.data:
            data = self.coordinator.data[COORDINATOR_KEY_API_DATA]

            if self._api_data_key not in data:
                raise UpdateFailed(
                    f"Unknown response value {data} for key {self._api_data_key}"
                )

            self._state = data[self._api_data_key]
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        try:
            await self.coordinator.set_state(self._api_data_key, True)

            self._state = True
            self._attr_available = True

            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        try:
            await self.coordinator.set_state(self._api_data_key, False)

            self._state = False
            self._attr_available = True

            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False
