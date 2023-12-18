"""Platform for PetWALK device tracker."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Final

from homeassistant import config_entries
from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SourceType,
    TrackerEntity,
)
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_HOME,
    STATE_NOT_HOME,
)
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
from pypetwalk.const import EVENT_DIRECTION_IN, EVENT_DIRECTION_OUT
from pypetwalk.exceptions import (
    PyPetWALKClientConnectionError,
    PyPetWALKInvalidResponseStatus,
)
import voluptuous as vol

from .const import DOMAIN

UPDATE_INTERVAL = timedelta(seconds=120)

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

    try:
        device_id = await api.get_device_id()
        device_name = await api.get_device_name()
        pets = await api.get_available_pets()
    except (PyPetWALKClientConnectionError, IndexError, KeyError) as err:
        raise ConfigEntryNotReady from err

    coordinator = DeviceTrackerCoordinator(hass, api, device_id)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entities = []
    if len(pets) > 0:
        for pet in pets:
            entities.append(
                PetDeviceTracker(
                    api,
                    coordinator,
                    pet_id=pet.id,
                    species=pet.species,
                    device_name=device_name,
                    entity_name=pet.name,
                    entity_id=f"pet_{pet.species.lower()}_{pet.name.lower()}",
                )
            )

    if len(entities) > 0:
        _LOGGER.info("Adding our Pet entities")
        add_entities(entities, True)


class DeviceTrackerCoordinator(DataUpdateCoordinator):
    """Base Class for Coordinator."""

    def __init__(self, hass, api, device_id):
        """Initialize Coordinator."""
        super().__init__(hass, _LOGGER, name="PetWALK", update_interval=UPDATE_INTERVAL)
        self._api = api
        self._device_id = device_id

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            async with asyncio.timeout(10):
                _LOGGER.info("Fetching Timeline Data")
                # return await self._api.get_timeline(self._device_id, 1)
                return await self._api.get_pet_status(self._device_id)
        except (PyPetWALKInvalidResponseStatus, PyPetWALKClientConnectionError) as err:
            raise UpdateFailed("Error communication with API") from err


class PetDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Pet Device Tracker Entity."""

    _attr_available = False

    def __init__(
        self,
        api: PyPetWALK,
        coordinator: DeviceTrackerCoordinator,
        pet_id: str,
        species: str,
        device_name: str,
        entity_name: str,
        entity_id: str,
    ):
        """Initialize the Device Tracker."""
        super().__init__(coordinator)

        self._api = api
        self._state = STATE_NOT_HOME
        self._pet_id = pet_id
        self._species = species
        self._device_name = device_name
        self._name = entity_name
        self._entity_id = entity_id
        self._lastCall = datetime.fromtimestamp(0)
        self._attr_extra_state_attributes = {"last_update": None}

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"petwalk_{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        """Return the name of the entity."""
        return f"PetWALK {self._device_name} {self._name}"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        return DeviceInfo(
            identifiers={("petwalk", self._device_name)},
            name=self._device_name,
            manufacturer="Petwalk Solutions GmbH",
        )

    @property
    def icon(self) -> str | None:
        """Return the icon of the device."""
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
    def location_name(self) -> str | None:
        """Returns the current state."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data

        if self._pet_id not in data:
            raise UpdateFailed(
                f"Unable to find current status for {self._name} ({self._pet_id})"
            )

        event = data[self._pet_id]

        self._attr_extra_state_attributes["last_update"] = event.date
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
