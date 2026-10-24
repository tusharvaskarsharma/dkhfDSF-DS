from typing import List, Dict, Optional, Any
from app.core.time_utils import (
    parse_utc_iso,
    format_utc_iso,
    format_london_display,
    generate_expected_intervals_in_range
)
from datetime import timedelta

def align_forecast_and_actuals(
    expected_intervals: List[Dict[str, Any]],
    actual_records: List[Dict[str, Any]],
    selected_forecasts_by_hour: Dict[str, Dict[str, Any]],
    granularity: str = "half_hourly"
) -> List[Dict[str, Any]]:
    """
    Align actual generation records with selected forecasts across all expected intervals.
    
    In UK market data:
    - FUELHH actuals are reported half-hourly per settlement period (e.g. 00:00, 00:30, 01:00...).
    - WINDFOR forecasts are published hourly (e.g. 00:00, 01:00, 02:00...).
    
    For half-hourly alignment:
      Each half-hour (SP 2k-1 and SP 2k) is matched to the hourly forecast covering it.
      (e.g., 00:00 and 00:30 both look up forecast at 00:00:00Z).
      
    For hourly alignment:
      Half-hours are grouped into 1-hour delivery intervals. Actual generation is the average MW
      across the two half-hours in that hour.
    """
    # Index actual records by delivery_time
    actual_map: Dict[str, Dict[str, Any]] = {}
    for a in actual_records:
        actual_map[a["delivery_time"]] = a

    if granularity == "hourly":
        return _align_hourly(expected_intervals, actual_map, selected_forecasts_by_hour)
    else:
        return _align_half_hourly(expected_intervals, actual_map, selected_forecasts_by_hour)

def _align_half_hourly(
    expected_intervals: List[Dict[str, Any]],
    actual_map: Dict[str, Dict[str, Any]],
    selected_forecasts_by_hour: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    aligned = []
    
    for interval in expected_intervals:
        deliv_utc_str = interval["start_time_utc"]
        deliv_dt = parse_utc_iso(deliv_utc_str)
        
        # Determine the parent hour for WINDFOR forecast lookup
        hour_dt = deliv_dt.replace(minute=0, second=0, microsecond=0)
        hour_utc_str = format_utc_iso(hour_dt)

        actual_rec = actual_map.get(deliv_utc_str)
        forecast_rec = selected_forecasts_by_hour.get(hour_utc_str)

        actual_mw = float(actual_rec["generation_mw"]) if actual_rec else None
        forecast_mw = float(forecast_rec["generation_mw"]) if forecast_rec else None

        has_actual = actual_mw is not None
        has_forecast = forecast_mw is not None

        if has_actual and has_forecast:
            status = "VALID"
            error_mw = round(actual_mw - forecast_mw, 2)
            abs_error_mw = round(abs(error_mw), 2)
        elif has_actual and not has_forecast:
            status = "MISSING_FORECAST"
            error_mw = None
            abs_error_mw = None
        elif not has_actual and has_forecast:
            status = "MISSING_ACTUAL"
            error_mw = None
            abs_error_mw = None
        else:
            status = "MISSING_BOTH"
            error_mw = None
            abs_error_mw = None

        lead_time_hours = forecast_rec.get("lead_time_hours") if forecast_rec else None
        selected_pub_time = forecast_rec.get("publish_time") if forecast_rec else None

        aligned.append({
            "delivery_time": deliv_utc_str,
            "display_time_london": interval["display_london_start"],
            "settlement_date": interval["settlement_date"],
            "settlement_period": interval["settlement_period"],
            "actual_mw": actual_mw,
            "forecast_mw": forecast_mw,
            "error_mw": error_mw,
            "abs_error_mw": abs_error_mw,
            "selected_publish_time": selected_pub_time,
            "lead_time_hours": lead_time_hours,
            "status": status
        })

    return aligned

def _align_hourly(
    expected_intervals: List[Dict[str, Any]],
    actual_map: Dict[str, Dict[str, Any]],
    selected_forecasts_by_hour: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    # Group half-hourly expected intervals into unique hours
    hours_seen = set()
    aligned = []

    for interval in expected_intervals:
        deliv_dt = parse_utc_iso(interval["start_time_utc"])
        hour_dt = deliv_dt.replace(minute=0, second=0, microsecond=0)
        hour_utc_str = format_utc_iso(hour_dt)
        
        if hour_utc_str in hours_seen:
            continue
        hours_seen.add(hour_utc_str)

        # Look up both half-hours for actuals
        hh1_str = hour_utc_str
        hh2_dt = hour_dt + timedelta(minutes=30)
        hh2_str = format_utc_iso(hh2_dt)

        act1 = actual_map.get(hh1_str)
        act2 = actual_map.get(hh2_str)

        actual_vals = []
        if act1:
            actual_vals.append(float(act1["generation_mw"]))
        if act2:
            actual_vals.append(float(act2["generation_mw"]))

        actual_mw = round(sum(actual_vals) / len(actual_vals), 2) if actual_vals else None
        
        forecast_rec = selected_forecasts_by_hour.get(hour_utc_str)
        forecast_mw = float(forecast_rec["generation_mw"]) if forecast_rec else None

        has_actual = actual_mw is not None
        has_forecast = forecast_mw is not None

        if has_actual and has_forecast:
            status = "VALID"
            error_mw = round(actual_mw - forecast_mw, 2)
            abs_error_mw = round(abs(error_mw), 2)
        elif has_actual and not has_forecast:
            status = "MISSING_FORECAST"
            error_mw = None
            abs_error_mw = None
        elif not has_actual and has_forecast:
            status = "MISSING_ACTUAL"
            error_mw = None
            abs_error_mw = None
        else:
            status = "MISSING_BOTH"
            error_mw = None
            abs_error_mw = None

        lead_time_hours = forecast_rec.get("lead_time_hours") if forecast_rec else None
        selected_pub_time = forecast_rec.get("publish_time") if forecast_rec else None

        aligned.append({
            "delivery_time": hour_utc_str,
            "display_time_london": format_london_display(hour_dt),
            "settlement_date": interval["settlement_date"],
            "settlement_period": interval["settlement_period"], # SP of first half-hour
            "actual_mw": actual_mw,
            "forecast_mw": forecast_mw,
            "error_mw": error_mw,
            "abs_error_mw": abs_error_mw,
            "selected_publish_time": selected_pub_time,
            "lead_time_hours": lead_time_hours,
            "status": status
        })

    return aligned
