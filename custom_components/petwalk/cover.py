"""Platform for PetWALK cover."""
from __future__ import annotations

import logging
from typing import Any

from pypetwalk.const import API_STATE_DOOR
from pypetwalk.exceptions import (
    PyPetWALKClientConnectionError,
    PyPetWALKInvalidResponseStatus,
)

from homeassistant import config_entries
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import STATE_CLOSED, STATE_OPEN
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
    """Set up the cover platform."""
    coordinator: PetwalkCoordinator = hass.data[DOMAIN][COORDINATOR]

    doors = [
        PetWALKDoor(
            coordinator,
            entity_name="Door",
            entity_id="door",
            api_data_key=API_STATE_DOOR,
            icon="mdi:door",
        ),
    ]

    add_entities(doors)


class PetWALKDoor(CoordinatorEntity, CoverEntity):
    """PetWALK Cover Entity."""

    _attr_available = False
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
    _attr_position = None

    def __init__(
        self,
        coordinator: PetwalkCoordinator,
        entity_name: str,
        entity_id: str,
        api_data_key: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the Door."""
        super().__init__(coordinator)

        self._state = STATE_CLOSED
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
    def is_closed(self) -> bool:
        """Return the current entity state."""
        return bool(self._state == STATE_CLOSED)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if COORDINATOR_KEY_API_DATA in self.coordinator.data:
            data = self.coordinator.data[COORDINATOR_KEY_API_DATA]

            if self._api_data_key not in data:
                raise UpdateFailed(
                    f"Unknown response value {data} for key {self._api_data_key}"
                )

            if data[self._api_data_key]:
                self._state = STATE_OPEN
            else:
                self._state = STATE_CLOSED

            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the Cover/Door."""
        try:
            await self.coordinator.set_state(self._api_data_key, True)

            self._state = STATE_OPEN
            self._attr_available = True

            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the Cover/Door."""
        try:
            await self.coordinator.set_state(self._api_data_key, False)

            self._state = STATE_CLOSED
            self._attr_available = True

            self.async_write_ha_state()  # PetWALK API is slow, so sync here the state
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError):
            self._attr_available = False
