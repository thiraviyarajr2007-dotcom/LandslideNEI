import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
import json
import time
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import ssl

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "landslides"
)

PROCESSED_ROOT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslides"
)

INSPECTION_ROOT = (
    PROJECT_ROOT
    / "data"
    / "inspection"
    / "landslide_service"
)

SERVICE_URL = (
    "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/142 Safari/537.36"
)

# Start with 2014 because all 8 NER states have layers.
LAYERS = {
    "AR": {
        "state": "Arunachal Pradesh",
        "layer": "disaster:AR_SLIM_2014_GCS",
        "bbox": (91.5, 26.5, 97.5, 29.5),
    },
    "AS": {
        "state": "Assam",
        "layer": "disaster:AS_SLIM_2014_GCS",
        "bbox": (89.5, 24.0, 96.5, 28.5),
    },
    "MN": {
        "state": "Manipur",
        "layer": "disaster:MN_SLIM_2014_GCS",
        "bbox": (93.0, 23.5, 94.9, 25.8),
    },
    "ML": {
        "state": "Meghalaya",
        "layer": "disaster:ML_SLIM_2014_GCS",
        "bbox": (89.5, 25.0, 92.9, 26.2),
    },
    "MZ": {
        "state": "Mizoram",
        "layer": "disaster:MZ_SLIM_2014_GCS",
        "bbox": (92.1, 21.9, 93.5, 24.5),
    },
    "NL": {
        "state": "Nagaland",
        "layer": "disaster:NL_SLIM_2014_GCS",
        "bbox": (93.3, 25.2, 95.3, 27.1),
    },
    "SK": {
        "state": "Sikkim",
        "layer": "disaster:SK_SLIM_2014_GCS",
        "bbox": (88.0, 27.0, 88.9, 28.2),
    },
    "TR": {
        "state": "Tripura",
        "layer": "disaster:TR_SLIM_2014_GCS",
        "bbox": (91.0, 22.9, 92.3, 24.5),
    },
}

# Number of grid cells per state side.
# This is intentionally conservative for the first extraction.
GRID_X = 12
GRID_Y = 12

# Multiple query points inside every grid cell.
SAMPLES_PER_CELL_X = 2
SAMPLES_PER_CELL_Y = 2

FEATURE_COUNT = 50

REQUEST_DELAY_SECONDS = 0.15

TIMEOUT_SECONDS = 30


# ============================================================
# SSL
# ============================================================

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


# ============================================================
# HELPERS
# ============================================================

def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def build_getfeatureinfo_url(
    layer,
    bbox,
    x,
    y,
    width=101,
    height=101,
):
    params = {
        "REQUEST": "GetFeatureInfo",
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "LAYERS": layer,
        "QUERY_LAYERS": layer,
        "INFO_FORMAT": "application/json",
        "BBOX": ",".join(
            f"{value:.10f}"
            for value in bbox
        ),
        "WIDTH": width,
        "HEIGHT": height,
        "X": x,
        "Y": y,
        "SRS": "EPSG:4326",
        "FEATURE_COUNT": FEATURE_COUNT,
        "BUFFER": 50,
    }

    return (
        SERVICE_URL
        + "?"
        + urlencode(params)
    )


def fetch_json(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urlopen(
        request,
        context=SSL_CONTEXT,
        timeout=TIMEOUT_SECONDS,
    ) as response:

        body = response.read()

        return json.loads(
            body.decode(
                "utf-8",
                errors="replace",
            )
        )


def make_grid(bbox):

    minx, miny, maxx, maxy = bbox

    dx = (maxx - minx) / GRID_X
    dy = (maxy - miny) / GRID_Y

    cells = []

    for ix in range(GRID_X):

        for iy in range(GRID_Y):

            cell_minx = minx + ix * dx
            cell_maxx = minx + (ix + 1) * dx

            cell_miny = miny + iy * dy
            cell_maxy = miny + (iy + 1) * dy

            cells.append(
                (
                    ix,
                    iy,
                    (
                        cell_minx,
                        cell_miny,
                        cell_maxx,
                        cell_maxy,
                    ),
                )
            )

    return cells


def extract_layer(layer_name, state, bbox):

    print()
    print("=" * 80)
    print(f"EXTRACTING: {state}")
    print(f"LAYER: {layer_name}")
    print("=" * 80)

    features = {}

    request_count = 0
    successful_requests = 0
    failed_requests = 0

    cells = make_grid(bbox)

    total_cells = len(cells)

    for cell_number, (
        ix,
        iy,
        cell_bbox,
    ) in enumerate(cells, start=1):

        cminx, cminy, cmaxx, cmaxy = cell_bbox

        if cell_number % 12 == 1 or cell_number == total_cells:
            print(
                f"  Progress: cell {cell_number}/{total_cells} "
                f"({ix},{iy}) - {len(features):,} unique features found so far..."
            )

        for sx in range(
            SAMPLES_PER_CELL_X
        ):

            for sy in range(
                SAMPLES_PER_CELL_Y
            ):

                # Query points are distributed inside the cell.
                px_fraction = (
                    sx + 0.5
                ) / SAMPLES_PER_CELL_X

                py_fraction = (
                    sy + 0.5
                ) / SAMPLES_PER_CELL_Y

                px = (
                    cminx
                    + px_fraction
                    * (cmaxx - cminx)
                )

                py = (
                    cminy
                    + py_fraction
                    * (cmaxy - cminy)
                )

                # Create a small BBOX around the query point.
                pad_x = (
                    cmaxx - cminx
                ) / 4

                pad_y = (
                    cmaxy - cminy
                ) / 4

                query_bbox = (
                    max(bbox[0], px - pad_x),
                    max(bbox[1], py - pad_y),
                    min(bbox[2], px + pad_x),
                    min(bbox[3], py + pad_y),
                )

                url = build_getfeatureinfo_url(
                    layer_name,
                    query_bbox,
                    50,
                    50,
                )

                request_count += 1

                try:

                    data = fetch_json(url)

                    successful_requests += 1

                    returned = data.get(
                        "features",
                        [],
                    )

                    for feature in returned:

                        feature_id = (
                            feature.get("id")
                        )

                        properties = feature.get(
                            "properties",
                            {},
                        )

                        slide_no = properties.get(
                            "SlideNo"
                        )

                        # Prefer official feature ID,
                        # then SlideNo.
                        dedup_key = (
                            feature_id
                            or slide_no
                        )

                        if dedup_key is None:

                            # Last-resort deterministic key.
                            dedup_key = (
                                json.dumps(
                                    feature,
                                    sort_keys=True,
                                    default=str,
                                )
                            )

                        features[str(
                            dedup_key
                        )] = feature

                except Exception as exc:

                    failed_requests += 1

                    print(
                        f"  WARNING request failed: "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                time.sleep(
                    REQUEST_DELAY_SECONDS
                )

    print()
    print(
        f"Requests attempted : "
        f"{request_count:,}"
    )

    print(
        f"Requests successful : "
        f"{successful_requests:,}"
    )

    print(
        f"Requests failed     : "
        f"{failed_requests:,}"
    )

    print(
        f"Unique features     : "
        f"{len(features):,}"
    )

    return (
        list(features.values()),
        {
            "requests_attempted": request_count,
            "requests_successful": successful_requests,
            "requests_failed": failed_requests,
            "unique_features": len(features),
        },
    )


# ============================================================
# VALIDATE FEATURES
# ============================================================

def validate_features(
    features,
    expected_state,
):

    if not features:
        raise RuntimeError(
            f"No features extracted for "
            f"{expected_state}."
        )

    required_properties = {
        "SlideNo",
        "State",
        "District",
        "Latitude",
        "Longitude",
        "Year",
    }

    property_sets = [
        set(
            feature.get(
                "properties",
                {},
            ).keys()
        )
        for feature in features
    ]

    combined_properties = set().union(
        *property_sets
    )

    missing = (
        required_properties
        - combined_properties
    )

    if missing:
        raise RuntimeError(
            f"{expected_state}: expected "
            f"properties missing: "
            + ", ".join(sorted(missing))
        )

    bad_states = []

    for feature in features:

        state = (
            feature
            .get("properties", {})
            .get("State")
        )

        if state and (
            state.strip().upper()
            != expected_state.upper()
        ):
            bad_states.append(state)

    if bad_states:

        print(
            "WARNING: features returned with "
            "different state values:"
        )

        for state in sorted(
            set(bad_states)
        ):
            print(
                f"  - {state}"
            )


# ============================================================
# SAVE LAYER
# ============================================================

def save_layer(
    code,
    state,
    layer_name,
    bbox,
    features,
    metrics,
):

    RAW_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_dir = (
        RAW_ROOT / "2014"
    )

    state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        state_dir
        / f"{code}_SLIM_2014_GCS.geojson"
    )

    collection = {
        "type": "FeatureCollection",
        "name": layer_name,
        "source": SERVICE_URL,
        "extraction": {
            "method": (
                "WMS GetFeatureInfo "
                "tiled sampling"
            ),
            "version": "1.1.1",
            "srs": "EPSG:4326",
            "state": state,
            "bbox": list(bbox),
            "extracted_at_utc": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            **metrics,
        },
        "features": features,
    }

    output.write_text(
        json.dumps(
            collection,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output


# ============================================================
# BUILD REPORT
# ============================================================

def build_report(results):

    return {
        "generated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "service": SERVICE_URL,
        "method": (
            "WMS GetFeatureInfo "
            "tiled sampling"
        ),
        "year": 2014,
        "raw_sources_modified": False,
        "states": results,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("PHASE 8C.5 — REAL LANDSLIDE INVENTORY EXTRACTION")
    print("=" * 80)

    results = {}

    for code, config in LAYERS.items():

        state = config["state"]
        layer = config["layer"]
        bbox = config["bbox"]

        features, metrics = extract_layer(
            layer,
            state,
            bbox,
        )

        validate_features(
            features,
            state,
        )

        output = save_layer(
            code,
            state,
            layer,
            bbox,
            features,
            metrics,
        )

        results[code] = {
            "state": state,
            "layer": layer,
            "bbox": list(bbox),
            "output": str(
                output.relative_to(
                    PROJECT_ROOT
                )
            ),
            "sha256": sha256(output),
            **metrics,
        }

    PROCESSED_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = build_report(
        results
    )

    report_file = (
        PROCESSED_ROOT
        / "landslide_2014_extraction_report.json"
    )

    report_file.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("PHASE 8C.5 EXTRACTION FINISHED")
    print("=" * 80)

    for code, result in results.items():

        print(
            f"{result['state']}: "
            f"{result['unique_features']:,} "
            f"features"
        )

    print()
    print(
        f"Report: {report_file}"
    )

    print(
        "\nIMPORTANT:"
        "\nThese are extracted source inventory "
        "features, not ML labels."
    )


if __name__ == "__main__":
    main()
