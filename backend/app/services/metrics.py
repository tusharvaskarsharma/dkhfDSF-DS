import math
from typing import List, Dict, Optional, Any
from app.models.schemas import AccuracyMetrics, DailyMetric

def calculate_accuracy_metrics(
    aligned_intervals: List[Dict[str, Any]],
    expected_count: int
) -> AccuracyMetrics:
    """
    Calculate forecast accuracy metrics strictly from valid paired intervals:
      e_t = A_t - F_t
      ME (bias) = (1/N) * sum(A_t - F_t)
      MAE = (1/N) * sum(|A_t - F_t|)
      RMSE = sqrt((1/N) * sum((A_t - F_t)^2))
      WAPE = (sum(|A_t - F_t|) / sum(|A_t|)) * 100%
      Coverage = (N / expected_count) * 100%
    """
    valid_pairs = [it for it in aligned_intervals if it["status"] == "VALID"]
    N = len(valid_pairs)
    missing_forecast = sum(1 for it in aligned_intervals if it["status"] == "MISSING_FORECAST")
    missing_actual = sum(1 for it in aligned_intervals if it["status"] == "MISSING_ACTUAL")

    coverage_pct = round((N / expected_count * 100.0), 2) if expected_count > 0 else 0.0

    if N == 0:
        return AccuracyMetrics(
            mae_mw=None,
            rmse_mw=None,
            bias_mw=None,
            wape_pct=None,
            coverage_pct=coverage_pct,
            valid_pairs_count=0,
            expected_intervals_count=expected_count,
            missing_forecast_count=missing_forecast,
            missing_actual_count=missing_actual,
            total_actual_mwh=0.0,
            total_forecast_mwh=0.0,
            explanation={
                "status": "No valid paired forecast/actual intervals available for the selected cutoff and date range."
            }
        )

    sum_errors = sum(it["actual_mw"] - it["forecast_mw"] for it in valid_pairs)
    sum_abs_errors = sum(abs(it["actual_mw"] - it["forecast_mw"]) for it in valid_pairs)
    sum_sq_errors = sum((it["actual_mw"] - it["forecast_mw"]) ** 2 for it in valid_pairs)
    sum_actuals = sum(abs(it["actual_mw"]) for it in valid_pairs)
    
    # Generation totals in MWh (each half-hour interval represents 0.5 hours of power)
    # If intervals are 1-hour, 1.0 hour. We can check time delta between intervals.
    is_hourly = len(aligned_intervals) > 1 and aligned_intervals[0]["delivery_time"][:13] != aligned_intervals[1]["delivery_time"][:13]
    hour_factor = 1.0 if is_hourly else 0.5

    total_act_mwh = round(sum(it["actual_mw"] for it in valid_pairs) * hour_factor, 2)
    total_fc_mwh = round(sum(it["forecast_mw"] for it in valid_pairs) * hour_factor, 2)

    me_bias = round(sum_errors / N, 2)
    mae = round(sum_abs_errors / N, 2)
    rmse = round(math.sqrt(sum_sq_errors / N), 2)

    if sum_actuals > 0:
        wape = round((sum_abs_errors / sum_actuals) * 100.0, 2)
        wape_explanation = "WAPE calculated as sum(|A_t - F_t|) / sum(|A_t|) * 100%."
    else:
        wape = None
        wape_explanation = "WAPE is undefined because total actual generation was zero in the selected period."

    bias_interp = "Underpredicted actuals on average (+)" if me_bias > 0 else (
        "Overpredicted actuals on average (-)" if me_bias < 0 else "Neutral zero bias"
    )

    return AccuracyMetrics(
        mae_mw=mae,
        rmse_mw=rmse,
        bias_mw=me_bias,
        wape_pct=wape,
        coverage_pct=coverage_pct,
        valid_pairs_count=N,
        expected_intervals_count=expected_count,
        missing_forecast_count=missing_forecast,
        missing_actual_count=missing_actual,
        total_actual_mwh=total_act_mwh,
        total_forecast_mwh=total_fc_mwh,
        explanation={
            "bias_interpretation": bias_interp,
            "wape_note": wape_explanation,
            "unit": "Generation and absolute errors in MW; WAPE and Coverage in %"
        }
    )

def calculate_daily_breakdown(aligned_intervals: List[Dict[str, Any]]) -> List[DailyMetric]:
    """Group aligned intervals by settlement date and compute daily accuracy metrics."""
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for it in aligned_intervals:
        by_date.setdefault(it["settlement_date"], []).append(it)

    daily_metrics = []
    for d_str, items in sorted(by_date.items()):
        valid = [x for x in items if x["status"] == "VALID"]
        n_val = len(valid)
        n_exp = len(items)
        cov = round((n_val / n_exp * 100.0), 1) if n_exp > 0 else 0.0

        if n_val > 0:
            sum_err = sum(x["actual_mw"] - x["forecast_mw"] for x in valid)
            sum_abs_err = sum(abs(x["actual_mw"] - x["forecast_mw"]) for x in valid)
            sum_sq_err = sum((x["actual_mw"] - x["forecast_mw"]) ** 2 for x in valid)
            sum_act = sum(abs(x["actual_mw"]) for x in valid)
            
            mae = round(sum_abs_err / n_val, 2)
            rmse = round(math.sqrt(sum_sq_err / n_val), 2)
            bias = round(sum_err / n_val, 2)
            wape = round((sum_abs_err / sum_act) * 100.0, 2) if sum_act > 0 else None
            avg_act = round(sum(x["actual_mw"] for x in valid) / n_val, 2)
            avg_fc = round(sum(x["forecast_mw"] for x in valid) / n_val, 2)
        else:
            mae = rmse = bias = wape = avg_act = avg_fc = None

        daily_metrics.append(DailyMetric(
            date=d_str,
            valid_pairs=n_val,
            expected_intervals=n_exp,
            coverage_pct=cov,
            mae_mw=mae,
            rmse_mw=rmse,
            bias_mw=bias,
            wape_pct=wape,
            avg_actual_mw=avg_act,
            avg_forecast_mw=avg_fc
        ))

    return daily_metrics
