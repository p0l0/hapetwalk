"""Platform for PetWALK sensor."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, UpdateFailed

from .const import (
    CONF_INCLUDE_ALL_EVENTS,
    COORDINATOR,
    COORDINATOR_KEY_PET_STATUS,
    DOMAIN,
    NAME,
)
from .coordinator import PetwalkCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: PetwalkCoordinator = hass.data[DOMAIN][COORDINATOR]

    entities = []
    if config[CONF_INCLUDE_ALL_EVENTS]:
        pets = coordinator.pets
        if len(pets) > 0:
            for pet in pets:
                if pet.species and pet.name:
                    entity_id = f"pet_{pet.species.lower()}_{pet.name.lower()}"
                elif pet.name:
                    entity_id = f"pet_{pet.name.lower()}"
                else:
                    _LOGGER.error(
                        "No Name for %s provided, skipping for addition", pet.id
                    )
                    continue

                entities.append(
                    PetTimestampSensor(
                        coordinator,
                        pet_id=pet.id,
                        species=pet.species,
                        entity_name=f"{pet.name} last event",
                        entity_id=entity_id,
                    )
                )

    if len(entities) > 0:
        _LOGGER.debug("Adding our Pet entities")
        add_entities(entities, True)


class PetTimestampSensor(CoordinatorEntity, SensorEntity):
    """Pet Sensor Entity."""

    _attr_available = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_native_value = None

    def __init__(
        self,
        coordinator: PetwalkCoordinator,
        pet_id: str,
        species: str | None,
        entity_name: str | None,
        entity_id: str,
    ) -> None:
        """Initialize the Device Tracker."""
        super().__init__(coordinator)

        self._pet_id = pet_id
        self._species = species
        self._device_name = coordinator.device_name
        self._name = entity_name
        self._entity_id = entity_id
        self._state = None

    @property
    def unique_id(self) -> str | None:
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
    def icon(self) -> str | None:
        """Return the icon of the device."""
        if not self._species:
            return "mdi:paw"

        match self._species.lower():
            case "cat":
                return "mdi:cat"
            case "dog":
                return "mdi:dog"
            case _:
                return "mdi:paw"

    @property
    def state(self) -> datetime | None:
        """Return current state."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if COORDINATOR_KEY_PET_STATUS in self.coordinator.data:
            data = self.coordinator.data[COORDINATOR_KEY_PET_STATUS]

            if self._pet_id not in data:
                raise UpdateFailed(
                    f"Unable to find current status for {self._name} ({self._pet_id})"
                )

            event = data[self._pet_id]
            self._state = event.date

            self.async_write_ha_state()
