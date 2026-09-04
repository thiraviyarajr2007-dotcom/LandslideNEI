import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CWC_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cwc_rainfall_features.csv"
)

IMD_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "imd"
    / "imd_districtwise_ner.csv"
)

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "rainfall"
)

OUTPUT_FILE = OUTPUT_ROOT / "rainfall_daily_integrated.csv"
REPORT_FILE = OUTPUT_ROOT / "rainfall_integration_report.json"


NER_STATES = {
    "ARUNACHAL PRADESH",
    "ASSAM",
    "MANIPUR",
    "MEGHALAYA",
    "MIZORAM",
    "NAGALAND",
    "SIKKIM",
    "TRIPURA",
}


# ============================================================
# HELPERS
# ============================================================

def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_state(value):
    if pd.isna(value):
        return None

    value = str(value).strip().upper()
    value = " ".join(value.split())
    value = value.replace("\r", "").replace("\n", "")

    return value


def require_columns(df, columns, dataset_name):
    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name}: missing required columns: "
            + ", ".join(missing)
        )


# ============================================================
# LOAD CWC
# ============================================================

def load_cwc():

    print()
    print("=" * 80)
    print("LOADING CWC PROCESSED RAINFALL")
    print("=" * 80)

    if not CWC_FILE.exists():
        raise FileNotFoundError(
            f"CWC processed file not found: {CWC_FILE}"
        )

    df = pd.read_csv(
        CWC_FILE,
        low_memory=False,
    )

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    require_columns(
        df,
        [
            "station_key",
            "station",
            "state",
            "district",
            "latitude",
            "longitude",
            "timestamp",
            "rainfall_1h",
            "rainfall_24h",
            "rainfall_3d",
            "rainfall_7d",
            "rainfall_24h_sum",
            "rainfall_3d_sum",
            "rainfall_7d_sum",
            "rainfall_obs_24h",
            "rainfall_obs_3d",
            "rainfall_obs_7d",
            "coverage_24h",
            "coverage_3d",
            "coverage_7d",
            "missing_24h",
            "missing_3d",
            "missing_7d",
            "rainfall_quality",
            "quality_flag",
            "source_file",
            "source_period",
        ],
        "CWC",
    )

    df["State_Normalized"] = df["state"].map(
        normalize_state
    )

    df = df.loc[
        df["State_Normalized"].isin(NER_STATES)
    ].copy()

    df["CWC_Timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["CWC_Date"] = (
        df["CWC_Timestamp"]
        .dt.floor("D")
    )

    df["rainfall_1h"] = pd.to_numeric(
        df["rainfall_1h"],
        errors="coerce",
    )

    print(
        f"\nNER CWC rows retained: {len(df):,}"
    )

    print(
        f"CWC date range: "
        f"{df['CWC_Date'].min()} -> "
        f"{df['CWC_Date'].max()}"
    )

    return df


# ============================================================
# LOAD IMD
# ============================================================

def load_imd():

    print()
    print("=" * 80)
    print("LOADING IMD DISTRICTWISE RAINFALL")
    print("=" * 80)

    if not IMD_FILE.exists():
        raise FileNotFoundError(
            f"IMD filtered file not found: {IMD_FILE}"
        )

    df = pd.read_csv(
        IMD_FILE,
        low_memory=False,
    )

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    require_columns(
        df,
        [
            "State",
            "District",
            "Date",
            "Daily Actual",
            "Daily Normal",
            "Daily Departure Per",
        ],
        "IMD",
    )

    df["State_Normalized"] = (
        df["State"].map(normalize_state)
    )

    invalid_states = set(
        df["State_Normalized"].dropna().unique()
    ) - NER_STATES

    if invalid_states:
        raise RuntimeError(
            "IMD filtered dataset contains non-NER states: "
            + ", ".join(sorted(invalid_states))
        )

    df["IMD_Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce",
    ).dt.floor("D")

    df["IMD_Daily_Actual_mm"] = pd.to_numeric(
        df["Daily Actual"],
        errors="coerce",
    )

    df["IMD_Daily_Normal_mm"] = pd.to_numeric(
        df["Daily Normal"],
        errors="coerce",
    )

    df["IMD_Daily_Departure_pct"] = pd.to_numeric(
        df["Daily Departure Per"],
        errors="coerce",
    )

    df["District_Normalized"] = (
        df["District"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df = df[
        [
            "State",
            "State_Normalized",
            "District",
            "District_Normalized",
            "IMD_Date",
            "IMD_Daily_Actual_mm",
            "IMD_Daily_Normal_mm",
            "IMD_Daily_Departure_pct",
            "Daily Category",
        ]
    ].copy()

    duplicate_count = int(
        df.duplicated(
            subset=[
                "State_Normalized",
                "District_Normalized",
                "IMD_Date",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_count:
        raise RuntimeError(
            "IMD district/date key duplicates detected: "
            f"{duplicate_count:,}"
        )

    print(
        f"NER IMD rows retained: {len(df):,}"
    )

    print(
        f"IMD date range: "
        f"{df['IMD_Date'].min()} -> "
        f"{df['IMD_Date'].max()}"
    )

    print(
        f"Unique districts: "
        f"{df['District_Normalized'].nunique():,}"
    )

    return df


# ============================================================
# BUILD DAILY CWC STATION TABLE
# ============================================================

def aggregate_cwc_daily(cwc):

    print()
    print("=" * 80)
    print("AGGREGATING CWC TO STATION-DAY")
    print("=" * 80)

    group_columns = [
        "State_Normalized",
        "station",
        "CWC_Date",
    ]

    aggregation = {
        "station_key": "first",
        "state": "first",
        "district": "first",
        "latitude": "first",
        "longitude": "first",
        "rainfall_1h": "sum",
        "rainfall_24h_sum": "max",
        "rainfall_3d_sum": "max",
        "rainfall_7d_sum": "max",
        "rainfall_24h": "max",
        "rainfall_3d": "max",
        "rainfall_7d": "max",
        "rainfall_obs_24h": "max",
        "rainfall_obs_3d": "max",
        "rainfall_obs_7d": "max",
        "coverage_24h": "min",
        "coverage_3d": "min",
        "coverage_7d": "min",
        "missing_24h": "any",
        "missing_3d": "any",
        "missing_7d": "any",
        "rainfall_quality": "first",
        "quality_flag": "first",
        "source_file": "first",
        "source_period": "first",
    }

    daily = (
        cwc
        .groupby(
            group_columns,
            as_index=False,
            dropna=False,
        )
        .agg(aggregation)
    )

    # Primary rolling rainfall accumulation aliases for compatibility
    daily["CWC_Rainfall_mm"] = daily["rainfall_1h"]
    daily["CWC_Rainfall_24h_mm"] = daily["rainfall_24h_sum"]
    daily["CWC_Rainfall_72h_mm"] = daily["rainfall_3d_sum"]
    daily["CWC_Rainfall_168h_mm"] = daily["rainfall_7d_sum"]

    print(
        f"Station-day rows: {len(daily):,}"
    )

    return daily


# ============================================================
# MATCH CWC STATION DAYS TO IMD DISTRICT DAYS
# ============================================================

def integrate(cwc_daily, imd):

    print()
    print("=" * 80)
    print("BUILDING RAINFALL INTEGRATION TABLE")
    print("=" * 80)

    print(
        "\nIntegration strategy:"
        "\n1. Preserve CWC station-day rainfall and source-supplied district metadata."
        "\n2. Preserve IMD district-day rainfall."
        "\n3. Join only on State + Date for state-level IMD enrichment."
        "\n4. Do not fabricate an IMD district-to-CWC-station spatial mapping."
    )

    state_daily_imd = (
        imd
        .groupby(
            [
                "State_Normalized",
                "IMD_Date",
            ],
            as_index=False,
        )
        .agg(
            IMD_State_Daily_Actual_mm=(
                "IMD_Daily_Actual_mm",
                "mean",
            ),
            IMD_State_Daily_Normal_mm=(
                "IMD_Daily_Normal_mm",
                "mean",
            ),
            IMD_State_Daily_Departure_pct=(
                "IMD_Daily_Departure_pct",
                "mean",
            ),
        )
    )

    integrated = cwc_daily.merge(
        state_daily_imd,
        left_on=[
            "State_Normalized",
            "CWC_Date",
        ],
        right_on=[
            "State_Normalized",
            "IMD_Date",
        ],
        how="left",
        validate="many_to_one",
    )

    integrated = integrated.drop(
        columns=["IMD_Date"]
    )

    integrated["Rainfall_Data_Status"] = (
        integrated[
            "IMD_State_Daily_Actual_mm"
        ]
        .notna()
        .map({
            True: "CWC_PLUS_IMD",
            False: "CWC_ONLY",
        })
    )

    integrated["Integration_Level"] = (
        "STATE_DATE"
    )

    integrated["CWC_Source"] = "CWC"
    integrated["IMD_Source"] = "IMD"

    return integrated


# ============================================================
# VALIDATION
# ============================================================

def validate_output(df, cwc, imd):

    print()
    print("=" * 80)
    print("VALIDATING INTEGRATED DATASET")
    print("=" * 80)

    if df.empty:
        raise RuntimeError(
            "Integrated rainfall dataset is empty."
        )

    if not set(
        df["State_Normalized"].dropna().unique()
    ).issubset(NER_STATES):
        raise RuntimeError(
            "Integrated dataset contains non-NER states."
        )

    if df["CWC_Date"].isna().any():
        raise RuntimeError(
            "Integrated dataset contains invalid CWC dates."
        )

    if df.duplicated(
        subset=[
            "State_Normalized",
            "station",
            "CWC_Date",
        ]
    ).any():
        raise RuntimeError(
            "Duplicate State + Station + Date rows found."
        )

    cwc_dates = set(
        cwc["CWC_Date"].dropna().dt.date
    )

    output_dates = set(
        df["CWC_Date"].dropna().dt.date
    )

    if not output_dates.issubset(cwc_dates):
        raise RuntimeError(
            "Integrated dates outside CWC source coverage."
        )

    print(
        f"Integrated rows: {len(df):,}"
    )

    print(
        f"States: "
        f"{df['State_Normalized'].nunique():,}"
    )

    print(
        f"Stations: "
        f"{df['station'].nunique():,}"
    )

    print(
        f"Date range: "
        f"{df['CWC_Date'].min()} -> "
        f"{df['CWC_Date'].max()}"
    )

    print("\nRows by state:")

    print(
        df["State_Normalized"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nIMD match status:")

    print(
        df["Rainfall_Data_Status"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nMissing-value summary:")

    for column in [
        "station_key",
        "station",
        "state",
        "district",
        "rainfall_quality",
        "quality_flag",
        "source_file",
        "source_period",
        "CWC_Rainfall_mm",
        "CWC_Rainfall_24h_mm",
        "CWC_Rainfall_72h_mm",
        "CWC_Rainfall_168h_mm",
        "rainfall_24h_sum",
        "rainfall_3d_sum",
        "rainfall_7d_sum",
        "coverage_24h",
        "coverage_3d",
        "coverage_7d",
        "IMD_State_Daily_Actual_mm",
        "IMD_State_Daily_Normal_mm",
        "IMD_State_Daily_Departure_pct",
    ]:
        if column in df.columns:
            missing = int(df[column].isna().sum())

            print(
                f"  {column}: "
                f"{missing:,} missing"
            )


# ============================================================
# REPORT
# ============================================================

def build_report(cwc, imd, integrated):

    total_station_days = int(len(integrated))
    station_days_with_imd = int((integrated["Rainfall_Data_Status"] == "CWC_PLUS_IMD").sum())
    station_days_without_imd = int((integrated["Rainfall_Data_Status"] == "CWC_ONLY").sum())
    pct_with_imd = round(
        (station_days_with_imd / total_station_days * 100.0) if total_station_days > 0 else 0.0,
        4
    )

    cwc_min_date = str(integrated["CWC_Date"].min())
    cwc_max_date = str(integrated["CWC_Date"].max())
    imd_min_date = str(imd["IMD_Date"].min())
    imd_max_date = str(imd["IMD_Date"].max())

    overlap_rows = integrated.loc[
        integrated["Rainfall_Data_Status"] == "CWC_PLUS_IMD", "CWC_Date"
    ]
    if not overlap_rows.empty:
        overlap_min_date = str(overlap_rows.min())
        overlap_max_date = str(overlap_rows.max())
    else:
        overlap_min_date = None
        overlap_max_date = None

    report = {
        "generated_at_utc": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "pipeline": (
            "CWC station-day + IMD state-day rainfall "
            "integration and source alignment layer"
        ),
        "ner_states": sorted(NER_STATES),
        "sources": {
            "cwc_processed": {
                "file": str(
                    CWC_FILE.relative_to(PROJECT_ROOT)
                ),
                "sha256": sha256(CWC_FILE),
                "rows": int(len(cwc)),
                "stations": int(cwc["station"].nunique()),
                "states": sorted(cwc["State_Normalized"].unique().tolist()),
                "date_range": {
                    "min": str(cwc["CWC_Date"].min()),
                    "max": str(cwc["CWC_Date"].max()),
                },
            },
            "imd_districtwise_ner": {
                "file": str(
                    IMD_FILE.relative_to(PROJECT_ROOT)
                ),
                "sha256": sha256(IMD_FILE),
                "rows": int(len(imd)),
                "districts": int(imd["District_Normalized"].nunique()),
                "states": sorted(imd["State_Normalized"].unique().tolist()),
                "date_range": {
                    "min": imd_min_date,
                    "max": imd_max_date,
                },
            },
        },
        "output": {
            "file": str(
                OUTPUT_FILE.relative_to(PROJECT_ROOT)
            ),
            "rows": total_station_days,
            "columns": int(len(integrated.columns)),
        },
        "temporal_overlap_metrics": {
            "total_integrated_station_days": total_station_days,
            "station_days_with_imd_match": station_days_with_imd,
            "station_days_without_imd_match": station_days_without_imd,
            "percentage_with_imd_match": pct_with_imd,
            "cwc_date_range": {
                "min": cwc_min_date,
                "max": cwc_max_date,
            },
            "imd_date_range": {
                "min": imd_min_date,
                "max": imd_max_date,
            },
            "overlap_date_range": {
                "min": overlap_min_date,
                "max": overlap_max_date,
            },
            "note": (
                "The current IMD dataset covers only 2026-08-19 to 2026-09-04, "
                "whereas CWC covers 2019-02-05 to 2026-09-02. Only 9 station-days "
                "overlap in this time window. This is a source availability limitation; "
                "IMD provides current monitoring alignment, not historical training coverage."
            ),
        },
        "integration": {
            "method": "state + date",
            "station_to_district_mapping_created": False,
            "cwc_district_preserved": True,
            "raw_sources_modified": False,
        },
        "states_present": sorted(
            integrated["State_Normalized"]
            .dropna()
            .unique()
            .tolist()
        ),
        "status_counts": {
            str(key): int(value)
            for key, value in (
                integrated[
                    "Rainfall_Data_Status"
                ]
                .value_counts()
                .items()
            )
        },
    }

    return report


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("RAINFALL INTEGRATION PIPELINE — PHASE 8B (CORRECTED)")
    print("=" * 80)

    cwc = load_cwc()

    imd = load_imd()

    cwc_daily = aggregate_cwc_daily(
        cwc
    )

    integrated = integrate(
        cwc_daily,
        imd,
    )

    validate_output(
        integrated,
        cwc,
        imd,
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    integrated.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    report = build_report(
        cwc,
        imd,
        integrated,
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("PHASE 8B COMPLETE")
    print("=" * 80)

    print(
        f"Output : {OUTPUT_FILE}"
    )

    print(
        f"Report : {REPORT_FILE}"
    )

    print(
        "\nRaw CWC and IMD datasets were NOT modified."
    )


if __name__ == "__main__":
    main()
