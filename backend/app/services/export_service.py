import csv
import io
from typing import List, Dict, Any

def generate_evaluation_csv(aligned_intervals: List[Dict[str, Any]]) -> str:
    """
    Generate CSV data matching the exact dashboard evaluation interval table.
    Explicitly handles missing values as empty strings ('') with clear status flags,
    never converting missing values silently to zero.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    
    headers = [
        "delivery_time_utc",
        "display_time_london",
        "settlement_date",
        "settlement_period",
        "status",
        "actual_generation_mw",
        "selected_forecast_mw",
        "error_mw",
        "abs_error_mw",
        "selected_publish_time_utc",
        "lead_time_hours"
    ]
    writer.writerow(headers)

    for it in aligned_intervals:
        writer.writerow([
            it["delivery_time"],
            it["display_time_london"],
            it.get("settlement_date", ""),
            it.get("settlement_period", "") if it.get("settlement_period") is not None else "",
            it["status"],
            f"{it['actual_mw']:.2f}" if it["actual_mw"] is not None else "",
            f"{it['forecast_mw']:.2f}" if it["forecast_mw"] is not None else "",
            f"{it['error_mw']:.2f}" if it["error_mw"] is not None else "",
            f"{it['abs_error_mw']:.2f}" if it["abs_error_mw"] is not None else "",
            it.get("selected_publish_time", ""),
            f"{it['lead_time_hours']:.2f}" if it.get("lead_time_hours") is not None else ""
        ])

    return output.getvalue()
