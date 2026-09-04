from pathlib import Path
import hashlib
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"

REPORT_FILE = PROJECT_ROOT / "data" / "landslide_atlas_inspection.json"

# Approximate Northeast India bounding box.
NER_LAT_MIN = 21.5
NER_LAT_MAX = 30.0
NER_LON_MIN = 88.0
NER_LON_MAX = 98.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def inspect_csv(path: Path):
    print("\n" + "=" * 80)
    print(f"FILE: {path.relative_to(PROJECT_ROOT)}")
    print("=" * 80)

    result = {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "rows": None,
        "columns": [],
        "dtypes": {},
        "missing_values": {},
        "errors": [],
    }

    try:
        df = pd.read_csv(path, low_memory=False)

        result["rows"] = len(df)
        result["columns"] = df.columns.tolist()
        result["dtypes"] = {
            col: str(dtype)
            for col, dtype in df.dtypes.items()
        }

        result["missing_values"] = {
            col: int(value)
            for col, value in df.isna().sum().items()
        }

        print(f"Rows: {len(df):,}")
        print(f"Columns: {len(df.columns)}")

        print("\nColumns:")
        for col in df.columns:
            print(f"  - {col}")

        print("\nData types:")
        for col, dtype in df.dtypes.items():
            print(f"  {col}: {dtype}")

        print("\nMissing values:")
        for col, count in df.isna().sum().items():
            if count:
                print(f"  {col}: {count:,}")

        print("\nFirst 5 rows:")
        print(df.head().to_string(index=False))

        print("\nDuplicate rows:")
        print(f"  {df.duplicated().sum():,}")

        # ----------------------------------------------------
        # Coordinate candidate detection
        # ----------------------------------------------------

        lower_map = {
            str(col).strip().lower(): col
            for col in df.columns
        }

        latitude_candidates = [
            original
            for normalized, original in lower_map.items()
            if (
                "latitude" in normalized
                or normalized in {"lat", "y"}
            )
        ]

        longitude_candidates = [
            original
            for normalized, original in lower_map.items()
            if (
                "longitude" in normalized
                or normalized in {"lon", "lng", "long", "x"}
            )
        ]

        result["latitude_candidates"] = latitude_candidates
        result["longitude_candidates"] = longitude_candidates

        print("\nCoordinate candidates:")
        print(f"  Latitude : {latitude_candidates}")
        print(f"  Longitude: {longitude_candidates}")

        if latitude_candidates and longitude_candidates:
            lat_col = latitude_candidates[0]
            lon_col = longitude_candidates[0]

            lat = pd.to_numeric(df[lat_col], errors="coerce")
            lon = pd.to_numeric(df[lon_col], errors="coerce")

            coordinate_report = {
                "latitude_column": lat_col,
                "longitude_column": lon_col,
                "valid_latitude": int(lat.notna().sum()),
                "valid_longitude": int(lon.notna().sum()),
                "invalid_latitude": int(lat.isna().sum()),
                "invalid_longitude": int(lon.isna().sum()),
                "latitude_min": (
                    float(lat.min()) if lat.notna().any() else None
                ),
                "latitude_max": (
                    float(lat.max()) if lat.notna().any() else None
                ),
                "longitude_min": (
                    float(lon.min()) if lon.notna().any() else None
                ),
                "longitude_max": (
                    float(lon.max()) if lon.notna().any() else None
                ),
            }

            inside_ner = (
                lat.between(NER_LAT_MIN, NER_LAT_MAX)
                & lon.between(NER_LON_MIN, NER_LON_MAX)
            )

            coordinate_report["inside_ner_bbox"] = int(
                inside_ner.sum()
            )

            coordinate_report["outside_ner_bbox"] = int(
                (~inside_ner & lat.notna() & lon.notna()).sum()
            )

            result["coordinates"] = coordinate_report

            print("\nCoordinate range:")
            print(
                f"  Latitude : "
                f"{coordinate_report['latitude_min']} -> "
                f"{coordinate_report['latitude_max']}"
            )
            print(
                f"  Longitude: "
                f"{coordinate_report['longitude_min']} -> "
                f"{coordinate_report['longitude_max']}"
            )
            print(
                f"  Inside NER bbox : "
                f"{coordinate_report['inside_ner_bbox']:,}"
            )
            print(
                f"  Outside NER bbox: "
                f"{coordinate_report['outside_ner_bbox']:,}"
            )

        # ----------------------------------------------------
        # Date/time candidate detection
        # ----------------------------------------------------

        date_keywords = [
            "date",
            "time",
            "year",
            "month",
            "day",
        ]

        date_candidates = [
            original
            for normalized, original in lower_map.items()
            if any(
                keyword in normalized
                for keyword in date_keywords
            )
        ]

        result["date_candidates"] = date_candidates

        print("\nDate/time candidates:")
        for col in date_candidates:
            print(f"  - {col}")

            parsed = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=True,
            )

            valid = parsed.notna()

            print(
                f"      parseable: "
                f"{valid.sum():,}/{len(df):,}"
            )

            if valid.any():
                print(
                    f"      range: "
                    f"{parsed.min()} -> {parsed.max()}"
                )

        # ----------------------------------------------------
        # Confidence / accuracy candidate detection
        # ----------------------------------------------------

        confidence_keywords = [
            "confidence",
            "accuracy",
            "quality",
            "certainty",
            "reliability",
            "score",
        ]

        confidence_candidates = [
            original
            for normalized, original in lower_map.items()
            if any(
                keyword in normalized
                for keyword in confidence_keywords
            )
        ]

        result["confidence_candidates"] = confidence_candidates

        print("\nConfidence / quality candidates:")
        for col in confidence_candidates:
            print(f"  - {col}")

        # ----------------------------------------------------
        # Location/category candidates
        # ----------------------------------------------------

        location_keywords = [
            "state",
            "district",
            "region",
            "location",
            "place",
            "village",
            "town",
            "site",
            "landslide",
            "type",
            "class",
            "category",
        ]

        location_candidates = [
            original
            for normalized, original in lower_map.items()
            if any(
                keyword in normalized
                for keyword in location_keywords
            )
        ]

        result["location_category_candidates"] = (
            location_candidates
        )

        print("\nLocation/category candidates:")
        for col in location_candidates:
            print(f"  - {col}")

        return result

    except Exception as exc:
        result["errors"].append(str(exc))
        print(f"\nERROR: {exc}")
        return result


def main():
    print("=" * 80)
    print("LANDSLIDE ATLAS -- NON-DESTRUCTIVE INSPECTION")
    print("=" * 80)

    csv_files = sorted(RAW_ROOT.rglob("*.csv"))

    if not csv_files:
        print("\nNo CSV files found under:")
        print(RAW_ROOT)
        return

    print(f"\nCSV files discovered: {len(csv_files)}")

    reports = []

    for path in csv_files:
        reports.append(inspect_csv(path))

    report = {
        "project_root": str(PROJECT_ROOT),
        "raw_root": str(RAW_ROOT),
        "ner_bbox": {
            "lat_min": NER_LAT_MIN,
            "lat_max": NER_LAT_MAX,
            "lon_min": NER_LON_MIN,
            "lon_max": NER_LON_MAX,
        },
        "files_discovered": len(csv_files),
        "files": reports,
    }

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
