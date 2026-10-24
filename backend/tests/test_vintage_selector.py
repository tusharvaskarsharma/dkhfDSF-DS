import pytest
from app.services.vintage_selector import (
    select_forecast_for_delivery,
    select_forecasts_for_delivery_intervals,
    build_vintage_evolution
)

def test_vintage_selection_with_cutoff():
    delivery = "2026-01-02T12:00:00Z"
    vintages = [
        {"id": 1, "delivery_time": delivery, "publish_time": "2026-01-01T06:00:00Z", "generation_mw": 14000.0, "retrieval_time": "2026-01-01T07:00:00Z"},
        {"id": 2, "delivery_time": delivery, "publish_time": "2026-01-01T11:30:00Z", "generation_mw": 14500.0, "retrieval_time": "2026-01-01T12:00:00Z"},
        {"id": 3, "delivery_time": delivery, "publish_time": "2026-01-01T17:00:00Z", "generation_mw": 15000.0, "retrieval_time": "2026-01-01T18:00:00Z"},
        {"id": 4, "delivery_time": delivery, "publish_time": "2026-01-02T06:00:00Z", "generation_mw": 15200.0, "retrieval_time": "2026-01-02T07:00:00Z"},
    ]

    # Test 1: Day-Ahead 12:00 UTC cutoff
    sel_da12 = select_forecast_for_delivery(vintages, decision_cutoff="2026-01-01T12:00:00Z")
    assert sel_da12 is not None
    assert sel_da12["id"] == 2
    assert sel_da12["generation_mw"] == 14500.0
    assert sel_da12["publish_time"] == "2026-01-01T11:30:00Z"
    assert sel_da12["lead_time_hours"] == 24.5

    # Test 2: Cutoff before any publication -> No look-ahead leak
    sel_early = select_forecast_for_delivery(vintages, decision_cutoff="2026-01-01T05:00:00Z")
    assert sel_early is None

    # Test 3: Late Cutoff -> Selects latest vintage
    sel_late = select_forecast_for_delivery(vintages, decision_cutoff="2026-01-02T10:00:00Z")
    assert sel_late is not None
    assert sel_late["id"] == 4
    assert sel_late["generation_mw"] == 15200.0

def test_deterministic_tie_break():
    delivery = "2026-01-02T12:00:00Z"
    same_time = "2026-01-01T11:30:00Z"
    vintages = [
        {"id": 10, "delivery_time": delivery, "publish_time": same_time, "generation_mw": 14000.0, "retrieval_time": "2026-01-01T12:00:00Z"},
        {"id": 20, "delivery_time": delivery, "publish_time": same_time, "generation_mw": 14200.0, "retrieval_time": "2026-01-01T12:05:00Z"},
    ]
    # Higher id wins deterministically
    sel = select_forecast_for_delivery(vintages, decision_cutoff="2026-01-01T12:00:00Z")
    assert sel is not None
    assert sel["id"] == 20
    assert sel["generation_mw"] == 14200.0

def test_build_vintage_evolution():
    delivery = "2026-01-02T12:00:00Z"
    vintages = [
        {"id": 1, "delivery_time": delivery, "publish_time": "2026-01-01T06:00:00Z", "generation_mw": 14000.0},
        {"id": 2, "delivery_time": delivery, "publish_time": "2026-01-01T11:30:00Z", "generation_mw": 14500.0},
        {"id": 3, "delivery_time": delivery, "publish_time": "2026-01-01T17:00:00Z", "generation_mw": 15000.0},
    ]
    actual = {"settlement_date": "2026-01-02", "settlement_period": 25, "generation_mw": 14800.0}

    evo = build_vintage_evolution(
        delivery_time=delivery,
        vintages=vintages,
        decision_cutoff="2026-01-01T12:00:00Z",
        actual_record=actual
    )

    assert evo["actual_mw"] == 14800.0
    assert evo["selected_forecast_mw"] == 14500.0
    assert len(evo["vintages"]) == 3
    # Check eligibility flags
    assert evo["vintages"][0]["is_eligible_before_cutoff"] is True
    assert evo["vintages"][0]["is_selected"] is False
    assert evo["vintages"][1]["is_eligible_before_cutoff"] is True
    assert evo["vintages"][1]["is_selected"] is True
    assert evo["vintages"][2]["is_eligible_before_cutoff"] is False
    assert evo["vintages"][2]["is_selected"] is False
