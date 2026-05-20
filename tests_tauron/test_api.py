from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import unittest

_API_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "tauron_outages"
    / "api.py"
)

_SPEC = spec_from_file_location("tauron_outages_api", _API_PATH)
assert _SPEC is not None
api = module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = api
_SPEC.loader.exec_module(api)

message_mentions_street = api.message_mentions_street
normalize_street = api.normalize_street
parse_outage_data = api.parse_outage_data


class TauronApiTests(unittest.TestCase):
    def test_normalize_street_removes_prefix_and_diacritics(self):
        self.assertEqual(normalize_street("ul. Długa"), "dluga")
        self.assertEqual(normalize_street("Aleja Jana Pawła II"), "jana pawla ii")

    def test_message_mentions_whole_street_name_only(self):
        self.assertTrue(message_mentions_street("Planowane: ul. Długa 1-10", "Długa"))
        self.assertTrue(message_mentions_street("Prace przy ulicy Podgórskiej", "Podgórska"))
        self.assertFalse(message_mentions_street("Prace przy ulicy Nadługa", "Długa"))

    def test_parse_outage_data_filters_nearby_area_rows(self):
        data = parse_outage_data(
            {
                "CurrentOutagePeriods": [
                    {
                        "StartDate": "2026-05-20T08:00:00",
                        "EndDate": "2026-05-20T10:00:00",
                        "OutageType": 2,
                        "Message": "Kraków ul. Długa od 1 do 10",
                    },
                    {
                        "StartDate": "2026-05-20T09:00:00",
                        "EndDate": "2026-05-20T12:00:00",
                        "OutageType": 1,
                        "Message": "Kraków ul. Krótka",
                    },
                ],
                "FutureOutagePeriods": [
                    {
                        "StartDate": "2026-05-21T08:00:00",
                        "EndDate": "2026-05-21T10:00:00",
                        "OutageType": 1,
                        "Message": "Kraków ul. Długa",
                    }
                ],
            },
            "Długa",
        )

        self.assertTrue(data.active)
        self.assertEqual(data.raw_current_count, 2)
        self.assertEqual(data.raw_future_count, 1)
        self.assertEqual(len(data.current), 1)
        self.assertEqual(len(data.future), 1)
        self.assertEqual(data.current[0].outage_type, "emergency")
        self.assertEqual(data.current[0].start, datetime(2026, 5, 20, 8, 0))

    def test_parse_outage_data_returns_inactive_when_only_nearby_rows_exist(self):
        data = parse_outage_data(
            {
                "CurrentOutagePeriods": [
                    {
                        "StartDate": "2026-05-20T08:00:00",
                        "EndDate": "2026-05-20T10:00:00",
                        "OutageType": 2,
                        "Message": "Kraków ul. Krótka",
                    }
                ],
                "FutureOutagePeriods": [],
            },
            "Długa",
        )

        self.assertFalse(data.active)
        self.assertEqual(len(data.current), 0)


if __name__ == "__main__":
    unittest.main()
