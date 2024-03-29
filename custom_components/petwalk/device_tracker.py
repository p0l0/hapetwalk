"""Platform for PetWALK device tracker."""
from __future__ import annotations

import logging

from pypetwalk.const import EVENT_DIRECTION_IN, EVENT_DIRECTION_OUT

from homeassistant import config_entries
from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, UpdateFailed

from .const import COORDINATOR, COORDINATOR_KEY_PET_STATUS, DOMAIN, NAME
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

    entities = []
    pets = coordinator.pets
    if len(pets) > 0:
        for pet in pets:
            if pet.unknown:
                _LOGGER.debug(
                    "Skipping Unknown pet with id %s and name %s", pet.id, pet.name
                )
                continue

            if pet.species and pet.name:
                entity_id = f"pet_{pet.species.lower()}_{pet.name.lower()}"
            elif pet.name:
                entity_id = f"pet_{pet.name.lower()}"
            else:
                _LOGGER.warning(
                    "No Name for %s provided, skipping for addition", pet.id
                )
                continue

            entities.append(
                PetDeviceTracker(
                    coordinator,
                    pet_id=pet.id,
                    species=pet.species,
                    entity_name=pet.name,
                    entity_id=entity_id,
                )
            )

    if len(entities) > 0:
        _LOGGER.debug("Adding our Pet entities")
        add_entities(entities, True)


class PetDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Pet Device Tracker Entity."""

    _attr_available = False
    _state: str = STATE_NOT_HOME

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
    def latitude(self) -> float | None:
        """Returns None for latitude, as PetWALK has no GPS."""
        return None

    @property
    def longitude(self) -> float | None:
        """Returns None for longitude, as PetWALK has no GPS."""
        return None

    @property
    def source_type(self) -> SourceType | str:
        """Returns the source type."""
        return SourceType.ROUTER

    @property
    def location_name(self) -> str:
        """Returns the current state."""
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

            if event.direction == EVENT_DIRECTION_IN:
                self._state = STATE_HOME
            elif event.direction == EVENT_DIRECTION_OUT:
                self._state = STATE_NOT_HOME
            else:
                raise UpdateFailed(
                    f"""Incorrect Direction found for {self._name} ({self._pet_id}):
                    {event.direction}"""
                )

            self.async_write_ha_state()
