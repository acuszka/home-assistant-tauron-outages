"""Data update coordinator for Tauron outages."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import OutageData, TauronApiError, TauronOutagesClient
from .const import CONF_RESOLVED_STREET, CONF_STREET_GAID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TauronOutagesCoordinator(DataUpdateCoordinator[OutageData]):
    """Coordinator that polls Tauron outage data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""

        self.config_entry = entry
        self.client = TauronOutagesClient(async_get_clientsession(hass))
        self.last_successful_update: datetime | None = None

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> OutageData:
        """Fetch outage data from Tauron."""

        try:
            data = await self.client.async_get_outages(
                self.config_entry.data[CONF_STREET_GAID],
                self.config_entry.data[CONF_RESOLVED_STREET],
            )
            self.last_successful_update = dt_util.utcnow()
            return data
        except TauronApiError as err:
            raise UpdateFailed(str(err)) from err
