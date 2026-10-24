from typing import List, Dict, Optional, Any
from app.core.time_utils import parse_utc_iso, format_london_display
from datetime import datetime

def select_forecast_for_delivery(
    vintages: List[Dict[str, Any]],
    decision_cutoff: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Select the single eligible forecast for a delivery interval at the given decision cutoff.
    
    Rule:
    1. Filter vintages satisfying: publish_time <= decision_cutoff (if cutoff is provided).
    2. If no eligible records exist, return None (NO look-ahead leakage, NO silent fallback).
    3. Choose the record with the maximum publish_time.
    4. Deterministic tie-break rule:
       If multiple records have identical publish_time, select by:
       a) id descending (latest inserted ID)
       b) retrieval_time descending
    """
    if not vintages:
        return None

    cutoff_dt = parse_utc_iso(decision_cutoff) if decision_cutoff else None

    eligible = []
    for v in vintages:
        v_pub_dt = parse_utc_iso(v["publish_time"])
        if cutoff_dt is None or v_pub_dt <= cutoff_dt:
            eligible.append((v_pub_dt, v.get("id") or 0, v.get("retrieval_time", ""), v))

    if not eligible:
        return None

    # Sort descending by: publish_dt, id, retrieval_time
    eligible.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    
    selected_raw = eligible[0][3]
    deliv_dt = parse_utc_iso(selected_raw["delivery_time"])
    pub_dt = eligible[0][0]
    lead_time_hours = round((deliv_dt - pub_dt).total_seconds() / 3600.0, 2)

    selected = dict(selected_raw)
    selected["lead_time_hours"] = lead_time_hours
    selected["is_selected"] = True
    return selected

def select_forecasts_for_delivery_intervals(
    all_forecasts: List[Dict[str, Any]],
    decision_cutoff: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Group all forecast records by delivery_time, and apply vintage selection logic
    for each delivery interval.
    Returns: dict mapping delivery_time (ISO UTC) -> selected forecast dict.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for f in all_forecasts:
        grouped.setdefault(f["delivery_time"], []).append(f)

    selected_map: Dict[str, Dict[str, Any]] = {}
    for delivery_time, vintages in grouped.items():
        sel = select_forecast_for_delivery(vintages, decision_cutoff)
        if sel is not None:
            selected_map[delivery_time] = sel

    return selected_map

def build_vintage_evolution(
    delivery_time: str,
    vintages: List[Dict[str, Any]],
    decision_cutoff: Optional[str] = None,
    actual_record: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build complete audit of how the forecast evolved across publication runs for a delivery interval.
    Marks each vintage as:
      - is_eligible_before_cutoff: bool
      - is_selected: bool
      - lead_time_hours: float
    """
    selected = select_forecast_for_delivery(vintages, decision_cutoff)
    selected_pub_time = selected["publish_time"] if selected else None
    
    cutoff_dt = parse_utc_iso(decision_cutoff) if decision_cutoff else None
    deliv_dt = parse_utc_iso(delivery_time)

    # Sort all vintages chronologically by publish_time
    sorted_vintages = sorted(
        vintages,
        key=lambda v: (parse_utc_iso(v["publish_time"]), v.get("id") or 0)
    )

    items = []
    for v in sorted_vintages:
        v_pub_dt = parse_utc_iso(v["publish_time"])
        is_eligible = cutoff_dt is None or v_pub_dt <= cutoff_dt
        is_selected = (v["publish_time"] == selected_pub_time) if selected else False
        lead_hours = round((deliv_dt - v_pub_dt).total_seconds() / 3600.0, 2)
        
        items.append({
            "publish_time": v["publish_time"],
            "display_publish_london": format_london_display(v_pub_dt),
            "generation_mw": float(v["generation_mw"]),
            "lead_time_hours": lead_hours,
            "is_eligible_before_cutoff": is_eligible,
            "is_selected": is_selected
        })

    warning = None
    if not items:
        warning = "No forecast publication vintages recorded for this delivery interval."
    elif not selected:
        warning = f"No forecast published before the chosen cutoff ({decision_cutoff})."

    return {
        "delivery_time": delivery_time,
        "display_time_london": format_london_display(deliv_dt),
        "settlement_date": actual_record.get("settlement_date") if actual_record else None,
        "settlement_period": actual_record.get("settlement_period") if actual_record else None,
        "actual_mw": float(actual_record["generation_mw"]) if actual_record else None,
        "decision_cutoff": decision_cutoff,
        "selected_publish_time": selected_pub_time,
        "selected_forecast_mw": float(selected["generation_mw"]) if selected else None,
        "vintages": items,
        "missing_vintage_warning": warning
    }
