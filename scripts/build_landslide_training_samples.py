from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.ops import transform
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "raw" / "landslides" / "2014"
OUTPUT_DIR = ROOT / "data" / "processed" / "landslides"

OUTPUT_CSV = OUTPUT_DIR / "landslide_training_samples.csv"
OUTPUT_REPORT = OUTPUT_DIR / "landslide_training_sample_report.json"

RANDOM_SEED = 20260905

# Number of negative samples requested per positive sample.
NEGATIVE_TO_POSITIVE_RATIO = 1.0

# Exclusion radius around known 2014 landslide polygons.
EXCLUSION_RADIUS_M = 1000.0

# Maximum attempts used to find valid negative points.
MAX_ATTEMPTS_MULTIPLIER = 1000

# Approximate state study areas used only for candidate generation.
# These are NOT administrative boundaries.
STATE_BBOXES = {
    "AR": (91.5, 26.5, 97.5, 29.5),
    "AS": (89.5, 24.0, 96.5, 28.5),
    "ML": (89.5, 25.0, 92.9, 26.2),
    "MN": (93.0, 23.5, 94.9, 25.8),
    "MZ": (92.1, 21.9, 93.5, 24.5),
    "NL": (93.3, 25.2, 95.3, 27.1),
    "SK": (88.0, 27.0, 88.9, 28.2),
    "TR": (91.0, 22.9, 92.3, 24.5),
}


def state_code_from_filename(path: Path) -> str:
    return path.name[:2].upper()


def utm_epsg_for_lon_lat(lon: float, lat: float) -> int:
    """
    Determine the northern-hemisphere UTM EPSG code.
    """
    zone = int(math.floor((lon + 180.0) / 6.0) + 1)
    return 32600 + zone


def make_projectors(lon: float, lat: float):
    """
    Create WGS84 <-> local UTM transformers.
    """
    epsg = utm_epsg_for_lon_lat(lon, lat)

    to_utm = Transformer.from_crs(
        "EPSG:4326",
        f"EPSG:{epsg}",
        always_xy=True,
    ).transform

    to_wgs84 = Transformer.from_crs(
        f"EPSG:{epsg}",
        "EPSG:4326",
        always_xy=True,
    ).transform

    return to_utm, to_wgs84


def load_positive_events():
    records = []

    for path in sorted(INPUT_DIR.glob("*_SLIM_2014_GCS.geojson")):
        state_code = state_code_from_filename(path)

        data = json.loads(path.read_text(encoding="utf-8"))

        for feature in data.get("features", []):
            properties = feature.get("properties", {})
            geometry_data = feature.get("geometry")

            if not geometry_data:
                continue

            try:
                geom = shape(geometry_data)
            except Exception:
                continue

            if geom.is_empty:
                continue

            lat = properties.get("Latitude")
            lon = properties.get("Longitude")

            if lat is None or lon is None:
                # Fall back to geometry centroid.
                centroid = geom.centroid
                lon = centroid.x
                lat = centroid.y

            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue

            records.append(
                {
                    "sample_id": f"LS2014_{len(records) + 1:06d}",
                    "label": 1,
                    "sample_type": "positive",
                    "source": "bhuvan_2014",
                    "slide_no": properties.get("SlideNo"),
                    "feature_id": None,
                    "state_code": state_code,
                    "state": properties.get("State"),
                    "district": properties.get("District"),
                    "latitude": lat,
                    "longitude": lon,
                    "year": properties.get("Year"),
                    "triggering": properties.get("Triggering"),
                    "activity": properties.get("Activity"),
                    "geomorph": properties.get("Geomorph"),
                    "lithology": properties.get("Lithology"),
                    "lulc": properties.get("LULC"),
                    "area_sqm": properties.get("Area_sqm"),
                    "geometry_type": geom.geom_type,
                    "_geometry": geom,
                }
            )

    return records


def build_state_exclusion_geometry(features, state_code):
    """
    Build a union of buffered known landslide polygons for a state.

    Buffering is performed in a local UTM projection to keep
    the 1 km exclusion distance approximately metric.
    """
    geometries = [
        r["_geometry"]
        for r in features
        if r["state_code"] == state_code
    ]

    if not geometries:
        return None

    # Use the mean centroid to select a local UTM zone.
    centroid_points = [g.centroid for g in geometries]
    mean_lon = sum(p.x for p in centroid_points) / len(centroid_points)
    mean_lat = sum(p.y for p in centroid_points) / len(centroid_points)

    to_utm, to_wgs84 = make_projectors(mean_lon, mean_lat)

    projected = [
        transform(to_utm, g)
        for g in geometries
    ]

    buffered = [
        g.buffer(EXCLUSION_RADIUS_M)
        for g in projected
    ]

    union_projected = buffered[0]

    for g in buffered[1:]:
        union_projected = union_projected.union(g)

    return transform(to_wgs84, union_projected)


def generate_negative_samples(positive_records):
    rng = np.random.default_rng(RANDOM_SEED)

    positive_count = len(positive_records)
    target_negative_count = int(
        round(positive_count * NEGATIVE_TO_POSITIVE_RATIO)
    )

    # Build exclusion geometries by state.
    exclusion_by_state = {}

    for state_code in STATE_BBOXES:
        exclusion_by_state[state_code] = build_state_exclusion_geometry(
            positive_records,
            state_code,
        )

    positive_by_state = {}
    for record in positive_records:
        positive_by_state.setdefault(record["state_code"], []).append(record)

    # Allocate negatives approximately according to positive state distribution.
    allocations = {}

    for state_code, records in positive_by_state.items():
        proportion = len(records) / positive_count
        allocations[state_code] = int(round(target_negative_count * proportion))

    # Correct rounding difference.
    allocation_total = sum(allocations.values())
    difference = target_negative_count - allocation_total

    if difference != 0:
        largest_state = max(
            allocations,
            key=lambda code: len(positive_by_state.get(code, [])),
        )
        allocations[largest_state] += difference

    negatives = []
    global_index = 1

    for state_code, target_count in allocations.items():
        if target_count <= 0:
            continue

        if state_code not in STATE_BBOXES:
            continue

        min_lon, min_lat, max_lon, max_lat = STATE_BBOXES[state_code]

        exclusion = exclusion_by_state.get(state_code)

        attempts = 0
        accepted = 0
        max_attempts = max(
            target_count * MAX_ATTEMPTS_MULTIPLIER,
            10000,
        )

        while accepted < target_count and attempts < max_attempts:
            attempts += 1

            lon = float(rng.uniform(min_lon, max_lon))
            lat = float(rng.uniform(min_lat, max_lat))

            point = Point(lon, lat)

            # Reject points within the exclusion zone.
            if exclusion is not None and exclusion.contains(point):
                continue

            # Ensure candidate is not extremely close to a known
            # positive coordinate even if polygon buffering has
            # numerical/topological edge cases.
            too_close = False

            for positive in positive_by_state.get(state_code, []):
                dlat = lat - positive["latitude"]
                dlon = lon - positive["longitude"]

                # Conservative geographic distance approximation.
                lat_m = dlat * 111_320.0
                lon_m = (
                    dlon
                    * 111_320.0
                    * math.cos(math.radians(lat))
                )

                distance_m = math.sqrt(
                    lat_m * lat_m + lon_m * lon_m
                )

                if distance_m < EXCLUSION_RADIUS_M:
                    too_close = True
                    break

            if too_close:
                continue

            # Use nearest positive state metadata only as provenance.
            # Do NOT pretend this is an observed "absence".
            negatives.append(
                {
                    "sample_id": f"NEG2014_{global_index:06d}",
                    "label": 0,
                    "sample_type": "negative_candidate",
                    "source": "spatial_negative_sampling",
                    "slide_no": None,
                    "feature_id": None,
                    "state_code": state_code,
                    "state": None,
                    "district": None,
                    "latitude": lat,
                    "longitude": lon,
                    "year": 2014,
                    "triggering": None,
                    "activity": None,
                    "geomorph": None,
                    "lithology": None,
                    "lulc": None,
                    "area_sqm": None,
                    "geometry_type": "Point",
                    "_geometry": point,
                }
            )

            global_index += 1
            accepted += 1

        print(
            f"{state_code}: requested={target_count}, "
            f"accepted={accepted}, attempts={attempts}"
        )

        if accepted < target_count:
            print(
                f"WARNING: Could not generate the requested number "
                f"of negatives for {state_code}."
            )

    return negatives


def clean_for_csv(records):
    rows = []

    for record in records:
        row = {
            key: value
            for key, value in record.items()
            if key != "_geometry"
        }
        rows.append(row)

    return pd.DataFrame(rows)


def validate_dataset(df, positive_records, negative_records):
    report = {
        "status": "PASS",
        "random_seed": RANDOM_SEED,
        "exclusion_radius_m": EXCLUSION_RADIUS_M,
        "negative_to_positive_ratio_requested": NEGATIVE_TO_POSITIVE_RATIO,
        "positive_count": int(len(positive_records)),
        "negative_count": int(len(negative_records)),
        "total_samples": int(len(df)),
        "label_counts": {
            str(k): int(v)
            for k, v in df["label"].value_counts().to_dict().items()
        },
        "positive_unique_slide_no": int(
            df.loc[df["label"] == 1, "slide_no"].nunique()
        ),
        "positive_null_coordinates": int(
            df.loc[
                df["label"] == 1,
                ["latitude", "longitude"],
            ].isna().any(axis=1).sum()
        ),
        "negative_null_coordinates": int(
            df.loc[
                df["label"] == 0,
                ["latitude", "longitude"],
            ].isna().any(axis=1).sum()
        ),
        "positive_state_counts": {
            str(k): int(v)
            for k, v in df[df["label"] == 1]["state_code"]
            .value_counts()
            .sort_index()
            .to_dict()
            .items()
        },
        "negative_state_counts": {
            str(k): int(v)
            for k, v in df[df["label"] == 0]["state_code"]
            .value_counts()
            .sort_index()
            .to_dict()
            .items()
        },
        "notes": [
            "Positive samples originate from the official 2014 Bhuvan inventory.",
            "Negative samples are spatially separated candidates, not confirmed absence observations.",
            "Negative candidates are generated inside state study bounding boxes.",
            "No rainfall, terrain, soil, LULC, or other environmental feature values are attached in Phase 8D.",
            "The 2014 inventory provides year-level temporal information; exact event dates are not assumed.",
        ],
    }

    if len(positive_records) != 2008:
        report["status"] = "FAIL"
        report["failure_reason"] = (
            f"Expected 2008 positive events, found "
            f"{len(positive_records)}."
        )

    if df["slide_no"].dropna().duplicated().any():
        report["status"] = "FAIL"
        report["failure_reason"] = (
            "Duplicate positive SlideNo values detected."
        )

    if report["positive_null_coordinates"] > 0:
        report["status"] = "FAIL"
        report["failure_reason"] = (
            "Positive samples contain null coordinates."
        )

    if report["negative_null_coordinates"] > 0:
        report["status"] = "FAIL"
        report["failure_reason"] = (
            "Negative samples contain null coordinates."
        )

    return report


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 8D - LANDSLIDE TRAINING SAMPLE CONSTRUCTION")
    print("=" * 70)

    print("\nLoading official 2014 Bhuvan inventory...")

    positive_records = load_positive_events()

    print(f"Positive events loaded: {len(positive_records)}")

    if len(positive_records) != 2008:
        raise RuntimeError(
            f"Expected exactly 2008 positive events; "
            f"found {len(positive_records)}. "
            f"Stop before generating training samples."
        )

    print("\nGenerating controlled negative candidates...")

    negative_records = generate_negative_samples(
        positive_records
    )

    print(f"\nNegative candidates generated: {len(negative_records)}")

    all_records = positive_records + negative_records

    df = clean_for_csv(all_records)

    # Stable deterministic ordering.
    df = df.sort_values(
        by=["label", "state_code", "sample_id"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    report = validate_dataset(
        df,
        positive_records,
        negative_records,
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8",
    )

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("PHASE 8D RESULT")
    print("=" * 70)

    print(f"Status: {report['status']}")
    print(f"Positive samples: {report['positive_count']}")
    print(f"Negative samples: {report['negative_count']}")
    print(f"Total samples: {report['total_samples']}")

    print("\nLabel distribution:")
    print(df["label"].value_counts().sort_index())

    print("\nPositive state distribution:")
    print(
        df[df["label"] == 1]["state_code"]
        .value_counts()
        .sort_index()
    )

    print("\nNegative state distribution:")
    print(
        df[df["label"] == 0]["state_code"]
        .value_counts()
        .sort_index()
    )

    print("\nOutput:")
    print(OUTPUT_CSV)
    print(OUTPUT_REPORT)

    if report["status"] != "PASS":
        raise RuntimeError(
            "Phase 8D validation FAILED. "
            "Do not commit this dataset."
        )

    print("\nPhase 8D validation PASSED.")
    print("Do NOT train the ML model yet.")


if __name__ == "__main__":
    main()
