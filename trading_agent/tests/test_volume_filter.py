import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.volume_filter import average_volume, passes_volume_filter


def test_average_volume_none_when_insufficient_history():
    assert average_volume([100] * 10, period=14) is None


def test_average_volume_excludes_current_bar():
    # 14 bars of 100, then a current bar of 1000 - average must be 100,
    # not pulled up by the current bar itself.
    volumes = [100] * 14 + [1000]
    assert average_volume(volumes, period=14) == 100.0


def test_passes_volume_filter_true_when_not_enough_history():
    assert passes_volume_filter([100] * 5, period=14) is True


def test_passes_volume_filter_blocks_below_ratio():
    volumes = [100] * 14 + [150]  # 1.5x average
    assert passes_volume_filter(volumes, period=14, min_ratio=2.0) is False


def test_passes_volume_filter_allows_at_or_above_ratio():
    volumes = [100] * 14 + [200]  # exactly 2.0x average
    assert passes_volume_filter(volumes, period=14, min_ratio=2.0) is True


def test_passes_volume_filter_true_when_average_is_zero():
    volumes = [0] * 14 + [50]
    assert passes_volume_filter(volumes, period=14, min_ratio=1.0) is True
