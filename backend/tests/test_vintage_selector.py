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

def test_prevent_ex_post_look_ahead_leakage():
    """Prove that vintages published after delivery time are NEVER selected, even with no cutoff."""
    delivery = "2026-01-02T12:00:00Z"
    vintages = [
        {"id": 1, "delivery_time": delivery, "publish_time": "2026-01-02T06:00:00Z", "generation_mw": 12000.0},
        {"id": 2, "delivery_time": delivery, "publish_time": "2026-01-02T11:00:00Z", "generation_mw": 12500.0},
        # Ex-post revision published AFTER interval started:
        {"id": 3, "delivery_time": delivery, "publish_time": "2026-01-02T14:00:00Z", "generation_mw": 13800.0},
        {"id": 4, "delivery_time": delivery, "publish_time": "2026-01-03T02:00:00Z", "generation_mw": 13900.0},
    ]

    # Without decision cutoff, it must select id=2 (11:00Z), NOT id=3 or id=4
    sel = select_forecast_for_delivery(vintages, decision_cutoff=None, delivery_time=delivery)
    assert sel is not None
    assert sel["id"] == 2
    assert sel["generation_mw"] == 12500.0
    assert sel["publish_time"] == "2026-01-02T11:00:00Z"
    assert sel["lead_time_hours"] == 1.0

def test_rolling_day_ahead_multi_day_evaluation():
    """Verify that in rolling_da mode, each delivery day uses its specific D-1 11:00 London cutoff."""
    fc_records = [
        # For Jan 1 delivery: published Dec 30 (eligible), Dec 31 10:00 (eligible), Dec 31 14:00 (too late for DA)
        {"id": 101, "delivery_time": "2026-01-01T15:00:00Z", "publish_time": "2025-12-30T11:00:00Z", "generation_mw": 8000.0},
        {"id": 102, "delivery_time": "2026-01-01T15:00:00Z", "publish_time": "2025-12-31T10:30:00Z", "generation_mw": 8500.0},
        {"id": 103, "delivery_time": "2026-01-01T15:00:00Z", "publish_time": "2025-12-31T14:00:00Z", "generation_mw": 9000.0},

        # For Jan 2 delivery: published Dec 31 10:30 (eligible), Jan 1 10:30 (eligible for Jan 2!), Jan 1 15:00 (too late for Jan 2)
        {"id": 201, "delivery_time": "2026-01-02T15:00:00Z", "publish_time": "2025-12-31T10:30:00Z", "generation_mw": 10000.0},
        {"id": 202, "delivery_time": "2026-01-02T15:00:00Z", "publish_time": "2026-01-01T10:30:00Z", "generation_mw": 11000.0},
        {"id": 203, "delivery_time": "2026-01-02T15:00:00Z", "publish_time": "2026-01-01T15:00:00Z", "generation_mw": 12000.0},
    ]

    sel_map = select_forecasts_for_delivery_intervals(
        fc_records,
        cutoff_type="rolling_da",
        da_cutoff_time="11:00"
    )

    # Jan 1 must pick 102 (published Dec 31 10:30Z <= Dec 31 11:00Z)
    assert "2026-01-01T15:00:00Z" in sel_map
    assert sel_map["2026-01-01T15:00:00Z"]["id"] == 102
    assert sel_map["2026-01-01T15:00:00Z"]["generation_mw"] == 8500.0

    # Jan 2 must pick 202 (published Jan 1 10:30Z <= Jan 1 11:00Z)
    assert "2026-01-02T15:00:00Z" in sel_map
    assert sel_map["2026-01-02T15:00:00Z"]["id"] == 202
    assert sel_map["2026-01-02T15:00:00Z"]["generation_mw"] == 11000.0

def test_bst_daylight_saving_cutoff():
    """Verify that during British Summer Time (BST), 11:00 London time evaluates to 10:00 UTC."""
    from app.core.time_utils import get_day_ahead_cutoff_utc, format_utc_iso
    # Summer date in July (BST is UTC+1)
    cutoff_utc = get_day_ahead_cutoff_utc("2026-07-15", cutoff_time_str="11:00")
    utc_str = format_utc_iso(cutoff_utc)
    # D-1 is 2026-07-14; 11:00 BST is 10:00 UTC
    assert utc_str == "2026-07-14T10:00:00Z"

def test_later_published_hindcast_cannot_replace_eligible_forecast():
    """
    Prove that a later-published NWP hindcast or assimilation record
    (even with a higher database ID and later publication timestamp)
    CANNOT replace an eligible earlier forecast for a historical trading decision.
    """
    delivery = "2026-01-02T12:00:00Z"
    
    # Target delivery: 2026-01-02T12:00:00Z.
    # D-1 is 2026-01-01. Order book cutoff for EPEX SPOT 09:20 London is 2026-01-01T09:20:00Z.
    # Four candidate records in the database:
    # 1. Run 1 published 2026-01-01T07:30:00Z (eligible for DA trading): 10,000 MW, ID 10
    # 2. Run 2 published 2026-01-01T15:30:00Z (post-DA auction, pre-delivery): 12,000 MW, ID 20
    # 3. Run 3 published 2026-01-02T14:00:00Z (post-delivery NWP assimilation tail): 14,000 MW, ID 900
    # 4. Run 4 published 2026-01-03T06:00:00Z (ex-post next-day reanalysis): 15,000 MW, ID 1200
    vintages = [
        {"id": 10, "delivery_time": delivery, "publish_time": "2026-01-01T07:30:00Z", "generation_mw": 10000.0, "retrieval_time": "2026-01-01T08:00:00Z"},
        {"id": 20, "delivery_time": delivery, "publish_time": "2026-01-01T15:30:00Z", "generation_mw": 12000.0, "retrieval_time": "2026-01-01T16:00:00Z"},
        {"id": 900, "delivery_time": delivery, "publish_time": "2026-01-02T14:00:00Z", "generation_mw": 14000.0, "retrieval_time": "2026-01-02T14:30:00Z"},
        {"id": 1200, "delivery_time": delivery, "publish_time": "2026-01-03T06:00:00Z", "generation_mw": 15000.0, "retrieval_time": "2026-01-03T06:30:00Z"},
    ]
    
    # 1. Day-Ahead Operational Decision (EPEX SPOT 09:20 London cutoff on D-1):
    sel_da = select_forecast_for_delivery(vintages, decision_cutoff="2026-01-01T09:20:00Z", delivery_time=delivery)
    assert sel_da is not None
    assert sel_da["id"] == 10
    assert sel_da["generation_mw"] == 10000.0
    assert sel_da["publish_time"] == "2026-01-01T07:30:00Z"
    
    # 2. Retrospective Latest Pre-Delivery (decision_cutoff is None, delivery_time=delivery):
    # Runs 1 & 2 published before delivery start (2026-01-02T12:00:00Z).
    # Runs 3 & 4 are post-delivery assimilation records (publish_time > delivery_time).
    # The selector MUST select Run 2 (15:30:00Z on D-1, 12,000 MW), rejecting Runs 3 & 4 despite their higher IDs.
    sel_retro = select_forecast_for_delivery(vintages, decision_cutoff=None, delivery_time=delivery)
    assert sel_retro is not None
    assert sel_retro["id"] == 20
    assert sel_retro["generation_mw"] == 12000.0
    assert sel_retro["publish_time"] == "2026-01-01T15:30:00Z"


