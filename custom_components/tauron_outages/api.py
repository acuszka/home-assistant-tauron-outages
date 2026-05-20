"""Client and parsing helpers for Tauron outage data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
from typing import Any

try:
    from aiohttp import ClientError, ClientSession
except ModuleNotFoundError:  # pragma: no cover - Home Assistant provides aiohttp.
    class ClientError(Exception):
        """Fallback used only by parser tests outside Home Assistant."""

    ClientSession = Any

BASE_URL = "https://www.tauron-dystrybucja.pl"


class TauronApiError(Exception):
    """Raised when Tauron data cannot be fetched or parsed."""


@dataclass(frozen=True)
class TauronLocation:
    """Resolved Tauron city or street location."""

    name: str
    gaid: str
    province_name: str | None = None
    district_name: str | None = None


@dataclass(frozen=True)
class OutagePeriod:
    """Normalized Tauron outage period."""

    start: datetime | None
    end: datetime | None
    outage_type: str
    message: str
    raw_outage_type: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class OutageData:
    """Filtered outage data for one configured street."""

    current: tuple[OutagePeriod, ...]
    future: tuple[OutagePeriod, ...]
    raw_current_count: int
    raw_future_count: int

    @property
    def active(self) -> bool:
        """Return true when a current outage matches the configured street."""

        return bool(self.current)

    @property
    def next_outage(self) -> OutagePeriod | None:
        """Return the next matching outage, preferring current periods."""

        periods = [*self.current, *self.future]
        periods.sort(key=lambda period: period.start or datetime.max)
        return periods[0] if periods else None


def normalize_street(value: str) -> str:
    """Normalize a street name or outage message for street matching."""

    text = (value or "").replace("Ł", "L").replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"\b(ulica|ul|aleja|al|plac|pl|osiedle|os)\.?\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def message_mentions_street(message: str, street_name: str) -> bool:
    """Return true when an outage message names the configured street."""

    normalized_message = normalize_street(message)
    normalized_street = normalize_street(street_name)

    if not normalized_message or not normalized_street:
        return False

    for variant in _street_variants(normalized_street):
        pattern = rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])"
        if re.search(pattern, normalized_message) is not None:
            return True
    return False


def _street_variants(normalized_street: str) -> set[str]:
    """Return conservative Polish adjective inflection variants for matching."""

    variants = {normalized_street}
    if normalized_street.endswith("a"):
        variants.add(f"{normalized_street[:-1]}ej")
        variants.add(f"{normalized_street[:-1]}iej")
    return variants


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_period(raw: dict[str, Any]) -> OutagePeriod:
    """Parse one Tauron outage period."""

    raw_type = raw.get("OutageType")
    outage_type: str

    try:
        raw_type_int = int(raw_type)
    except (TypeError, ValueError):
        raw_type_int = None

    if raw_type_int == 2:
        outage_type = "emergency"
    else:
        outage_type = "planned"

    return OutagePeriod(
        start=_parse_datetime(raw.get("StartDate")),
        end=_parse_datetime(raw.get("EndDate")),
        outage_type=outage_type,
        message=str(raw.get("Message") or ""),
        raw_outage_type=raw_type_int,
        raw=raw,
    )


def parse_outage_data(payload: dict[str, Any], street_name: str) -> OutageData:
    """Parse and filter Tauron outage payload for the configured street."""

    raw_current = payload.get("CurrentOutagePeriods") or []
    raw_future = payload.get("FutureOutagePeriods") or []

    if not isinstance(raw_current, list) or not isinstance(raw_future, list):
        raise TauronApiError("Unexpected Tauron outage response shape")

    def matching_periods(periods: list[Any]) -> tuple[OutagePeriod, ...]:
        parsed: list[OutagePeriod] = []
        for item in periods:
            if not isinstance(item, dict):
                continue
            period = parse_period(item)
            if message_mentions_street(period.message, street_name):
                parsed.append(period)
        return tuple(parsed)

    return OutageData(
        current=matching_periods(raw_current),
        future=matching_periods(raw_future),
        raw_current_count=len(raw_current),
        raw_future_count=len(raw_future),
    )


class TauronOutagesClient:
    """Minimal async client for Tauron outage endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client."""

        self._session = session

    async def _get_json(self, path: str, params: dict[str, str]) -> Any:
        url = f"{BASE_URL}{path}"

        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise TauronApiError(f"Could not fetch Tauron data from {path}") from err

    async def async_get_cities(self, name: str) -> list[TauronLocation]:
        """Return city matches for a user-entered name."""

        data = await self._get_json("/iapi/city/GetCities", {"partName": name})
        if not isinstance(data, list):
            raise TauronApiError("Unexpected Tauron city response shape")

        return [_location_from_payload(item) for item in data if isinstance(item, dict)]

    async def async_get_streets(self, city_gaid: str, name: str) -> list[TauronLocation]:
        """Return street matches for a city GAID and user-entered street."""

        data = await self._get_json(
            "/iapi/street/GetStreets",
            {"ownerGaid": city_gaid, "partName": name},
        )
        if not isinstance(data, list):
            raise TauronApiError("Unexpected Tauron street response shape")

        return [_location_from_payload(item) for item in data if isinstance(item, dict)]

    async def async_get_outages(self, street_gaid: str, street_name: str) -> OutageData:
        """Return matching outage data for a resolved street."""

        data = await self._get_json(
            "/iapi/outage/GetOutages",
            {"gaid": street_gaid, "type": "street"},
        )
        if not isinstance(data, dict):
            raise TauronApiError("Unexpected Tauron outage response shape")

        if data.get("status") is False:
            return OutageData((), (), 0, 0)

        return parse_outage_data(data, street_name)


def _location_from_payload(item: dict[str, Any]) -> TauronLocation:
    return TauronLocation(
        name=str(item.get("Name") or ""),
        gaid=str(item.get("Gaid") or ""),
        province_name=item.get("ProvinceName"),
        district_name=item.get("DistrictName"),
    )
