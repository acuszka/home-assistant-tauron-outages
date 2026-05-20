"""Binary sensors for Tauron outages."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import periods_attributes
from .coordinator import TauronOutagesCoordinator
from .entity import TauronOutagesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tauron outage binary sensors."""

    coordinator: TauronOutagesCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities([TauronOutageActiveBinarySensor(coordinator)])


class TauronOutageActiveBinarySensor(TauronOutagesEntity, BinarySensorEntity):
    """Binary sensor showing whether the configured street has a current outage."""

    _attr_name = "Outage active"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: TauronOutagesCoordinator) -> None:
        """Initialize the binary sensor."""

        super().__init__(coordinator, "outage_active")

    @property
    def is_on(self) -> bool:
        """Return true when a current matching outage exists."""

        return bool(self.coordinator.data and self.coordinator.data.active)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return matching current outage details."""

        return {
            "current_outages": periods_attributes(self.coordinator.data.current)
            if self.coordinator.data
            else []
        }
