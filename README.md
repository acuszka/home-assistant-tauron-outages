# Tauron Outages for Home Assistant

Home Assistant custom integration for checking Tauron Dystrybucja power outages
and planned electricity shutdowns for a configured address in Poland.

## What It Does

- Resolves a configured city and street using Tauron's public autocomplete API.
- Polls Tauron's outage endpoint every 6 hours by default.
- Treats Tauron results as area-level candidates.
- Marks the address as impacted only when an outage row mentions the configured
  street name.
- Ignores nearby outages that do not mention the configured street.

The house number is stored and shown as part of the configured address, but
matching is street-level because Tauron's outage lookup endpoint does not appear
to submit the house number.

## Entities

- Binary sensor: `Outage active`
- Sensor: `Current outages`
- Sensor: `Future outages`
- Sensor: `Next outage`
- Sensor: `Last update`

The current/future count sensors expose matching outage details in attributes.
Non-matching nearby outages returned by Tauron are not exposed.

## Installation With HACS

1. Add this repository as a custom HACS integration repository:
   `https://github.com/acuszka/home-assistant-tauron-outages`
2. Install `Tauron Outages`.
3. Restart Home Assistant.
4. Add the integration from Settings -> Devices & services.
5. Enter city, street, and house number.

## Manual Installation

Copy `custom_components/tauron_outages` into your Home Assistant
`config/custom_components/` directory, restart Home Assistant, then add
`Tauron Outages` from Settings -> Devices & services.

## Development

Run focused tests:

```sh
pytest tests_tauron
```
