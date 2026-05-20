"""Sensors for Tauron outages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import period_attributes, periods_attributes
from .coordinator import TauronOutagesCoordinator
from .entity import TauronOutagesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tauron outage sensors."""

    coordinator: TauronOutagesCoordinator = hass.data[entry.domain][entry.entry_id]
    async_add_entities(
        [
            TauronCurrentOutagesSensor(coordinator),
            TauronFutureOutagesSensor(coordinator),
            TauronNextOutageSensor(coordinator),
            TauronLastUpdateSensor(coordinator),
        ]
    )


class TauronCurrentOutagesSensor(TauronOutagesEntity, SensorEntity):
    """Sensor with matching current outage count."""

    _attr_name = "Current outages"
    _attr_native_unit_of_measurement = "outages"

    def __init__(self, coordinator: TauronOutagesCoordinator) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, "current_outages")

    @property
    def native_value(self) -> int:
        """Return matching current outage count."""

        return len(self.coordinator.data.current) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return matching current outage details."""

        return {
            "outages": periods_attributes(self.coordinator.data.current)
            if self.coordinator.data
            else []
        }


class TauronFutureOutagesSensor(TauronOutagesEntity, SensorEntity):
    """Sensor with matching future outage count."""

    _attr_name = "Future outages"
    _attr_native_unit_of_measurement = "outages"

    def __init__(self, coordinator: TauronOutagesCoordinator) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, "future_outages")

    @property
    def native_value(self) -> int:
        """Return matching future outage count."""

        return len(self.coordinator.data.future) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return matching future outage details."""

        return {
            "outages": periods_attributes(self.coordinator.data.future)
            if self.coordinator.data
            else []
        }


class TauronNextOutageSensor(TauronOutagesEntity, SensorEntity):
    """Sensor with the next matching outage start time."""

    _attr_name = "Next outage"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: TauronOutagesCoordinator) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, "next_outage")

    @property
    def native_value(self) -> datetime | None:
        """Return the next matching outage start time."""

        period = self.coordinator.data.next_outage if self.coordinator.data else None
        return period.start if period else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return next outage details."""

        period = self.coordinator.data.next_outage if self.coordinator.data else None
        return period_attributes(period)


class TauronLastUpdateSensor(TauronOutagesEntity, SensorEntity):
    """Sensor showing the last successful coordinator refresh."""

    _attr_name = "Last update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: TauronOutagesCoordinator) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, "last_update")

    @property
    def native_value(self) -> datetime | None:
        """Return the last successful update time."""

        return self.coordinator.last_successful_update
