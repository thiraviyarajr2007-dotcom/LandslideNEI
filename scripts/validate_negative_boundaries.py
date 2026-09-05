from pathlib import Path
import json
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

import sys

BASE = Path("data")
INPUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else BASE / "processed" / "landslides" / "landslide_training_samples.csv"
)
OUT_DIR = BASE / "inspection" / "landslide_validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BOUNDARY_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_IND_1.json"
BOUNDARY_FILE = OUT_DIR / "gadm41_IND_1.json"

STATE_MAP = {
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "SK": "Sikkim",
    "TR": "Tripura",
}

print("=" * 70)
print("LANDSLIDE NEGATIVE-SAMPLE STATE-BOUNDARY VALIDATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load training samples
# ------------------------------------------------------------
df = pd.read_csv(INPUT)

neg = df[df["label"] == 0].copy()

print(f"\nTotal samples:       {len(df)}")
print(f"Positive samples:    {(df['label'] == 1).sum()}")
print(f"Negative samples:    {len(neg)}")

# ------------------------------------------------------------
# 2. Download India ADM1 boundary data if needed
# ------------------------------------------------------------
if not BOUNDARY_FILE.exists():
    print("\nDownloading India ADM1 boundaries...")
    r = requests.get(BOUNDARY_URL, timeout=60)
    r.raise_for_status()
    BOUNDARY_FILE.write_bytes(r.content)
    print(f"Saved: {BOUNDARY_FILE}")
else:
    print(f"\nUsing existing boundary file: {BOUNDARY_FILE}")

# ------------------------------------------------------------
# 3. Read boundaries
# ------------------------------------------------------------
gdf = gpd.read_file(BOUNDARY_FILE)

print("\nBoundary columns:")
print(list(gdf.columns))

print(f"\nIndia ADM1 features: {len(gdf)}")

# Find the state-name column used by GADM
name_candidates = ["NAME_1", "name_1", "NAME", "name"]

name_col = None
for c in name_candidates:
    if c in gdf.columns:
        name_col = c
        break

if name_col is None:
    raise RuntimeError(
        "Could not identify the ADM1 state-name column. "
        f"Available columns: {list(gdf.columns)}"
    )

print(f"State-name column: {name_col}")

# ------------------------------------------------------------
# 4. Keep only the 8 NER states
# (GADM 4.1 stores names without spaces and splits border zones like Arunachal)
# ------------------------------------------------------------
norm_to_state = {name.replace(" ", "").lower(): name for name in STATE_MAP.values()}

gdf["_norm_name"] = gdf[name_col].astype(str).str.replace(" ", "").str.lower()
ner_boundary = gdf[gdf["_norm_name"].isin(norm_to_state.keys())].copy()

# Dissolve multi-part state polygons (e.g. Arunachal Pradesh IND.3_1 and Z07.3_1)
ner_boundary = ner_boundary.dissolve(by="_norm_name", as_index=False)
ner_boundary[name_col] = ner_boundary["_norm_name"].map(norm_to_state)

print(f"NER state polygons found: {len(ner_boundary)}")

missing_states = sorted(set(STATE_MAP.values()) - set(ner_boundary[name_col]))
if missing_states:
    raise RuntimeError(
        f"Missing NER states in boundary dataset: {missing_states}"
    )

# Reproject to WGS84 for point creation
ner_boundary = ner_boundary.to_crs("EPSG:4326")

# ------------------------------------------------------------
# 5. Validate each negative point
# ------------------------------------------------------------
geometry = [
    Point(float(lon), float(lat))
    for lon, lat in zip(neg["longitude"], neg["latitude"])
]

points = gpd.GeoDataFrame(
    neg,
    geometry=geometry,
    crs="EPSG:4326",
)

# Spatial join: point must fall within intended state
joined = gpd.sjoin(
    points,
    ner_boundary[[name_col, "geometry"]],
    how="left",
    predicate="within",
)

joined["expected_state"] = joined["state_code"].map(STATE_MAP)
joined["actual_state"] = joined[name_col]

joined["state_boundary_valid"] = (
    joined["actual_state"] == joined["expected_state"]
)

# ------------------------------------------------------------
# 6. Summary
# ------------------------------------------------------------
valid = int(joined["state_boundary_valid"].sum())
invalid = int((~joined["state_boundary_valid"]).sum())

print("\n" + "=" * 70)
print("VALIDATION RESULT")
print("=" * 70)

print(f"\nNegative candidates:       {len(joined)}")
print(f"Inside intended state:     {valid}")
print(f"Outside intended state:    {invalid}")

if len(joined):
    pct = valid / len(joined) * 100
    print(f"Boundary validity:         {pct:.2f}%")

# ------------------------------------------------------------
# 7. State-wise result
# ------------------------------------------------------------
print("\nState-wise validation:")
summary = (
    joined.groupby("state_code")
    .agg(
        negatives=("sample_id", "size"),
        valid=("state_boundary_valid", "sum"),
    )
)

summary["invalid"] = summary["negatives"] - summary["valid"]
summary["valid_pct"] = (
    summary["valid"] / summary["negatives"] * 100
).round(2)

print(summary.to_string())

# ------------------------------------------------------------
# 8. Save invalid candidates for inspection
# ------------------------------------------------------------
invalid_df = joined[~joined["state_boundary_valid"]].copy()

invalid_csv = OUT_DIR / "invalid_negative_candidates.csv"

# Don't write shapely geometry into CSV
save_cols = [
    "sample_id",
    "state_code",
    "expected_state",
    "actual_state",
    "latitude",
    "longitude",
    "sample_type",
    "source",
]

invalid_df[save_cols].to_csv(invalid_csv, index=False)

print(f"\nInvalid candidate report: {invalid_csv}")

# ------------------------------------------------------------
# 9. Save machine-readable report
# ------------------------------------------------------------
report = {
    "input": str(INPUT),
    "total_samples": int(len(df)),
    "positive_samples": int((df["label"] == 1).sum()),
    "negative_samples": int(len(neg)),
    "valid_negative_candidates": valid,
    "invalid_negative_candidates": invalid,
    "validity_percent": round(valid / len(neg) * 100, 4)
    if len(neg) else 0,
    "boundary_source": BOUNDARY_URL,
    "boundary_dataset": "GADM 4.1 India ADM1",
    "states_checked": sorted(STATE_MAP.keys()),
    "state_summary": {
        str(idx): {
            "negatives": int(row["negatives"]),
            "valid": int(row["valid"]),
            "invalid": int(row["invalid"]),
            "valid_pct": float(row["valid_pct"]),
        }
        for idx, row in summary.iterrows()
    },
}

report_file = OUT_DIR / "negative_boundary_validation_report.json"
report_file.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print(f"Validation report:        {report_file}")

print("\n" + "=" * 70)

if invalid == 0:
    print("PASS: Every negative candidate is inside its intended state.")
else:
    print(
        "REVIEW REQUIRED: Some negative candidates are outside "
        "their intended state."
    )

print("=" * 70)
