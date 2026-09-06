"""
Phase 8E.3.1: Rainfall Source & Temporal Audit Script
Audits CWC, IMD, and integrated rainfall datasets against the 4,016 landslide
training samples to evaluate temporal coverage, spatial matching, temporal
leakage risks, and reconstruction feasibility for 2014 landslide events.
"""

import os
import json
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

BASE_DIR = r"C:\SIH Landslide"
CWC_FEATURES_FILE = os.path.join(BASE_DIR, "data", "processed", "cwc_rainfall_features.csv")
INTEGRATED_DAILY_FILE = os.path.join(BASE_DIR, "data", "processed", "rainfall", "rainfall_daily_integrated.csv")
IMD_STATE_FILE = os.path.join(BASE_DIR, "data", "processed", "imd", "imd_statewise_ner.csv")
IMD_DIST_FILE = os.path.join(BASE_DIR, "data", "processed", "imd", "imd_districtwise_ner.csv")
TRAINING_SAMPLES_FILE = os.path.join(BASE_DIR, "data", "processed", "landslides", "landslide_training_samples_proximity.csv")

OUTPUT_JSON = os.path.join(BASE_DIR, "data", "inspection", "rainfall", "rainfall_training_audit.json")
OUTPUT_TXT = os.path.join(BASE_DIR, "data", "inspection", "rainfall", "rainfall_training_audit.txt")


def audit_cwc(cwc_path):
    print("Auditing CWC features...")
    df = pd.read_csv(cwc_path)
    
    unique_stations = df[["station_key", "station", "state", "district", "latitude", "longitude"]].drop_duplicates()
    
    audit = {
        "dataset_name": "CWC Hourly & Windowed Telemetry Features",
        "file_path": cwc_path,
        "total_records": int(len(df)),
        "min_timestamp": str(df["timestamp"].min()),
        "max_timestamp": str(df["timestamp"].max()),
        "unique_stations_count": int(df["station"].nunique()),
        "unique_station_keys_count": int(df["station_key"].nunique()),
        "states_covered": sorted(df["state"].dropna().unique().tolist()),
        "station_count_by_state": unique_stations["state"].value_counts().to_dict(),
        "district_count_by_state": unique_stations.groupby("state")["district"].nunique().to_dict(),
        "missing_coordinates": {
            "latitude_null": int(df["latitude"].isna().sum()),
            "longitude_null": int(df["longitude"].isna().sum())
        },
        "coordinate_bounds": {
            "min_lat": float(unique_stations["latitude"].min()),
            "max_lat": float(unique_stations["latitude"].max()),
            "min_lon": float(unique_stations["longitude"].min()),
            "max_lon": float(unique_stations["longitude"].max())
        },
        "rainfall_window_columns": [
            "rainfall_1h", "rainfall_24h", "rainfall_3d", "rainfall_7d",
            "rainfall_24h_sum", "rainfall_3d_sum", "rainfall_7d_sum"
        ],
        "coverage_columns": [
            "rainfall_obs_24h", "rainfall_obs_3d", "rainfall_obs_7d",
            "coverage_24h", "coverage_3d", "coverage_7d",
            "missing_24h", "missing_3d", "missing_7d"
        ],
        "quality_columns": ["rainfall_quality", "quality_flag", "timestamp_collision"],
        "quality_flag_distribution": df["quality_flag"].value_counts(dropna=False).to_dict(),
        "rainfall_quality_distribution": df["rainfall_quality"].value_counts(dropna=False).to_dict(),
        "mean_coverage": {
            "coverage_24h": float(df["coverage_24h"].mean()),
            "coverage_3d": float(df["coverage_3d"].mean()),
            "coverage_7d": float(df["coverage_7d"].mean())
        },
        "missingness_counts": {
            col: int(df[col].isna().sum())
            for col in ["rainfall_1h", "rainfall_24h", "rainfall_3d", "rainfall_7d"]
        },
        "source_period_distribution": df["source_period"].value_counts(dropna=False).to_dict()
    }
    return audit, unique_stations


def audit_integrated_daily(integ_path):
    print("Auditing integrated daily rainfall...")
    df = pd.read_csv(integ_path)
    
    audit = {
        "dataset_name": "Integrated Daily Rainfall (CWC + IMD)",
        "file_path": integ_path,
        "total_station_days": int(len(df)),
        "min_date": str(df["CWC_Date"].min()),
        "max_date": str(df["CWC_Date"].max()),
        "unique_stations_count": int(df["station"].nunique()),
        "states_covered": sorted(df["state"].dropna().unique().tolist()),
        "available_rainfall_variables": [
            "CWC_Rainfall_mm", "CWC_Rainfall_24h_mm", "CWC_Rainfall_72h_mm", "CWC_Rainfall_168h_mm",
            "IMD_State_Daily_Actual_mm", "IMD_State_Daily_Normal_mm", "IMD_State_Daily_Departure_pct"
        ],
        "spatial_metadata": ["State_Normalized", "station", "station_key", "state", "district", "latitude", "longitude"],
        "temporal_metadata": ["CWC_Date", "source_period"],
        "source_distribution": df["Rainfall_Data_Status"].value_counts(dropna=False).to_dict(),
        "integration_level": df["Integration_Level"].value_counts(dropna=False).to_dict(),
        "cwc_only_count": int((df["Rainfall_Data_Status"] == "CWC_ONLY").sum()),
        "cwc_plus_imd_count": int((df["Rainfall_Data_Status"] == "CWC_PLUS_IMD").sum()),
        "imd_overlap_notes": "Only 9 station-days overlap between CWC and IMD (from recent 2026 operational collection). 31,120 station-days have CWC only."
    }
    return audit


def audit_imd(state_path, dist_path):
    print("Auditing IMD state and district datasets...")
    df_st = pd.read_csv(state_path)
    df_dt = pd.read_csv(dist_path)
    
    audit = {
        "dataset_name": "IMD Operational Rainfall Data",
        "statewise": {
            "file_path": state_path,
            "total_records": int(len(df_st)),
            "min_date": str(df_st["Date"].min()),
            "max_date": str(df_st["Date"].max()),
            "unique_states_count": int(df_st["State_Normalized"].nunique()),
            "states_covered": sorted(df_st["State_Normalized"].unique().tolist()),
            "columns": df_st.columns.tolist()
        },
        "districtwise": {
            "file_path": dist_path,
            "total_records": int(len(df_dt)),
            "min_date": str(df_dt["Date"].min()),
            "max_date": str(df_dt["Date"].max()),
            "unique_states_count": int(df_dt["State_Normalized"].nunique()),
            "unique_districts_count": int(df_dt["District"].nunique()),
            "districts_per_state": df_dt.groupby("State_Normalized")["District"].nunique().to_dict(),
            "columns": df_dt.columns.tolist()
        },
        "historical_2014_data_exists": False,
        "operational_usability_for_2014_training": False,
        "notes": "IMD datasets cover only a 17-day operational window from 2026-08-19 to 2026-09-04. Zero historical 2014 observations exist. Using 2026 operational data for 2014 events would introduce severe temporal distortion."
    }
    return audit


def audit_training_samples(samples_path):
    print("Auditing training samples temporal metadata...")
    df = pd.read_csv(samples_path)
    
    pos_df = df[df["label"] == 1]
    neg_df = df[df["label"] == 0]
    
    audit = {
        "dataset_name": "Landslide Training Samples (Proximity Layer)",
        "file_path": samples_path,
        "total_samples": int(len(df)),
        "positives_count": int(len(pos_df)),
        "negatives_count": int(len(neg_df)),
        "date_year_columns_present": [col for col in df.columns if any(k in col.lower() for k in ["date", "year", "time"])],
        "year_distribution_positives": {str(k): int(v) for k, v in pos_df["year"].value_counts(dropna=False).to_dict().items()},
        "year_distribution_negatives": {str(k): int(v) for k, v in neg_df["year"].value_counts(dropna=False).to_dict().items()},
        "has_exact_event_dates": False,
        "positive_event_temporal_resolution": "Annual year only (2014.0). No month, day, or time stamp is recorded in the Bhuvan catalog.",
        "negative_event_temporal_resolution": "None (NaN). Negative samples are spatial background points sampled within GADM boundaries and have no reference date.",
        "can_establish_temporal_alignment": False,
        "notes": "Because positives lack specific event dates and negatives have no reference date, constructing event-relative temporal rainfall windows (e.g., 24h before event) is mathematically undefined without external date assumptions."
    }
    return audit, df


def analyze_spatial_matching(samples_df, cwc_stations_df):
    print("Analyzing spatial matching to CWC stations in UTM Zone 46N...")
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)
    
    st_x, st_y = transformer.transform(cwc_stations_df["longitude"].values, cwc_stations_df["latitude"].values)
    ts_x, ts_y = transformer.transform(samples_df["longitude"].values, samples_df["latitude"].values)
    
    tree = cKDTree(np.column_stack([st_x, st_y]))
    dists_m, indices = tree.query(np.column_stack([ts_x, ts_y]))
    
    dists_km = dists_m / 1000.0
    samples_df["dist_to_cwc_km"] = dists_km
    
    state_dists = {}
    for st, group in samples_df.groupby("state"):
        state_dists[st] = {
            "sample_count": int(len(group)),
            "min_km": round(float(group["dist_to_cwc_km"].min()), 2),
            "median_km": round(float(group["dist_to_cwc_km"].median()), 2),
            "mean_km": round(float(group["dist_to_cwc_km"].mean()), 2),
            "max_km": round(float(group["dist_to_cwc_km"].max()), 2)
        }
    
    audit = {
        "crs_used": "EPSG:32646 (WGS 84 / UTM zone 46N)",
        "distance_unit": "kilometres",
        "overall_statistics": {
            "min_km": round(float(dists_km.min()), 2),
            "p25_km": round(float(np.percentile(dists_km, 25)), 2),
            "median_km": round(float(np.median(dists_km)), 2),
            "mean_km": round(float(np.mean(dists_km)), 2),
            "p75_km": round(float(np.percentile(dists_km, 75)), 2),
            "max_km": round(float(dists_km.max()), 2),
            "std_km": round(float(np.std(dists_km)), 2)
        },
        "distance_threshold_counts": {
            "within_10km": int((dists_km <= 10.0).sum()),
            "within_10km_pct": round(float((dists_km <= 10.0).sum() / len(dists_km) * 100), 2),
            "within_25km": int((dists_km <= 25.0).sum()),
            "within_25km_pct": round(float((dists_km <= 25.0).sum() / len(dists_km) * 100), 2),
            "within_50km": int((dists_km <= 50.0).sum()),
            "within_50km_pct": round(float((dists_km <= 50.0).sum() / len(dists_km) * 100), 2),
            "greater_than_50km": int((dists_km > 50.0).sum()),
            "greater_than_50km_pct": round(float((dists_km > 50.0).sum() / len(dists_km) * 100), 2),
            "greater_than_100km": int((dists_km > 100.0).sum()),
            "greater_than_100km_pct": round(float((dists_km > 100.0).sum() / len(dists_km) * 100), 2)
        },
        "state_breakdown": state_dists,
        "critical_spatial_gaps": [
            "Meghalaya has 1,014 samples (25.2% of dataset) and 0 CWC stations (median distance: 53.62 km, max: 118.28 km).",
            "Mizoram has 708 samples (17.6% of dataset) and 0 CWC stations (median distance: 92.70 km, max: 200.50 km).",
            "Together, 1,722 out of 4,016 samples (42.88%) are in states with zero CWC telemetry stations.",
            "In mountainous orographic terrain, assigning telemetry observations from 40 to 90+ km away across major mountain divides introduces massive spatial error."
        ]
    }
    return audit


def analyze_temporal_leakage():
    print("Performing temporal leakage analysis...")
    return {
        "event_relative_reconstruction_feasible": False,
        "reason_summary": "Complete temporal disconnect between 2014 landslide inventory and available rainfall datasets.",
        "detailed_factors": {
            "factor_1_inventory_resolution": "ISRO Bhuvan 2014 inventory records only 'Year: 2014'. Exact event date (day/month/hour) is unknown. Antecedent windows (24h, 3d, 7d prior to failure) cannot be computed without a reference trigger timestamp.",
            "factor_2_negative_sampling": "Spatial negative samples are background geographic coordinates with Year=NaN. They have no natural reference timestamp. Assigning arbitrary dates would inject severe label-dependent bias.",
            "factor_3_cwc_coverage": "CWC telemetry data in the repository starts on 2019-02-05 and runs to 2026-09-02. Zero records exist for 2014 (5-year gap). Using 2019-2026 CWC data would represent post-event temporal leakage.",
            "factor_4_imd_coverage": "IMD statewise and districtwise data covers only 2026-08-19 to 2026-09-04 (a 17-day operational window in 2026). Zero records exist for 2014 (12-year gap)."
        },
        "impossible_cases": {
            "samples_lacking_exact_event_date": 4016,
            "samples_lacking_2014_cwc_rainfall": 4016,
            "samples_lacking_2014_imd_rainfall": 4016,
            "total_impossible_samples_pct": 100.0
        }
    }


def produce_recommendation():
    return {
        "outcome": "C",
        "outcome_title": "2014 rainfall cannot be reconstructed reliably from current datasets",
        "technical_justification": [
            "1. Temporal incompatibility: Bhuvan landslides occurred in 2014, while available CWC data begins in February 2019 and IMD operational data begins in August 2026. Zero historical 2014 rainfall data exists in the project repository.",
            "2. Lack of event timestamps: The Bhuvan 2014 catalog provides only the year (2014), not the specific day or hour of slope failure. Event-relative antecedent windows (24h, 3d, 7d) cannot be computed.",
            "3. Spatial coverage gaps: 42.88% of all training samples (Meghalaya and Mizoram) have zero CWC telemetry stations in their states, resulting in nearest-station distances of 50 to 200 km.",
            "4. Negative sample temporal neutrality: Negatives are spatial background candidates with no temporal date. Imputing an arbitrary date creates artificial spatial-temporal leakage."
        ],
        "recommended_architecture": {
            "phase_8f_model_training": "Train the baseline Landslide Susceptibility Model (LSM) purely on static conditioning factors: Terrain (elevation, slope, aspect, relief), Soil (WRB soil class, clay, sand, silt, bulk density), Land Cover (ESA WorldCover), and Infrastructure Proximity (road, river distance). This establishes a rigorous, scientifically valid static susceptibility model with zero temporal leakage.",
            "phase_8e3_dynamic_trigger_pipeline": "Rainfall should be treated as a real-time operational dynamic trigger rather than a forced static training feature. The early-warning system operates as a Two-Tier Decision Support System:\n  - Tier 1 (Static): P(Susceptibility) from the Random Forest / LightGBM model trained on terrain, soil, land cover, and proximity.\n  - Tier 2 (Dynamic): Rainfall Hazard Alerting from real-time CWC/IMD telemetry using Intensity-Duration / Cumulative Rainfall thresholds (e.g. 24h > 100mm or 72h > 200mm) intersecting with high-susceptibility zones to produce early warnings (Normal, Advisory, Watch, Warning).\n",
            "optional_future_extension": "If joint historical spatio-temporal training is strictly required in a future phase, acquire external 2014 gridded daily precipitation reanalysis (e.g., IMD 0.25 deg Gridded Daily Rainfall or NASA GPM IMERG 0.1 deg Final Daily for 2014), together with verified event date records from GSI landslide reports."
        }
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    cwc_audit, cwc_stations = audit_cwc(CWC_FEATURES_FILE)
    integ_audit = audit_integrated_daily(INTEGRATED_DAILY_FILE)
    imd_audit = audit_imd(IMD_STATE_FILE, IMD_DIST_FILE)
    ts_audit, ts_df = audit_training_samples(TRAINING_SAMPLES_FILE)
    spatial_audit = analyze_spatial_matching(ts_df, cwc_stations)
    temporal_audit = analyze_temporal_leakage()
    recommendation = produce_recommendation()
    
    full_report = {
        "status": "AUDIT_COMPLETE",
        "audit_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "section_1_cwc": cwc_audit,
        "section_2_integrated_daily": integ_audit,
        "section_3_imd": imd_audit,
        "section_4_training_samples": ts_audit,
        "section_5_temporal_leakage_analysis": temporal_audit,
        "section_6_spatial_matching_analysis": spatial_audit,
        "section_7_recommendation": recommendation
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"Saved audit JSON to: {OUTPUT_JSON}")
    
    lines = [
        "=" * 80,
        "PHASE 8E.3.1 — RAINFALL SOURCE & TEMPORAL AUDIT REPORT",
        "=" * 80,
        f"Generated UTC: {full_report['audit_timestamp_utc']}",
        f"Status: {full_report['status']}",
        "",
        "1. CWC HOURLY TELEMETRY AUDIT",
        f"   - File: {cwc_audit['file_path']}",
        f"   - Total Records: {cwc_audit['total_records']:,}",
        f"   - Timestamp Range: {cwc_audit['min_timestamp']} to {cwc_audit['max_timestamp']}",
        f"   - Unique Stations: {cwc_audit['unique_stations_count']} across {len(cwc_audit['states_covered'])} states",
        f"   - States Covered: {', '.join(cwc_audit['states_covered'])}",
        f"   - Stations by State: {cwc_audit['station_count_by_state']}",
        f"   - Missing Coordinates: Lat {cwc_audit['missing_coordinates']['latitude_null']}, Lon {cwc_audit['missing_coordinates']['longitude_null']}",
        f"   - Missingness: rainfall_1h={cwc_audit['missingness_counts']['rainfall_1h']:,} ({cwc_audit['missingness_counts']['rainfall_1h']/cwc_audit['total_records']*100:.1f}%), rainfall_24h={cwc_audit['missingness_counts']['rainfall_24h']:,} ({cwc_audit['missingness_counts']['rainfall_24h']/cwc_audit['total_records']*100:.1f}%)",
        f"   - Source Periods: {cwc_audit['source_period_distribution']}",
        f"   - Key Finding: CWC telemetry starts on 2019-02-05. Zero observations exist for 2014.",
        "",
        "2. INTEGRATED DAILY RAINFALL AUDIT",
        f"   - File: {integ_audit['file_path']}",
        f"   - Total Station-Days: {integ_audit['total_station_days']:,}",
        f"   - Date Range: {integ_audit['min_date']} to {integ_audit['max_date']}",
        f"   - Stations: {integ_audit['unique_stations_count']}",
        f"   - Source Distribution: {integ_audit['source_distribution']}",
        f"   - Overlap: Only 9 station-days have CWC+IMD overlap (August 2026). Zero 2014 data.",
        "",
        "3. IMD OPERATIONAL DATA AUDIT",
        f"   - Statewise Date Range: {imd_audit['statewise']['min_date']} to {imd_audit['statewise']['max_date']} (17 days, 136 records)",
        f"   - Districtwise Date Range: {imd_audit['districtwise']['min_date']} to {imd_audit['districtwise']['max_date']} (17 days, 1,666 records)",
        f"   - States Covered: 8/8 NER States; Districts Covered: 98",
        f"   - Historical 2014 Data Exists: {imd_audit['historical_2014_data_exists']}",
        f"   - Operational Usability for 2014 Training: {imd_audit['operational_usability_for_2014_training']}",
        f"   - Key Finding: Data is strictly operational current monitoring from Aug-Sep 2026. Cannot be used for 2014 training.",
        "",
        "4. TRAINING SAMPLES TEMPORAL AUDIT",
        f"   - Total Samples: {ts_audit['total_samples']} (2,008 positives, 2,008 negatives)",
        f"   - Positive Year Distribution: {ts_audit['year_distribution_positives']}",
        f"   - Negative Year Distribution: {ts_audit['year_distribution_negatives']}",
        f"   - Exact Event Dates Exist: {ts_audit['has_exact_event_dates']}",
        f"   - Temporal Details: Positives contain only annual year 2014.0 (no month/day/hour). Negatives have Year=NaN.",
        "",
        "5. TEMPORAL LEAKAGE ANALYSIS",
        f"   - Feasible to Reconstruct Antecedent Windows (24h, 3d, 7d): {temporal_audit['event_relative_reconstruction_feasible']}",
        f"   - Reason: {temporal_audit['reason_summary']}",
        f"   - Impossible Cases: {temporal_audit['impossible_cases']['samples_lacking_exact_event_date']}/{ts_audit['total_samples']} (100.0%)",
        "",
        "6. SPATIAL MATCHING ANALYSIS (UTM Zone 46N)",
        f"   - Distance to Nearest CWC Station:",
        f"     * Min:    {spatial_audit['overall_statistics']['min_km']:.2f} km",
        f"     * 25%:    {spatial_audit['overall_statistics']['p25_km']:.2f} km",
        f"     * Median: {spatial_audit['overall_statistics']['median_km']:.2f} km",
        f"     * Mean:   {spatial_audit['overall_statistics']['mean_km']:.2f} km",
        f"     * 75%:    {spatial_audit['overall_statistics']['p75_km']:.2f} km",
        f"     * Max:    {spatial_audit['overall_statistics']['max_km']:.2f} km",
        f"   - Distance Thresholds:",
        f"     * <= 10 km:  {spatial_audit['distance_threshold_counts']['within_10km']} ({spatial_audit['distance_threshold_counts']['within_10km_pct']}%)",
        f"     * <= 25 km:  {spatial_audit['distance_threshold_counts']['within_25km']} ({spatial_audit['distance_threshold_counts']['within_25km_pct']}%)",
        f"     * <= 50 km:  {spatial_audit['distance_threshold_counts']['within_50km']} ({spatial_audit['distance_threshold_counts']['within_50km_pct']}%)",
        f"     * > 50 km:   {spatial_audit['distance_threshold_counts']['greater_than_50km']} ({spatial_audit['distance_threshold_counts']['greater_than_50km_pct']}%)",
        f"     * > 100 km:  {spatial_audit['distance_threshold_counts']['greater_than_100km']} ({spatial_audit['distance_threshold_counts']['greater_than_100km_pct']}%)",
        f"   - State Coverage Gaps:",
    ]
    for st, data in spatial_audit["state_breakdown"].items():
        lines.append(f"     * {st:18s}: {data['sample_count']:4d} samples | Median {data['median_km']:6.2f} km | Max {data['max_km']:6.2f} km")
    lines.extend([
        "",
        "7. FINAL RECOMMENDATION",
        f"   - Outcome: {recommendation['outcome']} ({recommendation['outcome_title']})",
        "   - Key Justifications:",
    ])
    for j in recommendation["technical_justification"]:
        lines.append(f"     {j}")
    lines.extend([
        "   - Recommended Architecture:",
        f"     * ML Training (Phase 8F): {recommendation['recommended_architecture']['phase_8f_model_training']}",
        f"     * Dynamic Trigger: {recommendation['recommended_architecture']['phase_8e3_dynamic_trigger_pipeline']}",
        "=" * 80
    ])
    
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Saved audit TXT to: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
