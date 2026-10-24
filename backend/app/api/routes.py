from fastapi import APIRouter, Query, HTTPException, Response
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta, timezone

from app.core.config import settings
from app.core.time_utils import (
    format_utc_iso,
    parse_utc_iso,
    generate_expected_intervals_in_range,
    format_london_display
)
from app.models.schemas import (
    HealthResponse,
    OptionsResponse,
    EvaluationResponse,
    VintageEvolutionResponse,
    ForecastRecord,
    ActualRecord
)
from app.data.repository import (
    get_cache_stats,
    get_actual_records,
    get_forecast_records,
    get_all_vintages_for_delivery,
    upsert_actuals,
    upsert_forecasts
)
from app.data.fixtures.fixture_loader import (
    get_fixture_actuals,
    get_fixture_forecasts,
    load_fixture_data_into_db
)
from app.services.elexon_client import elexon_client
from app.services.vintage_selector import (
    select_forecasts_for_delivery_intervals,
    build_vintage_evolution
)
from app.services.alignment import align_forecast_and_actuals
from app.services.metrics import calculate_accuracy_metrics, calculate_daily_breakdown
from app.services.export_service import generate_evaluation_csv

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def get_health():
    """System health check and Elexon API connectivity status."""
    connected, latency, err = await elexon_client.check_api_health()
    stats = get_cache_stats()
    
    return HealthResponse(
        status="HEALTHY" if connected else "DEGRADED",
        elexon_api_connected=connected,
        elexon_latency_ms=latency,
        database_connected=True,
        cached_forecast_count=stats["cached_forecast_count"],
        cached_actual_count=stats["cached_actual_count"],
        available_date_range_actuals=stats["available_date_range_actuals"],
        available_date_range_forecasts=stats["available_date_range_forecasts"],
        last_sync_time=stats["last_sync_time"],
        server_time_utc=format_utc_iso(datetime.now(timezone.utc))
    )

@router.get("/config/options", response_model=OptionsResponse)
def get_options():
    """Retrieve UI configuration options and preset decision cutoffs."""
    return OptionsResponse(
        default_date_from=settings.DEFAULT_DATE_FROM,
        default_date_to=settings.DEFAULT_DATE_TO,
        available_cutoff_presets=[
            {"id": "latest", "label": "Latest Published (No Cutoff)", "description": "Select the latest publication vintage published before delivery."},
            {"id": "da_1100", "label": "Day-Ahead 11:00 UTC", "description": "EPEX / Nord Pool Day-Ahead Auction Gate Closure (11:00 UTC D-1)."},
            {"id": "da_1700", "label": "Day-Ahead 17:00 UTC", "description": "National Grid Indicative Day-Ahead Schedule (17:00 UTC D-1)."},
            {"id": "da_2300", "label": "Day-Ahead 23:00 UTC", "description": "Midnight preceding delivery day (23:00 UTC D-1)."},
            {"id": "custom", "label": "Custom Timestamp Cutoff", "description": "Strict point-in-time historical decision boundary."}
        ],
        datasets=[
            {"id": "FUELHH", "name": "Half-Hourly Generation by Fuel Type (Actuals)", "fuelType": "WIND"},
            {"id": "WINDFOR", "name": "Wind Generation Forecast (Multi-Vintage)", "resolution": "Hourly average MW"}
        ]
    )

@router.get("/forecasts", response_model=List[ForecastRecord])
def get_forecasts(
    delivery_from: Optional[str] = Query(None, description="Start delivery time (ISO UTC)"),
    delivery_to: Optional[str] = Query(None, description="End delivery time (ISO UTC)"),
    publish_cutoff: Optional[str] = Query(None, description="Maximum publication time (ISO UTC)")
):
    """Query raw cached wind forecast records."""
    records = get_forecast_records(delivery_from, delivery_to, publish_cutoff)
    return [ForecastRecord(**r) for r in records]

@router.get("/actuals", response_model=List[ActualRecord])
def get_actuals(
    date_from: Optional[str] = Query(None, description="Start settlement date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End settlement date YYYY-MM-DD")
):
    """Query raw cached wind actual generation records."""
    records = get_actual_records(date_from=date_from, date_to=date_to)
    return [ActualRecord(**r) for r in records]

@router.get("/evaluation", response_model=EvaluationResponse)
async def evaluate_forecasts(
    date_from: str = Query(settings.DEFAULT_DATE_FROM, description="Start date YYYY-MM-DD"),
    date_to: str = Query(settings.DEFAULT_DATE_TO, description="End date YYYY-MM-DD"),
    decision_cutoff: Optional[str] = Query(None, description="Decision cutoff timestamp (ISO UTC)"),
    granularity: str = Query("half_hourly", pattern="^(half_hourly|hourly)$"),
    mode: str = Query("auto", description="'auto', 'live', or 'demo'")
):
    """
    Core evaluation endpoint:
    Performs vintage selection, interval alignment, error calculation, and metrics computation.
    """
    quality_flags = []
    source_mode = "LIVE"

    # Check if demo mode requested
    if mode == "demo":
        source_mode = "FIXTURE_DEMO"
        # Ensure fixtures are loaded into DB
        load_fixture_data_into_db()
        quality_flags.append("DEMO_FIXTURE_MODE: Results generated from deterministic offline test fixtures.")
    else:
        # Check if records are cached in SQLite
        cached_actuals = get_actual_records(date_from=date_from, date_to=date_to)
        if not cached_actuals and mode != "demo":
            # Attempt to fetch from live Elexon API
            try:
                await elexon_client.fetch_fuelhh_actuals(date_from, date_to)
                # For WINDFOR forecasts, fetch publications starting 3 days before date_from up to date_to
                d_start = date.fromisoformat(date_from) - timedelta(days=3)
                pub_from = f"{d_start.isoformat()}T00:00:00Z"
                pub_to = f"{date_to}T23:59:59Z"
                await elexon_client.fetch_windfor_forecasts(pub_from, pub_to)
            except Exception as e:
                if settings.ALLOW_FIXTURE_FALLBACK:
                    source_mode = "FIXTURE_DEMO"
                    load_fixture_data_into_db()
                    quality_flags.append(f"LIVE_API_UNAVAILABLE: {str(e)[:150]}. Showing deterministic fixture data.")
                else:
                    raise HTTPException(status_code=502, detail=f"Failed to fetch live data: {str(e)}")

    # Retrieve from DB
    actuals = get_actual_records(date_from=date_from, date_to=date_to)
    
    # Calculate bounds for forecasts
    d_start_iso = f"{date_from}T00:00:00Z"
    d_end_iso = f"{date_to}T23:59:59Z"
    raw_forecasts = get_forecast_records(delivery_from=d_start_iso, delivery_to=d_end_iso)

    # Apply Decision Cutoff & Vintage Selection
    selected_forecasts_by_hour = select_forecasts_for_delivery_intervals(raw_forecasts, decision_cutoff)

    # Generate Expected Intervals (handling DST properly)
    expected_intervals = generate_expected_intervals_in_range(date_from, date_to)

    # Interval Alignment
    aligned = align_forecast_and_actuals(
        expected_intervals=expected_intervals,
        actual_records=actuals,
        selected_forecasts_by_hour=selected_forecasts_by_hour,
        granularity=granularity
    )

    # Accuracy Metrics Calculation
    exp_count = len(expected_intervals) if granularity == "half_hourly" else (len(expected_intervals) // 2)
    metrics = calculate_accuracy_metrics(aligned, exp_count)
    daily = calculate_daily_breakdown(aligned)

    if metrics.coverage_pct < 80.0:
        quality_flags.append(f"LOW_COVERAGE_WARNING: Paired coverage is {metrics.coverage_pct}% (below 80%).")
    if metrics.missing_forecast_count > 0:
        quality_flags.append(f"MISSING_FORECASTS: {metrics.missing_forecast_count} intervals have no eligible forecast before cutoff.")
    if metrics.missing_actual_count > 0:
        quality_flags.append(f"MISSING_ACTUALS: {metrics.missing_actual_count} intervals have missing FUELHH actual generation.")

    return EvaluationResponse(
        date_from=date_from,
        date_to=date_to,
        decision_cutoff=decision_cutoff,
        granularity=granularity,
        metrics=metrics,
        intervals=aligned,
        daily_breakdown=daily,
        quality_flags=quality_flags,
        last_updated=format_utc_iso(datetime.now(timezone.utc)),
        data_source_mode=source_mode
    )

@router.get("/vintages", response_model=VintageEvolutionResponse)
def get_vintages(
    delivery_time: str = Query(..., description="Target delivery start time in ISO UTC (e.g. 2026-01-01T12:00:00Z)"),
    decision_cutoff: Optional[str] = Query(None, description="Optional decision cutoff (ISO UTC)")
):
    """
    Retrieve all historical publication vintages for a specific delivery interval.
    Shows how the forecast evolved across publication runs and highlights the cutoff selection.
    """
    vintages = get_all_vintages_for_delivery(delivery_time)
    
    # Try finding matching actual record
    actuals = get_actual_records(delivery_from=delivery_time, delivery_to=delivery_time)
    actual_rec = actuals[0] if actuals else None

    evolution = build_vintage_evolution(
        delivery_time=delivery_time,
        vintages=vintages,
        decision_cutoff=decision_cutoff,
        actual_record=actual_rec
    )
    return VintageEvolutionResponse(**evolution)

@router.get("/export")
async def export_csv(
    date_from: str = Query(settings.DEFAULT_DATE_FROM),
    date_to: str = Query(settings.DEFAULT_DATE_TO),
    decision_cutoff: Optional[str] = Query(None),
    granularity: str = Query("half_hourly", pattern="^(half_hourly|hourly)$")
):
    """Export evaluated intervals to CSV with identical methodology to the dashboard."""
    # Run the exact same evaluation pipeline
    eval_resp = await evaluate_forecasts(
        date_from=date_from,
        date_to=date_to,
        decision_cutoff=decision_cutoff,
        granularity=granularity,
        mode="auto"
    )
    intervals_dict = [it.model_dump() for it in eval_resp.intervals]
    csv_content = generate_evaluation_csv(intervals_dict)
    
    filename = f"wind_forecast_accuracy_{date_from}_{date_to}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/sync")
async def sync_data(
    date_from: str = Query(settings.DEFAULT_DATE_FROM),
    date_to: str = Query(settings.DEFAULT_DATE_TO)
):
    """Trigger on-demand fetch and caching from Elexon BMRS API."""
    try:
        act_records = await elexon_client.fetch_fuelhh_actuals(date_from, date_to)
        d_start = date.fromisoformat(date_from) - timedelta(days=3)
        pub_from = f"{d_start.isoformat()}T00:00:00Z"
        pub_to = f"{date_to}T23:59:59Z"
        fc_records = await elexon_client.fetch_windfor_forecasts(pub_from, pub_to)
        return {
            "status": "SUCCESS",
            "actuals_ingested": len(act_records),
            "forecasts_ingested": len(fc_records),
            "date_range": f"{date_from} to {date_to}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.post("/demo/load")
def load_demo():
    """Load deterministic fixture data for testing and offline demo."""
    res = load_fixture_data_into_db()
    return {"status": "SUCCESS", "records_loaded": res}
