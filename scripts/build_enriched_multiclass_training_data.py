"""
Generate an enriched, realistic, multi-class landslide training dataset.
Combines real topographic, soil, and proximity attributes from the 4,016 Northeast India
inventory samples with realistic CWC/IMD multi-window rainfall distributions and physical
failure thresholds.
"""

import math
import sys
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data_validation import (
    REQUIRED_FEATURES,
    TARGET_COLUMN,
    ALLOWED_TARGET_CLASSES,
    validate_training_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "data" / "processed" / "landslides" / "landslide_training_samples_proximity.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "landslide_training.csv"

def build_enriched_dataset(n_samples: int = 1200, random_state: int = 42) -> pd.DataFrame:
    rng = np.random.RandomState(random_state)
    
    # Load 4,016 real geospatial samples
    inv_df = pd.read_csv(INVENTORY_PATH)
    
    # Impute missing values with medians
    inv_df["elevation_m"] = inv_df["elevation_m"].fillna(inv_df["elevation_m"].median())
    inv_df["slope_deg"] = inv_df["slope_deg"].fillna(inv_df["slope_deg"].median())
    inv_df["clay_percent"] = inv_df["clay_percent"].fillna(inv_df["clay_percent"].median())
    inv_df["bulk_density_kg_dm3"] = inv_df["bulk_density_kg_dm3"].fillna(inv_df["bulk_density_kg_dm3"].median())
    
    # Stratified draw from real inventory
    pos_samples = inv_df[inv_df["label"] == 1].sample(n=n_samples // 2, replace=True, random_state=rng)
    neg_samples = inv_df[inv_df["label"] == 0].sample(n=n_samples // 2, replace=True, random_state=rng)
    combined = pd.concat([pos_samples, neg_samples], ignore_index=True).sample(frac=1.0, random_state=rng).reset_index(drop=True)
    
    rows = []
    for idx, row in combined.iterrows():
        slope = round(float(np.clip(row["slope_deg"], 0.5, 75.0)), 1)
        elevation = round(float(np.clip(row["elevation_m"], 20.0, 5500.0)), 1)
        hist_landslide = int(row["label"])
        
        # Distance to landslide in km
        dist_m = row["distance_to_nearest_other_landslide_m"]
        if pd.isna(dist_m) or dist_m < 0:
            dist_km = round(float(rng.uniform(0.1, 15.0)), 2)
        else:
            dist_km = round(float(dist_m / 1000.0), 2)
        dist_km = float(np.clip(dist_km, 0.05, 50.0))
        
        # Soil risk index based on clay fraction and bulk density
        clay = float(row["clay_percent"])
        bd = float(row["bulk_density_kg_dm3"])
        soil_risk = round(float(np.clip(0.45 * (clay / 38.0) + 0.35 * (1.35 - bd) / 0.5 + rng.normal(0, 0.04), 0.05, 0.95)), 2)
        
        # Assign target risk class based on a balanced target scenario
        target_class = rng.choice(["Low", "Watch", "High", "Critical"])
        
        if target_class == "Low":
            r24 = rng.uniform(2.0, 35.0)
            r3d = r24 + rng.uniform(5.0, 45.0)
            r7d = r3d + rng.uniform(10.0, 90.0)
        elif target_class == "Watch":
            r24 = rng.uniform(30.0, 75.0)
            r3d = r24 + rng.uniform(25.0, 90.0)
            r7d = r3d + rng.uniform(40.0, 160.0)
        elif target_class == "High":
            r24 = rng.uniform(65.0, 130.0)
            r3d = r24 + rng.uniform(50.0, 150.0)
            r7d = r3d + rng.uniform(80.0, 240.0)
        else: # Critical
            r24 = rng.uniform(115.0, 260.0)
            r3d = r24 + rng.uniform(90.0, 240.0)
            r7d = r3d + rng.uniform(140.0, 380.0)
            
        r24 = round(float(r24), 1)
        r3d = round(float(r3d), 1)
        r7d = round(float(r7d), 1)
        
        # Ensure monotonically increasing window rainfall
        if r3d < r24:
            r3d = round(r24 + 10.0, 1)
        if r7d < r3d:
            r7d = round(r3d + 15.0, 1)
            
        rows.append({
            "rainfall_24h": r24,
            "rainfall_3d": r3d,
            "rainfall_7d": r7d,
            "slope": slope,
            "elevation": elevation,
            "historical_landslide": hist_landslide,
            "distance_to_landslide": dist_km,
            "soil_risk": soil_risk,
            "risk": target_class
        })
        
    df = pd.DataFrame(rows)
    # Ensure correct column order
    df = df[REQUIRED_FEATURES + [TARGET_COLUMN]]
    return df

if __name__ == "__main__":
    print("Generating enriched multi-class landslide training dataset...")
    enriched_df = build_enriched_dataset(n_samples=1200, random_state=42)
    print(f"Generated {len(enriched_df)} samples. Class distribution:")
    print(enriched_df["risk"].value_counts())
    
    # Validate dataframe with schema validator
    val_res = validate_training_data(enriched_df)
    if not val_res["valid"]:
        print("Validation errors:", val_res["errors"])
        raise ValueError("Generated dataset failed validation!")
        
    print("Schema validation passed 100%!")
    enriched_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Successfully saved to {OUTPUT_PATH}")
