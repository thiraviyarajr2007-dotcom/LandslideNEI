from pathlib import Path
import hashlib
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "cwc_telemetry_hourly"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_ROOT / "cwc_rainfall_features.csv"
REPORT_FILE = PROCESSED_ROOT / "cwc_preprocess_report.json"

# Approximate Northeast India bounding box.
NER_LAT_MIN = 21.5
NER_LAT_MAX = 30.0
NER_LON_MIN = 88.0
NER_LON_MAX = 98.0

# Rainfall values above this are retained but flagged.
EXTREME_RAINFALL_MM = 100.0

# Coverage is a data-quality indicator, not a scientific rainfall threshold.
MIN_COVERAGE_FOR_FEATURE = 0.75

EXPECTED_HOURS = {
    "24h": 24,
    "3d": 72,
    "7d": 168,
}


# ============================================================
# COLUMN MAPPING
# ============================================================

COLUMN_MAP = {
    "SlNo": "sl_no",
    "Station": "station",
    "Agency": "agency",
    "State LGD Code": "state_lgd_code",
    "State": "state",
    "District LGD Code": "district_lgd_code",
    "District": "district",
    "Tehsil": "tehsil",
    "Block": "block",
    "Village": "village",
    "River": "river",
    "Basin": "basin",
    "Tributary": "tributary",
    "Subtributary": "subtributary",
    "SubSubtributary": "subsubtributary",
    "Local River": "local_river",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Data Acquisition Time": "timestamp",
    "Telemetry Hourly Rainfall (mm)": "rainfall_1h",
}


REQUIRED_COLUMNS = set(COLUMN_MAP.keys())


# ============================================================
# HELPERS
# ============================================================

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_text(value):
    if pd.isna(value):
        return np.nan

    value = str(value).strip()

    if not value:
        return np.nan

    return value


def parse_period_from_path(path: Path) -> str:
    """
    Folder names are metadata only.
    Actual timestamps are always used for temporal interpretation.
    """

    folder = path.parent.name

    if folder == "1991_2020":
        return "1991_2020_source"

    if folder == "2021_2025":
        return "2021_2025_source"

    if folder == "2026_2030":
        return "2026_2030_source"

    return folder


def classify_rainfall(value):
    if pd.isna(value):
        return "MISSING"

    if value < 0:
        return "INVALID_NEGATIVE"

    if value > EXTREME_RAINFALL_MM:
        return "EXTREME_REVIEW"

    if value > 50:
        return "HIGH_REVIEW"

    if value > 0:
        return "VALID"

    return "ZERO"


# ============================================================
# LOAD ONE FILE
# ============================================================

def load_cwc_file(path: Path):
    result = {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "sha256": file_sha256(path),
        "rows": 0,
        "valid_rows": 0,
        "invalid_timestamp": 0,
        "invalid_coordinates": 0,
        "missing_rainfall": 0,
        "negative_rainfall": 0,
        "extreme_rainfall": 0,
        "error": None,
    }

    try:
        df = pd.read_csv(path, low_memory=False)

        result["rows"] = len(df)

        missing_columns = REQUIRED_COLUMNS - set(df.columns)

        if missing_columns:
            result["error"] = (
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )
            return None, result

        df = df.rename(columns=COLUMN_MAP)

        # Keep only columns needed by the ML pipeline plus metadata.
        keep_columns = list(COLUMN_MAP.values())
        df = df[keep_columns].copy()

        # ----------------------------------------------------
        # Text normalization
        # ----------------------------------------------------

        text_columns = [
            "station",
            "agency",
            "state",
            "district",
            "tehsil",
            "block",
            "village",
            "river",
            "basin",
            "tributary",
            "subtributary",
            "subsubtributary",
            "local_river",
        ]

        for column in text_columns:
            df[column] = df[column].map(normalize_text)

        # ----------------------------------------------------
        # Numeric conversion
        # ----------------------------------------------------

        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["rainfall_1h"] = pd.to_numeric(
            df["rainfall_1h"],
            errors="coerce",
        )

        # ----------------------------------------------------
        # Timestamp conversion
        # ----------------------------------------------------

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
            dayfirst=True,
        )

        result["invalid_timestamp"] = int(df["timestamp"].isna().sum())

        # ----------------------------------------------------
        # Coordinate validation
        # ----------------------------------------------------

        coordinate_valid = (
            df["latitude"].between(NER_LAT_MIN, NER_LAT_MAX)
            & df["longitude"].between(NER_LON_MIN, NER_LON_MAX)
        )

        coordinate_missing = (
            df["latitude"].isna()
            | df["longitude"].isna()
        )

        invalid_coordinate_mask = ~coordinate_valid | coordinate_missing

        result["invalid_coordinates"] = int(
            invalid_coordinate_mask.sum()
        )

        # ----------------------------------------------------
        # Rainfall QC
        # ----------------------------------------------------

        result["missing_rainfall"] = int(
            df["rainfall_1h"].isna().sum()
        )

        result["negative_rainfall"] = int(
            (df["rainfall_1h"] < 0).sum()
        )

        result["extreme_rainfall"] = int(
            (df["rainfall_1h"] > EXTREME_RAINFALL_MM).sum()
        )

        # ----------------------------------------------------
        # Source metadata
        # ----------------------------------------------------

        df["source_file"] = path.name
        df["source_period"] = parse_period_from_path(path)

        # ----------------------------------------------------
        # Quality flag
        # ----------------------------------------------------

        df["rainfall_quality"] = df["rainfall_1h"].map(
            classify_rainfall
        )

        # Invalid timestamps are retained for audit.
        # They are excluded from temporal feature generation.
        df["timestamp_valid"] = df["timestamp"].notna()

        df["coordinates_valid"] = coordinate_valid

        # ML feature generation requires valid timestamp,
        # coordinates and non-negative rainfall.
        usable = (
            df["timestamp_valid"]
            & df["coordinates_valid"]
            & (
                df["rainfall_1h"].isna()
                | (df["rainfall_1h"] >= 0)
            )
        )

        result["valid_rows"] = int(usable.sum())

        return df, result

    except Exception as exc:
        result["error"] = str(exc)
        return None, result


# ============================================================
# EXACT DUPLICATE FILE DETECTION
# ============================================================

def find_unique_files(csv_files):
    hash_to_file = {}
    duplicate_files = []

    for path in sorted(csv_files):
        digest = file_sha256(path)

        if digest in hash_to_file:
            duplicate_files.append({
                "duplicate": str(path.relative_to(PROJECT_ROOT)),
                "original": str(
                    hash_to_file[digest].relative_to(PROJECT_ROOT)
                ),
                "sha256": digest,
            })
        else:
            hash_to_file[digest] = path

    unique_files = list(hash_to_file.values())

    return unique_files, duplicate_files


# ============================================================
# ROLLING RAINFALL FEATURES
# ============================================================

def add_rainfall_features(group):
    """
    Generate rainfall totals using time-based windows.

    Missing observations are NOT converted to zero.

    Coverage is calculated separately so that a low-observation
    window cannot silently look like a complete rainfall window.
    """

    group = group.sort_values("timestamp").copy()

    group = group.set_index("timestamp")

    rainfall = group["rainfall_1h"]

    # Sum available observations.
    group["rainfall_24h_sum"] = rainfall.rolling(
        "24h",
        min_periods=1,
    ).sum()

    group["rainfall_3d_sum"] = rainfall.rolling(
        "72h",
        min_periods=1,
    ).sum()

    group["rainfall_7d_sum"] = rainfall.rolling(
        "168h",
        min_periods=1,
    ).sum()

    # Number of observations available in each window.
    group["rainfall_obs_24h"] = rainfall.rolling(
        "24h",
        min_periods=1,
    ).count()

    group["rainfall_obs_3d"] = rainfall.rolling(
        "72h",
        min_periods=1,
    ).count()

    group["rainfall_obs_7d"] = rainfall.rolling(
        "168h",
        min_periods=1,
    ).count()

    # Coverage ratio.
    group["coverage_24h"] = (
        group["rainfall_obs_24h"] / EXPECTED_HOURS["24h"]
    ).clip(upper=1.0)

    group["coverage_3d"] = (
        group["rainfall_obs_3d"] / EXPECTED_HOURS["3d"]
    ).clip(upper=1.0)

    group["coverage_7d"] = (
        group["rainfall_obs_7d"] / EXPECTED_HOURS["7d"]
    ).clip(upper=1.0)

    # Missing indicators.
    group["missing_24h"] = (
        group["coverage_24h"] < MIN_COVERAGE_FOR_FEATURE
    )

    group["missing_3d"] = (
        group["coverage_3d"] < MIN_COVERAGE_FOR_FEATURE
    )

    group["missing_7d"] = (
        group["coverage_7d"] < MIN_COVERAGE_FOR_FEATURE
    )

    # ML-ready totals.
    # If coverage is insufficient, do not pretend the value
    # represents a complete time window.
    group["rainfall_24h"] = group["rainfall_24h_sum"].where(
        group["coverage_24h"] >= MIN_COVERAGE_FOR_FEATURE
    )

    group["rainfall_3d"] = group["rainfall_3d_sum"].where(
        group["coverage_3d"] >= MIN_COVERAGE_FOR_FEATURE
    )

    group["rainfall_7d"] = group["rainfall_7d_sum"].where(
        group["coverage_7d"] >= MIN_COVERAGE_FOR_FEATURE
    )

    group = group.reset_index()

    return group


# ============================================================
# MAIN PROCESS
# ============================================================

def main():
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(RAW_ROOT.rglob("*.csv"))

    print("=" * 70)
    print("CWC RAINFALL PREPROCESSING")
    print("=" * 70)

    print(f"Project root : {PROJECT_ROOT}")
    print(f"Raw root     : {RAW_ROOT}")
    print(f"CSV files    : {len(csv_files)}")
    print()

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found under {RAW_ROOT}"
        )

    # --------------------------------------------------------
    # Exact duplicate file detection
    # --------------------------------------------------------

    unique_files, duplicate_files = find_unique_files(csv_files)

    print(f"Unique files : {len(unique_files)}")
    print(f"Duplicates   : {len(duplicate_files)}")
    print()

    if duplicate_files:
        print("WARNING: Exact duplicate files detected:")
        for item in duplicate_files:
            print(
                f"  {item['duplicate']} "
                f"== {item['original']}"
            )

        print()

    # --------------------------------------------------------
    # Load all unique files
    # --------------------------------------------------------

    frames = []
    file_reports = []

    for path in unique_files:
        print(f"Processing: {path.name}")

        frame, report = load_cwc_file(path)

        file_reports.append(report)

        if frame is not None and len(frame) > 0:
            frames.append(frame)

    if not frames:
        raise RuntimeError(
            "No usable CWC records were loaded."
        )

    data = pd.concat(
        frames,
        ignore_index=True,
    )

    # --------------------------------------------------------
    # Remove invalid temporal rows from feature generation
    # --------------------------------------------------------

    before = len(data)

    feature_data = data[
        data["timestamp_valid"]
        & data["coordinates_valid"]
    ].copy()

    removed_invalid = before - len(feature_data)

    # Negative rainfall is retained in the audit data,
    # but excluded from ML rainfall aggregation.
    negative_mask = feature_data["rainfall_1h"] < 0

    negative_rows = int(negative_mask.sum())

    feature_data = feature_data[
        ~negative_mask
    ].copy()

    # --------------------------------------------------------
    # Station identity
    # --------------------------------------------------------

    feature_data["station_key"] = (
        feature_data["state"].fillna("UNKNOWN").astype(str)
        + "::"
        + feature_data["station"].fillna("UNKNOWN").astype(str)
    )

    # --------------------------------------------------------
    # Station + timestamp collision audit
    # --------------------------------------------------------

    collision_counts = (
        feature_data
        .groupby(["station_key", "timestamp"])
        .size()
        .reset_index(name="row_count")
    )

    collisions = collision_counts[
        collision_counts["row_count"] > 1
    ].copy()

    collision_row_count = int(
        collisions["row_count"].sum()
    ) if not collisions.empty else 0

    print(
        f"Station+timestamp collision groups: "
        f"{len(collisions)}"
    )

    print(
        f"Rows involved in collisions: "
        f"{collision_row_count}"
    )

    # --------------------------------------------------------
    # Do NOT silently choose one row when collisions occur.
    #
    # If duplicate station/timestamp records have identical
    # rainfall values, they can safely be collapsed.
    #
    # If rainfall differs, preserve the rows and flag them.
    # --------------------------------------------------------

    duplicate_group_columns = [
        "station_key",
        "timestamp",
    ]

    rainfall_variation = (
        feature_data
        .groupby(duplicate_group_columns)["rainfall_1h"]
        .nunique(dropna=False)
        .reset_index(name="rainfall_value_count")
    )

    feature_data = feature_data.merge(
        rainfall_variation,
        on=duplicate_group_columns,
        how="left",
    )

    feature_data["timestamp_collision"] = (
        feature_data["rainfall_value_count"] > 1
    )

    # Identical station/timestamp/rainfall records are exact
    # measurement duplicates and can be collapsed.
    exact_measurement_duplicates = feature_data.duplicated(
        subset=[
            "station_key",
            "timestamp",
            "rainfall_1h",
        ],
        keep="first",
    )

    collapsed_measurement_duplicates = int(
        exact_measurement_duplicates.sum()
    )

    feature_data = feature_data[
        ~exact_measurement_duplicates
    ].copy()

    # --------------------------------------------------------
    # Sort before rolling windows
    # --------------------------------------------------------

    feature_data = feature_data.sort_values(
        ["station_key", "timestamp"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Rolling features
    # --------------------------------------------------------

    print()
    print("Generating rainfall windows...")

    feature_data = (
        feature_data
        .groupby(
            "station_key",
            group_keys=True,
        )
        .apply(
            add_rainfall_features,
            include_groups=False,
        )
        .reset_index(level=0)
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Final quality flag
    # --------------------------------------------------------

    feature_data["quality_flag"] = "OK"

    feature_data.loc[
        feature_data["rainfall_1h"].isna(),
        "quality_flag",
    ] = "MISSING_RAINFALL"

    feature_data.loc[
        feature_data["rainfall_1h"] > EXTREME_RAINFALL_MM,
        "quality_flag",
    ] = "EXTREME_REVIEW"

    feature_data.loc[
        feature_data["timestamp_collision"],
        "quality_flag",
    ] = "TIMESTAMP_COLLISION"

    feature_data.loc[
        feature_data["missing_24h"],
        "quality_flag",
    ] = "LOW_24H_COVERAGE"

    # Keep extreme observations.
    # Keep raw rainfall.
    # Keep coverage metadata.
    # Do not clip or replace values.

    # --------------------------------------------------------
    # Actual date span
    # --------------------------------------------------------

    min_timestamp = feature_data["timestamp"].min()
    max_timestamp = feature_data["timestamp"].max()

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_columns = [
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
        "timestamp_collision",
        "quality_flag",
        "source_file",
        "source_period",
    ]

    feature_data[output_columns].to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "configuration": {
            "ner_bbox": {
                "lat_min": NER_LAT_MIN,
                "lat_max": NER_LAT_MAX,
                "lon_min": NER_LON_MIN,
                "lon_max": NER_LON_MAX,
            },
            "extreme_rainfall_mm": EXTREME_RAINFALL_MM,
            "min_coverage_for_feature": MIN_COVERAGE_FOR_FEATURE,
        },
        "input": {
            "csv_files_found": len(csv_files),
            "unique_files_processed": len(unique_files),
            "exact_duplicate_files": len(duplicate_files),
            "duplicate_files": duplicate_files,
        },
        "processing": {
            "raw_rows_loaded": int(before),
            "rows_removed_invalid_timestamp_or_coordinates": int(
                removed_invalid
            ),
            "negative_rows_excluded_from_aggregation": negative_rows,
            "identical_measurement_duplicates_collapsed": (
                collapsed_measurement_duplicates
            ),
            "station_timestamp_collision_groups": (
                len(collisions)
            ),
            "rows_after_processing": int(len(feature_data)),
        },
        "output": {
            "file": str(
                OUTPUT_FILE.relative_to(PROJECT_ROOT)
            ),
            "rows": int(len(feature_data)),
            "columns": output_columns,
            "min_timestamp": (
                min_timestamp.isoformat()
                if pd.notna(min_timestamp)
                else None
            ),
            "max_timestamp": (
                max_timestamp.isoformat()
                if pd.notna(max_timestamp)
                else None
            ),
        },
        "rainfall": {
            "missing_rainfall": int(
                feature_data["rainfall_1h"].isna().sum()
            ),
            "extreme_rainfall": int(
                (feature_data["rainfall_1h"] > EXTREME_RAINFALL_MM).sum()
            ),
            "maximum_rainfall_1h": (
                float(feature_data["rainfall_1h"].max())
                if feature_data["rainfall_1h"].notna().any()
                else None
            ),
        },
        "stations": {
            "unique_station_keys": int(
                feature_data["station_key"].nunique()
            ),
            "states": sorted(
                feature_data["state"].dropna().unique().tolist()
            ),
        },
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("PREPROCESSING COMPLETE")
    print("=" * 70)

    print(f"Rows loaded              : {before:,}")
    print(
        "Invalid timestamp/coords : "
        f"{removed_invalid:,}"
    )
    print(
        "Negative excluded        : "
        f"{negative_rows:,}"
    )
    print(
        "Exact measurement dupes  : "
        f"{collapsed_measurement_duplicates:,}"
    )
    print(
        "Timestamp collision groups: "
        f"{len(collisions):,}"
    )
    print(
        f"Final rows               : "
        f"{len(feature_data):,}"
    )

    print(
        f"Stations                 : "
        f"{feature_data['station_key'].nunique():,}"
    )

    print(
        f"Date range               : "
        f"{min_timestamp} -> {max_timestamp}"
    )

    print()
    print(f"Output : {OUTPUT_FILE}")
    print(f"Report : {REPORT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
