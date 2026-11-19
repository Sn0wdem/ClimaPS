from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from climaps.core.weather_api import _parse_point_payload
from climaps.ui_styles import format_datetime_friendly


class FormattingAndUiTests(unittest.TestCase):
    def test_format_datetime_friendly(self):
        # Test standard ISO string
        self.assertEqual(format_datetime_friendly("2026-11-19T16:00"), "19/11/2026 às 16:00")
        self.assertEqual(format_datetime_friendly("2026-11-19T16:00:00"), "19/11/2026 às 16:00")
        self.assertEqual(format_datetime_friendly("2026-11-19 16:00"), "19/11/2026 às 16:00")
        
        # Test Timestamp object
        ts = pd.Timestamp("2026-11-19 16:00")
        self.assertEqual(format_datetime_friendly(ts), "19/11/2026 às 16:00")

        # Test idempotence
        self.assertEqual(format_datetime_friendly("19/11/2026 às 16:00"), "19/11/2026 às 16:00")

        # Test null / empty
        self.assertEqual(format_datetime_friendly(None), "-")
        self.assertEqual(format_datetime_friendly(""), "-")
        self.assertEqual(format_datetime_friendly(pd.NaT), "-")

    def test_parse_point_payload_formats_horario(self):
        payload = {
            "latitude": -3.1,
            "longitude": -60.0,
            "timezone": "America/Manaus",
            "current": {
                "time": "2026-11-19T16:00",
                "temperature_2m": 32.5,
                "apparent_temperature": 38.0,
                "relative_humidity_2m": 75,
                "is_day": 1,
                "precipitation": 0.0,
                "weather_code": 0,
                "cloud_cover": 20,
                "pressure_msl": 1012,
                "wind_speed_10m": 12.0,
                "wind_gusts_10m": 18.0,
            },
            "daily": {
                "uv_index_max": [8.5],
                "sunrise": ["2026-11-19T05:45"],
                "sunset": ["2026-11-19T18:05"],
            },
        }
        res = _parse_point_payload(payload, "Manaus (BR)", -3.1, -60.0)
        self.assertEqual(res["horario"], "19/11/2026 às 16:00")
        self.assertEqual(res["local"], "Manaus (BR)")
        self.assertEqual(res["temperatura_c"], 32.5)


if __name__ == "__main__":
    unittest.main()
