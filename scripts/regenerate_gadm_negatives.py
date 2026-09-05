from pathlib import Path
import json
import random
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASELINE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
    / "landslide_training_samples.csv"
)

BOUNDARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "inspection"
    / "landslide_validation"
    / "gadm41_IND_1.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
)

OUTPUT_FILE = OUTPUT_DIR / "landslide_training_samples_gadm_corrected.csv"
REPORT_FILE = OUTPUT_DIR / "landslide_training_samples_gadm_correction_report.json"

SEED = 20260905
NEGATIVE_BUFFER_METERS = 1000.0
MAX_ATTEMPTS_MULTIPLIER = 500

STATE_NAMES = {
    "AR": "ArunachalPradesh",
    "AS": "Assam",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "SK": "Sikkim",
    "TR": "Tripura",
}


# ============================================================
# HELPERS
# ============================================================

def log(message=""):
    print(message, flush=True)


def utm_epsg(latitude, longitude):
    zone = int((longitude + 180) // 6) + 1
    return 32600 + zone if latitude >= 0 else 32700 + zone


def make_projected_geometry(geometry, source_crs, target_epsg):
    transformer = Transformer.from_crs(
        source_crs,
        f"EPSG:{target_epsg}",
        always_xy=True,
    )
    return transform(transformer.transform, geometry)


def generate_negative_points(
    state_code,
    state_polygon_wgs84,
    positive_points,
    required_count,
    rng,
):
    """
    Generate points strictly inside the intended state polygon.

    Candidates are rejected if they are:
      - outside the state polygon
      - within NEGATIVE_BUFFER_METERS of a known positive coordinate

    This preserves the interpretation:
      spatial negative candidate
    rather than confirmed absence.
    """

    minx, miny, maxx, maxy = state_polygon_wgs84.bounds

    centroid = state_polygon_wgs84.centroid
    epsg = utm_epsg(centroid.y, centroid.x)

    projected_polygon = make_projected_geometry(
        state_polygon_wgs84,
        "EPSG:4326",
        epsg,
    )

    projected_positive_points = []

    for lon, lat in positive_points:
        point = Point(lon, lat)
        projected_positive_points.append(
            make_projected_geometry(point, "EPSG:4326", epsg)
        )

    positive_union = None

    if projected_positive_points:
        from shapely.ops import unary_union

        positive_union = unary_union(
            [
                p.buffer(NEGATIVE_BUFFER_METERS)
                for p in projected_positive_points
            ]
        )

    accepted = []

    max_attempts = required_count * MAX_ATTEMPTS_MULTIPLIER
    attempts = 0

    while len(accepted) < required_count and attempts < max_attempts:
        attempts += 1

        lon = rng.uniform(minx, maxx)
        lat = rng.uniform(miny, maxy)

        candidate_wgs84 = Point(lon, lat)

        # Strict state-polygon containment.
        if not state_polygon_wgs84.contains(candidate_wgs84):
            continue

        candidate_projected = make_projected_geometry(
            candidate_wgs84,
            "EPSG:4326",
            epsg,
        )

        # Keep candidates away from known positive landslide locations.
        if positive_union is not None and positive_union.intersects(
            candidate_projected
        ):
            continue

        accepted.append((lat, lon))

    if len(accepted) < required_count:
        raise RuntimeError(
            f"Could not generate enough negatives for {state_code}. "
            f"Required={required_count}, generated={len(accepted)}, "
            f"attempts={attempts}."
        )

    return accepted, attempts


# ============================================================
# MAIN
# ============================================================

def main():

    log("=" * 70)
    log("GADM-CORRECTED LANDSLIDE NEGATIVE SAMPLE GENERATION")
    log("=" * 70)

    if not BASELINE_FILE.exists():
        raise FileNotFoundError(f"Baseline file not found: {BASELINE_FILE}")

    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(f"GADM boundary file not found: {BOUNDARY_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log()
    log(f"Baseline:  {BASELINE_FILE}")
    log(f"Boundary:  {BOUNDARY_FILE}")
    log(f"Output:    {OUTPUT_FILE}")
    log()

    # --------------------------------------------------------
    # Load baseline
    # --------------------------------------------------------

    df = pd.read_csv(BASELINE_FILE)

    log(f"Baseline rows: {len(df)}")

    required_columns = {
        "sample_id",
        "label",
        "sample_type",
        "source",
        "slide_no",
        "feature_id",
        "state_code",
        "state",
        "district",
        "latitude",
        "longitude",
        "year",
        "triggering",
        "activity",
        "geomorph",
        "lithology",
        "lulc",
        "area_sqm",
        "geometry_type",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Baseline missing required columns: {sorted(missing_columns)}"
        )

    positives = df[df["label"] == 1].copy()

    if len(positives) != 2008:
        raise ValueError(
            f"Expected 2008 positive samples, found {len(positives)}."
        )

    log(f"Positive samples: {len(positives)}")

    # --------------------------------------------------------
    # Verify positive samples are not modified
    # --------------------------------------------------------

    if positives["slide_no"].duplicated().any():
        raise ValueError("Duplicate positive SlideNo values detected.")

    if positives[["latitude", "longitude"]].isnull().any().any():
        raise ValueError("Positive samples contain null coordinates.")

    # --------------------------------------------------------
    # Load GADM
    # --------------------------------------------------------

    log()
    log("Loading GADM ADM1 boundaries...")

    boundaries = gpd.read_file(BOUNDARY_FILE)

    if boundaries.crs is None:
        boundaries = boundaries.set_crs("EPSG:4326")

    boundaries = boundaries.to_crs("EPSG:4326")

    log(f"GADM features: {len(boundaries)}")
    log(f"CRS: {boundaries.crs}")

    if "NAME_1" not in boundaries.columns:
        raise ValueError("GADM file does not contain NAME_1.")

    ner_polygons = {}

    for state_code, state_name in STATE_NAMES.items():

        matches = boundaries[
            boundaries["NAME_1"].astype(str).str.strip() == state_name
        ]

        if matches.empty:
            raise ValueError(
                f"Could not find GADM polygon for {state_code}: {state_name}"
            )

        # Dissolve if the state has multiple ADM1 geometry parts.
        polygon = matches.geometry.union_all()

        if polygon.is_empty:
            raise ValueError(
                f"Empty geometry for {state_code}: {state_name}"
            )

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        ner_polygons[state_code] = polygon

        log(
            f"{state_code}: {state_name} "
            f"(area={polygon.area:.6f} deg²)"
        )

    # --------------------------------------------------------
    # Generate corrected negatives
    # --------------------------------------------------------

    rng = random.Random(SEED)

    negative_rows = []
    generation_report = {}

    log()
    log("Generating corrected negatives...")
    log()

    for state_code in STATE_NAMES:

        state_positive = positives[
            positives["state_code"].astype(str).str.upper() == state_code
        ].copy()

        required_count = len(state_positive)

        if required_count == 0:
            raise ValueError(
                f"No positive samples found for state {state_code}."
            )

        polygon = ner_polygons[state_code]

        positive_points = list(
            zip(
                state_positive["longitude"].astype(float),
                state_positive["latitude"].astype(float),
            )
        )

        generated, attempts = generate_negative_points(
            state_code=state_code,
            state_polygon_wgs84=polygon,
            positive_points=positive_points,
            required_count=required_count,
            rng=rng,
        )

        log(
            f"{state_code}: "
            f"positives={required_count}, "
            f"negatives={len(generated)}, "
            f"attempts={attempts}"
        )

        generation_report[state_code] = {
            "positive_count": required_count,
            "negative_count": len(generated),
            "attempts": attempts,
        }

        for index, (lat, lon) in enumerate(generated, start=1):

            negative_rows.append(
                {
                    "sample_id": f"NEG_{state_code}_{index:04d}",
                    "label": 0,
                    "sample_type": "negative",
                    "source": "GADM_spatial_negative_candidate",
                    "slide_no": None,
                    "feature_id": None,
                    "state_code": state_code,
                    "state": STATE_NAMES[state_code],
                    "district": None,
                    "latitude": lat,
                    "longitude": lon,
                    "year": None,
                    "triggering": None,
                    "activity": None,
                    "geomorph": None,
                    "lithology": None,
                    "lulc": None,
                    "area_sqm": None,
                    "geometry_type": "Point",
                }
            )

    negatives = pd.DataFrame(negative_rows)

    # --------------------------------------------------------
    # Combine positives + corrected negatives
    # --------------------------------------------------------

    corrected = pd.concat(
        [
            positives,
            negatives,
        ],
        ignore_index=True,
    )

    corrected = corrected[list(df.columns)]

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    log()
    log("=" * 70)
    log("FINAL VALIDATION")
    log("=" * 70)

    errors = []

    if len(corrected) != 4016:
        errors.append(
            f"Expected 4016 total rows, found {len(corrected)}"
        )

    if (corrected["label"] == 1).sum() != 2008:
        errors.append("Positive count is not 2008.")

    if (corrected["label"] == 0).sum() != 2008:
        errors.append("Negative count is not 2008.")

    if positives["slide_no"].tolist() != (
        corrected[corrected["label"] == 1]["slide_no"].tolist()
    ):
        errors.append(
            "Positive SlideNo sequence changed."
        )

    # Strict polygon validation for every negative.
    corrected_negatives = corrected[
        corrected["label"] == 0
    ].copy()

    invalid_boundary_rows = []

    for row_index, row in corrected_negatives.iterrows():

        state_code = str(row["state_code"]).upper()

        point = Point(
            float(row["longitude"]),
            float(row["latitude"]),
        )

        polygon = ner_polygons[state_code]

        if not polygon.contains(point):
            invalid_boundary_rows.append(
                {
                    "row_index": int(row_index),
                    "sample_id": row["sample_id"],
                    "state_code": state_code,
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )

    if invalid_boundary_rows:
        errors.append(
            f"{len(invalid_boundary_rows)} negatives are outside "
            f"their intended GADM state polygon."
        )

    duplicate_coords = corrected_negatives.duplicated(
        subset=["latitude", "longitude"]
    ).sum()

    if duplicate_coords:
        errors.append(
            f"{duplicate_coords} duplicate negative coordinates detected."
        )

    state_counts = corrected.groupby(
        ["state_code", "label"]
    ).size().unstack(fill_value=0)

    for state_code in STATE_NAMES:

        positive_count = int(
            state_counts.loc[state_code, 1]
            if state_code in state_counts.index and 1 in state_counts.columns
            else 0
        )

        negative_count = int(
            state_counts.loc[state_code, 0]
            if state_code in state_counts.index and 0 in state_counts.columns
            else 0
        )

        if positive_count != negative_count:
            errors.append(
                f"{state_code}: positive={positive_count}, "
                f"negative={negative_count}"
            )

    log()
    log(f"Total samples:        {len(corrected)}")
    log(f"Positive samples:     {(corrected['label'] == 1).sum()}")
    log(f"Negative samples:     {(corrected['label'] == 0).sum()}")
    log(f"Invalid negatives:    {len(invalid_boundary_rows)}")
    log(f"Duplicate negatives:  {duplicate_coords}")

    log()
    log("State-wise counts:")
    print(state_counts.to_string())

    if errors:
        log()
        log("VALIDATION FAILED")
        for error in errors:
            log(f"  - {error}")

        report = {
            "status": "FAIL",
            "baseline_file": str(BASELINE_FILE),
            "boundary_file": str(BOUNDARY_FILE),
            "output_file": str(OUTPUT_FILE),
            "seed": SEED,
            "negative_buffer_meters": NEGATIVE_BUFFER_METERS,
            "baseline_rows": int(len(df)),
            "positive_rows": int(len(positives)),
            "negative_rows_generated": int(len(negatives)),
            "total_rows": int(len(corrected)),
            "invalid_boundary_rows": invalid_boundary_rows[:100],
            "invalid_boundary_count": len(invalid_boundary_rows),
            "duplicate_negative_coordinates": int(duplicate_coords),
            "errors": errors,
            "generation_report": generation_report,
        }

        REPORT_FILE.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # Save corrected dataset
    # --------------------------------------------------------

    corrected.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    report = {
        "status": "PASS",
        "method": "GADM ADM1 polygon-constrained spatial negative sampling",
        "baseline_file": str(BASELINE_FILE),
        "boundary_file": str(BOUNDARY_FILE),
        "output_file": str(OUTPUT_FILE),
        "seed": SEED,
        "negative_buffer_meters": NEGATIVE_BUFFER_METERS,
        "baseline_rows": int(len(df)),
        "positive_rows": int(len(positives)),
        "negative_rows": int(len(negatives)),
        "total_rows": int(len(corrected)),
        "invalid_boundary_count": 0,
        "duplicate_negative_coordinates": 0,
        "positive_slide_no_preserved": True,
        "state_counts": {
            state_code: {
                "positive": int(
                    state_counts.loc[state_code, 1]
                ),
                "negative": int(
                    state_counts.loc[state_code, 0]
                ),
            }
            for state_code in STATE_NAMES
        },
        "generation_report": generation_report,
        "scientific_note": (
            "Negative samples are spatial negative candidates generated "
            "inside the intended GADM state polygon and outside a "
            "1 km buffer around known positive landslide coordinates. "
            "They are not confirmed landslide absences."
        ),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    log()
    log("=" * 70)
    log("VALIDATION PASSED")
    log("=" * 70)
    log()
    log(f"Corrected dataset: {OUTPUT_FILE}")
    log(f"Correction report: {REPORT_FILE}")
    log()
    log("The original baseline CSV was NOT modified.")
    log("The 2,008 positive Bhuvan samples were preserved.")
    log("All 2,008 negatives are inside their intended GADM state.")
    log()


if __name__ == "__main__":
    main()
