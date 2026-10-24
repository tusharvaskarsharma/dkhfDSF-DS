from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional, Tuple

LONDON_TZ = ZoneInfo("Europe/London")
UTC_TZ = timezone.utc

def parse_utc_iso(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp string into a timezone-aware UTC datetime."""
    if not ts:
        raise ValueError("Timestamp string cannot be empty")
    ts_clean = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_clean)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(UTC_TZ)

def format_utc_iso(dt: datetime) -> str:
    """Format a datetime into a standard UTC ISO 8601 string with trailing 'Z'."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    utc_dt = dt.astimezone(UTC_TZ)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def to_london(dt: datetime) -> datetime:
    """Convert any aware datetime to Europe/London timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    return dt.astimezone(LONDON_TZ)

def format_london_display(dt: datetime, include_seconds: bool = False) -> str:
    """Format a datetime into a clear Europe/London representation including timezone name (GMT/BST)."""
    ldn = to_london(dt)
    tz_abbr = ldn.strftime("%Z")
    time_fmt = "%Y-%m-%d %H:%M:%S" if include_seconds else "%Y-%m-%d %H:%M"
    return f"{ldn.strftime(time_fmt)} {tz_abbr}"

def get_settlement_day_bounds_utc(settlement_date_str: str) -> Tuple[datetime, datetime]:
    """
    Given a UK settlement date 'YYYY-MM-DD', determine the exact UTC start and end bounds.
    In the UK power market, a settlement day starts at 00:00:00 local London time
    and ends at 24:00:00 local London time.
    """
    y, m, d = [int(p) for p in settlement_date_str.split("-")]
    # Start of day in London local time
    ldn_start = datetime(y, m, d, 0, 0, 0, tzinfo=LONDON_TZ)
    utc_start = ldn_start.astimezone(UTC_TZ)
    
    # End of day is start of next day
    next_day = date(y, m, d) + timedelta(days=1)
    ldn_end = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0, tzinfo=LONDON_TZ)
    utc_end = ldn_end.astimezone(UTC_TZ)
    
    return utc_start, utc_end

def get_settlement_period_count_for_date(settlement_date_str: str) -> int:
    """
    Returns the expected number of 30-minute settlement periods for a UK settlement date:
    - 48 for standard days (24 hours)
    - 46 for spring clock-forward transition (23 hours)
    - 50 for autumn clock-back transition (25 hours)
    """
    utc_start, utc_end = get_settlement_day_bounds_utc(settlement_date_str)
    duration_minutes = int((utc_end - utc_start).total_seconds() / 60)
    return duration_minutes // 30

def generate_settlement_periods_for_date(settlement_date_str: str) -> List[Dict]:
    """
    Generate all expected half-hourly settlement periods for a settlement date.
    Each item contains:
      - settlement_date: 'YYYY-MM-DD'
      - settlement_period: int (1..48 / 46 / 50)
      - start_time_utc: ISO string
      - end_time_utc: ISO string
      - display_london_start: human readable London time
      - display_london_end: human readable London time
    """
    utc_start, utc_end = get_settlement_day_bounds_utc(settlement_date_str)
    periods = []
    current_utc = utc_start
    sp_index = 1
    
    while current_utc < utc_end:
        next_utc = current_utc + timedelta(minutes=30)
        periods.append({
            "settlement_date": settlement_date_str,
            "settlement_period": sp_index,
            "start_time_utc": format_utc_iso(current_utc),
            "end_time_utc": format_utc_iso(next_utc),
            "display_london_start": format_london_display(current_utc),
            "display_london_end": format_london_display(next_utc),
        })
        current_utc = next_utc
        sp_index += 1
        
    return periods

def generate_expected_intervals_in_range(date_from_str: str, date_to_str: str) -> List[Dict]:
    """Generate all expected half-hour delivery intervals across [date_from, date_to] inclusive."""
    d_start = date.fromisoformat(date_from_str)
    d_end = date.fromisoformat(date_to_str)
    if d_end < d_start:
        raise ValueError("date_to must be >= date_from")
        
    all_periods = []
    curr = d_start
    while curr <= d_end:
        all_periods.extend(generate_settlement_periods_for_date(curr.isoformat()))
        curr += timedelta(days=1)
    return all_periods
