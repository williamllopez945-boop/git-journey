import unittest

from trading_agent.income_institutional_flow import (
    average_trailing_volume,
    volume_surge_confirmed,
)


class TestAverageTrailingVolume(unittest.TestCase):
    def test_none_when_not_warmed_up(self):
        volumes = [100] * 20
        self.assertIsNone(average_trailing_volume(volumes, lookback_days=20))

    def test_none_on_zero_trailing_average(self):
        volumes = [0] * 20 + [500]
        self.assertIsNone(average_trailing_volume(volumes, lookback_days=20))

    def test_excludes_todays_volume(self):
        volumes = [100] * 20 + [100000]
        self.assertAlmostEqual(average_trailing_volume(volumes, lookback_days=20), 100.0)

    def test_uses_only_trailing_window(self):
        volumes = [9999] + [100] * 5 + [1]
        self.assertAlmostEqual(average_trailing_volume(volumes, lookback_days=5), 100.0)


class TestVolumeSurgeConfirmed(unittest.TestCase):
    def test_false_when_not_warmed_up(self):
        volumes = [100] * 20
        self.assertFalse(volume_surge_confirmed(volumes, lookback_days=20))

    def test_false_on_ordinary_volume(self):
        volumes = [100] * 20 + [110]
        self.assertFalse(volume_surge_confirmed(volumes, lookback_days=20, surge_multiple=1.5))

    def test_true_at_exact_multiple_boundary(self):
        volumes = [100] * 20 + [150]
        self.assertTrue(volume_surge_confirmed(volumes, lookback_days=20, surge_multiple=1.5))

    def test_true_on_clear_surge(self):
        volumes = [100] * 20 + [1000]
        self.assertTrue(volume_surge_confirmed(volumes, lookback_days=20, surge_multiple=1.5))

    def test_false_on_zero_trailing_average(self):
        volumes = [0] * 20 + [500]
        self.assertFalse(volume_surge_confirmed(volumes, lookback_days=20))


if __name__ == "__main__":
    unittest.main()
