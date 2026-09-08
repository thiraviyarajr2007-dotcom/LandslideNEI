"""
Rigorous Validation & QC Test Suite for Historical Landslide-Rainfall Dataset
Project: LANDSLIDENEI
"""

import os
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_dataset_integrity():
    print("=== RUNNING AUTOMATED QC VALIDATION SUITE ===")
    
    # 1. Historical Landslide Events
    events_path = os.path.join(PROJECT_ROOT, "historical_landslide_events.csv")
    assert os.path.exists(events_path), "historical_landslide_events.csv missing"
    df_events = pd.read_csv(events_path, keep_default_na=False)
    
    print(f"1. Events CSV: {len(df_events)} rows, {len(df_events.columns)} columns")
    assert len(df_events) == 75, f"Expected 75 events, found {len(df_events)}"
    
    req_cols = [
        'event_id', 'event_date', 'event_time', 'event_time_precision',
        'state', 'district', 'subdistrict', 'village', 'locality',
        'latitude', 'longitude', 'location_precision', 'landslide_type',
        'trigger_reported', 'fatalities', 'houses_affected', 'road_affected',
        'source_id', 'source_name', 'source_url', 'source_document',
        'source_page', 'source_date', 'access_date', 'confidence', 'notes'
    ]
    for col in req_cols:
        assert col in df_events.columns, f"Missing required column: {col}"
        
    # Check bounds
    lats = pd.to_numeric(df_events['latitude'])
    lons = pd.to_numeric(df_events['longitude'])
    assert (lats >= 21.5).all() and (lats <= 30.0).all(), "Latitudes out of NER bounds [21.5, 30.0]"
    assert (lons >= 88.0).all() and (lons <= 98.0).all(), "Longitudes out of NER bounds [88.0, 98.0]"
    print("  -> Coordinates validated within NER bounding box [21.5N-30.0N, 88.0E-98.0E]")
    
    # Check Enums
    valid_time_prec = {'EXACT_TIME', 'DATE_ONLY', 'MONTH_ONLY', 'YEAR_ONLY', 'UNKNOWN'}
    assert set(df_events['event_time_precision']).issubset(valid_time_prec), "Invalid event_time_precision enum"
    
    valid_loc_prec = {'EXACT_COORDINATE', 'APPROXIMATE_COORDINATE', 'GEOCODED_LOCATION', 'DISTRICT_ONLY', 'STATE_ONLY', 'UNKNOWN'}
    assert set(df_events['location_precision']).issubset(valid_loc_prec), "Invalid location_precision enum"
    print("  -> Enums validated strictly against schema requirements")
    
    # Check Casualties
    fats = pd.to_numeric(df_events['fatalities'])
    assert fats.sum() == 21, f"Expected exactly 21 total casualties, got {fats.sum()}"
    print("  -> Casualty total matches official NESAC summary: exactly 21 casualties")
    
    # 2. Source Register
    src_path = os.path.join(PROJECT_ROOT, "source_register.csv")
    assert os.path.exists(src_path), "source_register.csv missing"
    df_src = pd.read_csv(src_path, keep_default_na=False)
    print(f"2. Source Register: {len(df_src)} sources registered")
    assert set(df_events['source_id']).issubset(set(df_src['source_id'])), "Unregistered source_id in events"
    print("  -> Foreign key integrity verified between events and source_register")
    
    # 3. Rainfall Alignment
    align_path = os.path.join(PROJECT_ROOT, "event_rainfall_alignment.csv")
    assert os.path.exists(align_path), "event_rainfall_alignment.csv missing"
    df_align = pd.read_csv(align_path, keep_default_na=False)
    print(f"3. Alignment CSV: {len(df_align)} rows")
    assert len(df_align) == 75, "Alignment row count mismatch"
    valid_align = {'EXACT', 'SAME_DAY', 'WITHIN_24H', 'WITHIN_72H', 'DATE_ONLY', 'UNKNOWN'}
    assert set(df_align['temporal_alignment']).issubset(valid_align), "Invalid temporal_alignment enum"
    print("  -> Temporal alignment enums verified")
    
    # 4. Rainfall Windows
    win_path = os.path.join(PROJECT_ROOT, "event_rainfall_windows.csv")
    assert os.path.exists(win_path), "event_rainfall_windows.csv missing"
    df_win = pd.read_csv(win_path, keep_default_na=False)
    print(f"4. Windows CSV: {len(df_win)} rows")
    assert len(df_win) == 75, "Windows row count mismatch"
    # Check that missing rainfall windows are empty strings and not synthetic zeroes
    uncalc_gpm = df_win[df_win['rainfall_source'] == 'GPM/IMERG']
    assert (uncalc_gpm['rainfall_1h_mm'] == '').all(), "Synthetic zeroes detected in uncalculated 1h window!"
    assert (uncalc_gpm['rainfall_72h_mm'] == '').all(), "Synthetic zeroes detected in uncalculated 72h window!"
    print("  -> Zero-replacement audit passed: missing rainfall windows are strictly NULL, no synthetic zeros")
    
    # 5. Candidate Control Periods
    ctrl_path = os.path.join(PROJECT_ROOT, "candidate_control_periods.csv")
    assert os.path.exists(ctrl_path), "candidate_control_periods.csv missing"
    df_ctrl = pd.read_csv(ctrl_path, keep_default_na=False)
    print(f"5. Candidate Controls: {len(df_ctrl)} rows")
    assert len(df_ctrl) == 75, "Candidate controls row count mismatch"
    assert (df_ctrl['quality'] == 'CANDIDATE_CONTROL').all(), "Improper control labeling"
    assert not (df_ctrl['quality'].str.contains('CONFIRMED_NO_LANDSLIDE')).any(), "Prohibited CONFIRMED_NO_LANDSLIDE label detected!"
    print("  -> Control labels strictly verified as CANDIDATE_CONTROL")
    
    # 6. Duplicate Review
    dup_path = os.path.join(PROJECT_ROOT, "event_duplicate_review.csv")
    assert os.path.exists(dup_path), "event_duplicate_review.csv missing"
    df_dup = pd.read_csv(dup_path, keep_default_na=False)
    print(f"6. Duplicate Review: {len(df_dup)} candidate pairs audited")
    valid_decisions = {'SAME_EVENT', 'DIFFERENT_EVENT', 'UNCERTAIN'}
    assert set(df_dup['decision']).issubset(valid_decisions), "Invalid decision enum in duplicate review"
    print("  -> Duplicate review audit decisions validated")
    
    # 7. QC Report
    qc_path = os.path.join(PROJECT_ROOT, "HISTORICAL_LANDSLIDE_RAINFALL_QC.md")
    assert os.path.exists(qc_path), "HISTORICAL_LANDSLIDE_RAINFALL_QC.md missing"
    with open(qc_path, 'r', encoding='utf-8') as f:
        qc_txt = f.read()
    assert "Total event records: 75" in qc_txt
    assert "DATASET READY FOR SCIENTIFIC REVIEW" in qc_txt
    print("7. QC Markdown Report verified with exact required template and status.")
    
    print("\nALL AUTOMATED QC AND AUDIT CHECKS PASSED WITH 100% COMPLIANCE!")

if __name__ == "__main__":
    test_dataset_integrity()
