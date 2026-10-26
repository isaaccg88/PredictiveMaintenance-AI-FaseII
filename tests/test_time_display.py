"""Regression tests for the dashboard's timestamp presentation."""
import unittest

from app.time_display import format_request_local, format_simulated_utc


class TimeDisplayTests(unittest.TestCase):
    def test_utc_midnight_date_shift_in_mexico(self):
        self.assertEqual(
            format_request_local("2026-10-26T05:46:25.764592+00:00"),
            "25/10/2026 23:46:25",
        )

    def test_explicit_z_offset(self):
        self.assertEqual(
            format_request_local("2026-10-26T06:00:00Z"),
            "26/10/2026 00:00:00",
        )

    def test_simulated_reading_remains_utc(self):
        self.assertEqual(
            format_simulated_utc("2026-06-24T18:00:00+00:00"),
            "24/06/2026 18:00:00 UTC",
        )

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            format_request_local("2026-10-26T05:46:25")


if __name__ == "__main__":
    unittest.main()
