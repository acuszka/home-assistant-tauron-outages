"""Config flow for Tauron Outages."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, TextSelector

from .api import TauronApiError, TauronLocation, TauronOutagesClient
from .const import (
    CONF_CITY,
    CONF_CITY_GAID,
    CONF_HOUSE_NUMBER,
    CONF_RESOLVED_CITY,
    CONF_RESOLVED_STREET,
    CONF_STREET,
    CONF_STREET_GAID,
    DOMAIN,
)


class TauronOutagesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tauron Outages."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._client: TauronOutagesClient | None = None
        self._user_input: dict[str, str] = {}
        self._cities: list[TauronLocation] = []
        self._streets: list[TauronLocation] = []

    @property
    def client(self) -> TauronOutagesClient:
        """Return the Tauron client."""

        if self._client is None:
            self._client = TauronOutagesClient(async_get_clientsession(self.hass))
        return self._client

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input = dict(user_input)
            try:
                self._cities = await self.client.async_get_cities(user_input[CONF_CITY])
            except TauronApiError:
                errors["base"] = "cannot_connect"
            else:
                if not self._cities:
                    errors[CONF_CITY] = "not_found"
                elif len(self._cities) == 1:
                    return await self._resolve_streets(self._cities[0])
                else:
                    return await self.async_step_city()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): TextSelector(),
                    vol.Required(CONF_STREET): TextSelector(),
                    vol.Required(CONF_HOUSE_NUMBER): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_city(
        self, user_input: dict[str, str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle city selection when Tauron returns multiple matches."""

        if user_input is not None:
            city = self._location_by_gaid(self._cities, user_input[CONF_CITY_GAID])
            return await self._resolve_streets(city)

        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY_GAID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": city.gaid, "label": _location_label(city)}
                                for city in self._cities
                            ]
                        )
                    )
                }
            ),
        )

    async def async_step_street(
        self, user_input: dict[str, str] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle street selection when Tauron returns multiple matches."""

        if user_input is not None:
            street = self._location_by_gaid(self._streets, user_input[CONF_STREET_GAID])
            city = self._location_by_gaid(self._cities, self._user_input[CONF_CITY_GAID])
            return await self._create_entry(city, street)

        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STREET_GAID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {
                                    "value": street.gaid,
                                    "label": _location_label(street),
                                }
                                for street in self._streets
                            ]
                        )
                    )
                }
            ),
        )

    async def _resolve_streets(
        self, city: TauronLocation
    ) -> config_entries.ConfigFlowResult:
        self._user_input[CONF_CITY_GAID] = city.gaid

        try:
            self._streets = await self.client.async_get_streets(
                city.gaid,
                self._user_input[CONF_STREET],
            )
        except TauronApiError:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_CITY, default=self._user_input[CONF_CITY]): TextSelector(),
                        vol.Required(CONF_STREET, default=self._user_input[CONF_STREET]): TextSelector(),
                        vol.Required(
                            CONF_HOUSE_NUMBER,
                            default=self._user_input[CONF_HOUSE_NUMBER],
                        ): TextSelector(),
                    }
                ),
                errors={"base": "cannot_connect"},
            )

        if not self._streets:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_CITY, default=self._user_input[CONF_CITY]): TextSelector(),
                        vol.Required(CONF_STREET, default=self._user_input[CONF_STREET]): TextSelector(),
                        vol.Required(
                            CONF_HOUSE_NUMBER,
                            default=self._user_input[CONF_HOUSE_NUMBER],
                        ): TextSelector(),
                    }
                ),
                errors={CONF_STREET: "not_found"},
            )

        if len(self._streets) == 1:
            return await self._create_entry(city, self._streets[0])

        return await self.async_step_street()

    async def _create_entry(
        self,
        city: TauronLocation,
        street: TauronLocation,
    ) -> config_entries.ConfigFlowResult:
        unique_id = f"{city.gaid}_{street.gaid}_{self._user_input[CONF_HOUSE_NUMBER]}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        data = {
            CONF_CITY: self._user_input[CONF_CITY],
            CONF_STREET: self._user_input[CONF_STREET],
            CONF_HOUSE_NUMBER: self._user_input[CONF_HOUSE_NUMBER],
            CONF_CITY_GAID: city.gaid,
            CONF_STREET_GAID: street.gaid,
            CONF_RESOLVED_CITY: city.name,
            CONF_RESOLVED_STREET: street.name,
        }

        return self.async_create_entry(
            title=f"{city.name}, {street.name} {self._user_input[CONF_HOUSE_NUMBER]}",
            data=data,
        )

    @staticmethod
    def _location_by_gaid(
        locations: list[TauronLocation],
        gaid: str,
    ) -> TauronLocation:
        return next(location for location in locations if location.gaid == gaid)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""

        return TauronOutagesOptionsFlow(config_entry)


class TauronOutagesOptionsFlow(config_entries.OptionsFlow):
    """Options flow placeholder."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show empty options flow."""

        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))


def _location_label(location: TauronLocation) -> str:
    parts = [location.name]
    details = ", ".join(
        part for part in (location.district_name, location.province_name) if part
    )
    if details:
        parts.append(f"({details})")
    return " ".join(parts)
