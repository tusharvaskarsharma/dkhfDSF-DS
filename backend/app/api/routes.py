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
            {
                "id": "rolling_da",
                "label": "Day-Ahead Operational (Rolling D-1 11:00 London Time)",
                "description": "Standard GB Day-Ahead trading cutoff. For each delivery day D, evaluates the forecast published before 11:00 London Local Time on D-1 (EPEX SPOT / Nord Pool auction gate closure; 11:00 GMT in winter / 10:00 UTC during BST)."
            },
            {
                "id": "rolling_da_1700",
                "label": "Day-Ahead Schedule (Rolling D-1 17:00 London Time)",
                "description": "National Grid ESO Indicative Day-Ahead schedule publication boundary (17:00 London Local Time on D-1)."
            },
            {
                "id": "latest",
                "label": "Retrospective Benchmark (Latest before Delivery)",
                "description": "Evaluates the latest available forecast published prior to interval delivery start (strictly publish_time <= delivery_time; ex-post runs excluded)."
            },
            {
                "id": "snapshot",
                "label": "Historical Point-in-Time Snapshot",
                "description": "Strict point-in-time barrier. Evaluates only what had been published at or before a single fixed historical instant."
            }
        ],
        datasets=[
            {"id": "FUELHH", "name": "Half-Hourly Generation by Fuel Type (Actuals)", "fuelType": "WIND", "resolution": "Half-hourly (SP 1-48, average MW)"},
            {"id": "WINDFOR", "name": "Wind Generation Forecast (Multi-Vintage)", "resolution": "Hourly average MW (broadcast to SP 2k-1/2k in HH mode)"}
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
    cutoff_type: str = Query("rolling_da", pattern="^(rolling_da|snapshot|latest)$", description="Cutoff selection rule"),
    da_cutoff_time: str = Query("11:00", description="Day-Ahead cutoff time in London local time (HH:MM)"),
    decision_cutoff: Optional[str] = Query(None, description="Static decision cutoff timestamp in ISO UTC (used when cutoff_type='snapshot')"),
    granularity: str = Query("hourly", pattern="^(hourly|half_hourly)$", description="Evaluation time resolution"),
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
    selected_forecasts_by_hour = select_forecasts_for_delivery_intervals(
        raw_forecasts,
        cutoff_type=cutoff_type,
        decision_cutoff=decision_cutoff,
        da_cutoff_time=da_cutoff_time
    )

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

    alignment_method = "native_hourly" if granularity == "hourly" else "half_hourly_broadcast"
    if granularity == "half_hourly":
        quality_flags.append("HALF_HOURLY_BROADCAST: WINDFOR is natively hourly (average MW). Hourly forecasts are duplicated across SP 2k-1 and SP 2k. Intra-hour ramp variations are incorporated into error metrics.")
    else:
        quality_flags.append("NATIVE_HOURLY: Actual FUELHH periods are averaged ((SP_2k-1 + SP_2k)/2) to match WINDFOR's native 1-hour resolution without observation duplication.")

    if cutoff_type == "rolling_da":
        quality_flags.append(f"DAY_AHEAD_OPERATIONAL: For each delivery day D, evaluated against forecast published prior to D-1 {da_cutoff_time} London local time (GB Day-Ahead Auction cutoff).")
    elif cutoff_type == "snapshot":
        quality_flags.append(f"POINT_IN_TIME_SNAPSHOT: Single cutoff applied at {decision_cutoff}. Later intervals without published vintages prior to this instant are marked MISSING_FORECAST.")
    else:
        quality_flags.append("RETROSPECTIVE_BENCHMARK: Evaluated against latest available forecast published prior to delivery start (strictly publish_time <= delivery_time; ex-post runs excluded).")

    if metrics.coverage_pct < 80.0:
        quality_flags.append(f"LOW_COVERAGE_WARNING: Paired coverage is {metrics.coverage_pct}% (below 80%).")
    if metrics.missing_forecast_count > 0:
        quality_flags.append(f"MISSING_FORECASTS: {metrics.missing_forecast_count} intervals have no eligible forecast before cutoff.")
    if metrics.missing_actual_count > 0:
        quality_flags.append(f"MISSING_ACTUALS: {metrics.missing_actual_count} intervals have missing FUELHH actual generation.")

    return EvaluationResponse(
        date_from=date_from,
        date_to=date_to,
        cutoff_type=cutoff_type,
        da_cutoff_time=da_cutoff_time,
        decision_cutoff=decision_cutoff,
        granularity=granularity,
        alignment_method=alignment_method,
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
    cutoff_type: str = Query("rolling_da", pattern="^(rolling_da|snapshot|latest)$"),
    da_cutoff_time: str = Query("11:00"),
    decision_cutoff: Optional[str] = Query(None),
    granularity: str = Query("hourly", pattern="^(hourly|half_hourly)$")
):
    """Export evaluated intervals to CSV with identical methodology to the dashboard."""
    # Run the exact same evaluation pipeline
    eval_resp = await evaluate_forecasts(
        date_from=date_from,
        date_to=date_to,
        cutoff_type=cutoff_type,
        da_cutoff_time=da_cutoff_time,
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
