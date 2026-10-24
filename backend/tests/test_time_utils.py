import pytest
from datetime import datetime, timezone
from app.core.time_utils import (
    parse_utc_iso,
    format_utc_iso,
    to_london,
    format_london_display,
    get_settlement_period_count_for_date,
    generate_settlement_periods_for_date,
    generate_expected_intervals_in_range
)

def test_parse_and_format_utc():
    ts = "2026-01-01T12:00:00Z"
    dt = parse_utc_iso(ts)
    assert dt.tzinfo is not None
    assert dt.hour == 12
    assert dt.day == 1
    assert format_utc_iso(dt) == ts

def test_london_timezone_conversions():
    # Winter (GMT, UTC+0)
    dt_winter = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
    disp_winter = format_london_display(dt_winter)
    assert "2026-01-15 14:30 GMT" == disp_winter

    # Summer (BST, UTC+1)
    dt_summer = datetime(2026, 7, 15, 14, 30, tzinfo=timezone.utc)
    disp_summer = format_london_display(dt_summer)
    assert "2026-07-15 15:30 BST" == disp_summer

def test_settlement_period_counts_normal_and_dst():
    # Normal Day: 48 periods
    assert get_settlement_period_count_for_date("2026-01-01") == 48
    assert get_settlement_period_count_for_date("2026-06-01") == 48

    # Spring Transition (Clock Forward, 23 hours): 46 periods
    assert get_settlement_period_count_for_date("2026-03-29") == 46

    # Autumn Transition (Clock Back, 25 hours): 50 periods
    assert get_settlement_period_count_for_date("2026-10-25") == 50

def test_generate_settlement_periods_continuity():
    periods = generate_settlement_periods_for_date("2026-01-01")
    assert len(periods) == 48
    assert periods[0]["settlement_period"] == 1
    assert periods[0]["start_time_utc"] == "2026-01-01T00:00:00Z"
    assert periods[-1]["settlement_period"] == 48
    assert periods[-1]["end_time_utc"] == "2026-01-02T00:00:00Z"

def test_generate_expected_intervals_in_range():
    # 3 days in January = 3 * 48 = 144 periods
    intervals = generate_expected_intervals_in_range("2026-01-01", "2026-01-03")
    assert len(intervals) == 144
    assert intervals[0]["settlement_date"] == "2026-01-01"
    assert intervals[-1]["settlement_date"] == "2026-01-03"
