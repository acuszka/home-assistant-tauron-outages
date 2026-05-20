"""Shared entity base for Tauron outages."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOUSE_NUMBER,
    CONF_RESOLVED_CITY,
    CONF_RESOLVED_STREET,
    CONF_STREET_GAID,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import TauronOutagesCoordinator


class TauronOutagesEntity(CoordinatorEntity[TauronOutagesCoordinator]):
    """Base entity for Tauron outages."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TauronOutagesCoordinator, key: str) -> None:
        """Initialize the entity."""

        super().__init__(coordinator)
        entry: ConfigEntry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_STREET_GAID])},
            manufacturer=MANUFACTURER,
            name=f"{entry.data[CONF_RESOLVED_CITY]} {entry.data[CONF_RESOLVED_STREET]} {entry.data[CONF_HOUSE_NUMBER]}",
        )

