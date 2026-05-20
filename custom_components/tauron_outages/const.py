"""Constants for the Tauron Outages integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "tauron_outages"

CONF_CITY = "city"
CONF_STREET = "street"
CONF_CITY_GAID = "city_gaid"
CONF_STREET_GAID = "street_gaid"
CONF_HOUSE_NUMBER = "house_number"
CONF_RESOLVED_CITY = "resolved_city"
CONF_RESOLVED_STREET = "resolved_street"

DEFAULT_SCAN_INTERVAL = timedelta(hours=6)

MANUFACTURER = "TAURON Dystrybucja"
