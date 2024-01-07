"""The PetWALK integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_INCLUDE_ALL_EVENTS,
    COORDINATOR,
    DEFAULT_INCLUDE_ALL_EVENTS,
    DOMAIN,
)
from .coordinator import PetwalkCoordinator

_LOGGER = logging.getLogger(__name__)

# Supported Platforms
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.DEVICE_TRACKER,
    Platform.COVER,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PetWALK from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Initialize our Coordinator
    coordinator = hass.data[DOMAIN][COORDINATOR] = hass.data[DOMAIN].get(
        COORDINATOR, PetwalkCoordinator(hass, entry)
    )
    await coordinator.initialize()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entry when its updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)

    if config_entry.version == 1:
        data = {**config_entry.data}
        data[CONF_INCLUDE_ALL_EVENTS] = DEFAULT_INCLUDE_ALL_EVENTS

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=data)

    _LOGGER.debug("Migration to version %d successful", config_entry.version)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)
