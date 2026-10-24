from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ForecastRecord(BaseModel):
    id: Optional[int] = None
    dataset: str = "WINDFOR"
    publish_time: str
    delivery_time: str
    generation_mw: float
    retrieval_time: str
    source_status: str = "OK"

class ActualRecord(BaseModel):
    id: Optional[int] = None
    dataset: str = "FUELHH"
    settlement_date: str
    settlement_period: int
    delivery_time: str
    fuel_type: str = "WIND"
    generation_mw: float
    publish_time: str
    retrieval_time: str

class EvaluationInterval(BaseModel):
    delivery_time: str
    display_time_london: str
    settlement_date: str
    settlement_period: Optional[int] = None
    actual_mw: Optional[float] = None
    forecast_mw: Optional[float] = None
    error_mw: Optional[float] = None
    abs_error_mw: Optional[float] = None
    selected_publish_time: Optional[str] = None
    lead_time_hours: Optional[float] = None
    status: str  # "VALID", "MISSING_FORECAST", "MISSING_ACTUAL", "MISSING_BOTH"

class AccuracyMetrics(BaseModel):
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    bias_mw: Optional[float] = None  # Mean Error (A_t - F_t)
    wape_pct: Optional[float] = None
    coverage_pct: float
    valid_pairs_count: int
    expected_intervals_count: int
    missing_forecast_count: int
    missing_actual_count: int
    total_actual_mwh: Optional[float] = None
    total_forecast_mwh: Optional[float] = None
    explanation: Dict[str, str] = Field(default_factory=dict)

class DailyMetric(BaseModel):
    date: str
    valid_pairs: int
    expected_intervals: int
    coverage_pct: float
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    bias_mw: Optional[float] = None
    wape_pct: Optional[float] = None
    avg_actual_mw: Optional[float] = None
    avg_forecast_mw: Optional[float] = None

class EvaluationResponse(BaseModel):
    date_from: str
    date_to: str
    cutoff_type: str = "rolling_da"  # "rolling_da", "snapshot", "latest"
    da_cutoff_time: str = "11:00"     # London local time
    decision_cutoff: Optional[str] = None
    granularity: str = "hourly"       # "hourly" (default native) or "half_hourly"
    alignment_method: str = "native_hourly"
    metrics: AccuracyMetrics
    intervals: List[EvaluationInterval]
    daily_breakdown: List[DailyMetric]
    quality_flags: List[str]
    last_updated: str
    data_source_mode: str = "LIVE"  # "LIVE" or "FIXTURE_DEMO"

class VintageItem(BaseModel):
    publish_time: str
    display_publish_london: str
    generation_mw: float
    lead_time_hours: float
    is_eligible_before_cutoff: bool
    is_selected: bool
    is_ex_post: bool = False

class VintageEvolutionResponse(BaseModel):
    delivery_time: str
    display_time_london: str
    settlement_date: Optional[str] = None
    settlement_period: Optional[int] = None
    actual_mw: Optional[float] = None
    decision_cutoff: Optional[str] = None
    selected_publish_time: Optional[str] = None
    selected_forecast_mw: Optional[float] = None
    vintages: List[VintageItem]
    missing_vintage_warning: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    elexon_api_connected: bool
    elexon_latency_ms: Optional[float] = None
    database_connected: bool
    cached_forecast_count: int
    cached_actual_count: int
    available_date_range_actuals: Optional[Dict[str, Optional[str]]] = None
    available_date_range_forecasts: Optional[Dict[str, Optional[str]]] = None
    last_sync_time: Optional[str] = None
    server_time_utc: str

class OptionsResponse(BaseModel):
    default_date_from: str
    default_date_to: str
    available_cutoff_presets: List[Dict[str, str]]
    datasets: List[Dict[str, str]]
