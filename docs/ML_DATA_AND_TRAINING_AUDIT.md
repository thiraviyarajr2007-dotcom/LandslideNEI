# ML DATA & MODEL TRAINING AUDIT REPORT

**Project:** SIH Landslide — Landslide Risk Prediction & Early Warning System for North-East India (LandslideNEI)  
**Location:** `C:\SIH Landslide`  
**Audit Date:** 2026-09-09  
**Audit Mode:** Scientific Code & Artifact Traceability Audit  
**Active Production Model:** `model/static_lsm_pipeline.joblib`  
**Model Classification:** **A. TRAINING COMPLETE AND VALID (DO NOT RETRAIN)**

---

## 1. Executive Summary

A comprehensive, scientific machine learning data and model training audit was executed across the entire repository. Every dataset, feature engineering pipeline, training script, and fitted model artifact was traced from raw source to deployed inference.

### Key Audit Findings:
1. **Model A (`model/static_lsm_pipeline.joblib`) is Fitted, Verified, and Operationally Active:**  
   The deployed joblib file is a complete `sklearn.pipeline.Pipeline` consisting of a median/mode `ColumnTransformer` and a 150-tree `RandomForestClassifier` with balanced subsample weighting. It is fully fitted, non-empty, and verified active across the FastAPI backend, desktop workstation, and standalone Windows executable.
2. **Authoritative Training Dataset (`landslide_training_samples_proximity.csv`):**  
   Contains **4,016 samples** (2,008 positive landslide events from the official ISRO Bhuvan 2014 Seasonal Landslide Inventory Map across all 8 NER states, and 2,008 negative background points strictly buffered $\ge 1,000\text{ m}$ away from any known landslide and clipped to official GADM41 state boundaries).
3. **Rigorous Two-Tier Architecture (Zero Temporal Leakage):**  
   An audit of historical precipitation datasets proved that forcing rainfall into static susceptibility training would create 100% temporal disconnect and catastrophic leakage (the Bhuvan inventory provides only the year 2014 without exact day/hour timestamps, while repository CWC telemetry begins in 2019 and IMD begins in 2026). The system correctly isolates **Tier 1 (Static Susceptibility ML)** from **Tier 2 (Dynamic Rainfall Triggering)**.
4. **Leakage-Free Spatial Block Cross-Validation:**  
   Model A was evaluated using **1.0° regular geographic grid-block clustering** (41 spatial blocks grouped into 5 balanced spatial folds via KMeans). It achieves an honest spatial **ROC-AUC of 0.8057 ± 0.0708** and **PR-AUC of 0.7950 ± 0.0545** on held-out mountain regions.
5. **Ablation of Spatial Clustering Leakage:**  
   Proximity feature ablation demonstrated that while `distance_to_nearest_other_landslide_m` artificially inflates ROC-AUC to 0.9549, this is pure cluster leakage from inventory grouping and the $\ge 1\text{ km}$ negative buffer. Model A (environmental only: terrain, soil, landcover) was deliberately and scientifically chosen as the primary defensible model.
6. **Retraining Status:**  
   **NO RETRAINING IS REQUIRED.** The current model is complete, correctly trained, scientifically sound, leakage-free, and directly consumes the intended authoritative datasets.

---

## 2. Complete Dataset Inventory

| Dataset Name | Exact File Path | Format | Rows | Cols | Geographic Coverage | Temporal Coverage | Classification | Role in Pipeline | Suitable for ML Training? |
|:---|:---|:---:|:---:|:---:|:---|:---|:---:|:---|:---:|
| **Bhuvan 2014 Landslide Inventory** | `data/raw/landslides/2014/*_SLIM_2014_GCS.geojson` (8 files) | GeoJSON | 2,008 polygons | Varied | All 8 NER States (AR, AS, ML, MN, MZ, NL, SK, TR) | 2014 Annual Inventory | Raw Historical Inventory | Primary source for all 2,008 positive training events | **YES (Positives)** |
| **GADM41 NER State Boundaries** | `data/inspection/landslide_validation/gadm41_IND_1.json` | GeoJSON | 8 polygons | 11 | All 8 NER States | 2022 v4.1 | Authoritative Admin Boundary | Used to clip negative sampling strictly within NER states | **YES (Mask)** |
| **Copernicus GLO-30 DEM** | `data/raw/dem/copernicus_glo30/downloads/*.tif` | GeoTIFF | 30m Rasters | 1 band | Regional tiles (22°N–29°N, 88°E–97°E) | 2020 World DEM | Raw Remote Sensing Raster | Extracted terrain features (elev, slope, aspect, relief) | **YES (Conditioning)** |
| **SoilGrids 250m Rasters** | `data/raw/soil/*.tif` (bdod, clay, sand, silt, wrb) | GeoTIFF | 250m Rasters | 1 band | Full Northeast India Domain | ISRIC 2020 | Raw Geotechnical Raster | Extracted soil features (clay, sand, silt, bulk density, WRB class) | **YES (Conditioning)** |
| **ESA WorldCover 10m Rasters** | `data/raw/worldcover/esa_worldcover_v200/*.tif` | GeoTIFF | 10m Rasters | 1 band | Full Northeast India Domain | ESA 2021 v200 | Raw Land Cover Raster | Extracted landcover class for static training | **YES (Conditioning)** |
| **OpenStreetMap Road Network** | `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.shp` | Shapefile | Vector lines | 5 | Full Northeast India Domain | Geofabrik 2024 | Raw Vector Network | Feature ablation for Model B1/B2 (`distance_to_road_m`) | **Ablated (Model B)** |
| **CWC Hourly Telemetry Features** | `data/processed/cwc_rainfall_features.csv` | CSV | 298,359 | 28 | 73 CWC Stations across NER | 2019-02-05 to 2026-09-02 | Processed Telemetry | **Runtime Tier 2 Dynamic Trigger ONLY** (Not for static ML) | **NO (Temporal Leakage)** |
| **IMD Districtwise Daily Rainfall** | `data/raw/imd/rainfall_districtwise_daily_imd.csv` | CSV | 12,366 | 22 | 98 Districts across 8 NER States | 2026-08-19 to 2026-09-04 | Raw Operational Telemetry | Runtime macro rainfall context (Not for 2014 training) | **NO (Temporal Leakage)** |
| **IMD Statewise Daily Rainfall** | `data/raw/imd/rainfall_statewise_daily_imd.csv` | CSV | 683 | 21 | 8 NER States | 2026-08-19 to 2026-09-04 | Raw Operational Telemetry | Runtime macro rainfall context (Not for 2014 training) | **NO (Temporal Leakage)** |
| **Integrated Daily Rainfall** | `data/processed/rainfall/rainfall_daily_integrated.csv` | CSV | 31,129 | 39 | 73 Stations across NER | 2019-02-05 to 2026-09-04 | Processed Merged Daily | Historical rainfall audit & operational validation | **NO (Temporal Leakage)** |
| **NESAC 2021 Verified Landslides** | `historical_landslide_events.csv` | CSV | 75 | 26 | 8 NER States | 2021 Monsoon | Authoritative Event Layer | **Runtime 3D GIS Overlay & Threshold Audit ONLY** | **NO (Test/Overlay)** |
| **Event Rainfall Windows (NESAC)** | `event_rainfall_windows.csv` | CSV | 75 | 23 | 8 NER States | 2021 Monsoon | Processed Event Antecedent | Operational rainfall trigger threshold validation | **NO (Validation Only)** |
| **Legacy Multiclass Toy Dataset** | `data/raw/landslide_training.csv` | CSV | 1,200 | 9 | Synthetic / Prototype | Undated | Derived / Legacy Prototype | Superseded by Model A; not used in production | **NO (Superseded)** |
| **Definitive Model A Training Table** | `data/processed/landslides/landslide_training_samples_proximity.csv` | CSV | 4,016 | 39 | All 8 NER States | 2014 Inventory + 2020/2021 Rasters | Processed Unified Feature Table | **Active Training Table for `static_lsm_pipeline.joblib`** | **YES (Authoritative)** |

---

## 3. Separation of Static Susceptibility vs Dynamic Triggering

A core scientific principle of this early warning system is the **strict separation** of:
- **Tier 1 — Static Landslide Susceptibility Model (Model A):**  
  Trained on inherent, stationary geospatial conditioning factors (topography, geology/soil, vegetation/land cover). These dictate the physical propensity of a slope to fail given an external trigger.
- **Tier 2 — Dynamic Rainfall Triggering Engine:**  
  Evaluates real-time, event-scale meteorology ($R_{1h}$, $R_{24h}$, $R_{72h}$) against physical hazard thresholds (WATCH at 50 mm/24h, HIGH at 100 mm/24h) with quality, freshness (6h), and distance (50 km) constraints.
- **Tier 3 — Risk Fusion Engine:**  
  Fuses Tier 1 and Tier 2 deterministically. If rainfall telemetry is unavailable or unobserved (`NO_DATA`), fusion defaults strictly to `STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED`. No fake weather or synthetic zeros are ever injected.

### Why Rainfall MUST NOT be in Model A:
1. **Temporal Disconnect:** The Bhuvan landslide events occurred in 2014. The repository's CWC station data began in February 2019. IMD operational telemetry began in August 2026. Zero rainfall records exist in the repository for the year 2014.
2. **Missing Failure Timestamps:** Bhuvan 2014 records provide only the year (`2014.0`), without month, day, or hour. Antecedent precipitation windows ($R_{24h}$, $R_{3d}$, $R_{7d}$) cannot be reconstructed without a timestamp.
3. **Severe Temporal Leakage:** Imputing modern rainfall (2019–2026) to 2014 landslide events would violate basic temporal causality.
4. **Negative Sample Imputation Bias:** Non-landslide background coordinates have no event date. Forcing an arbitrary date on negatives injects severe label bias.

---

## 4. Current Model Artifact Inspection (`model/static_lsm_pipeline.joblib`)

The fitted pipeline artifact was loaded directly in Python using `joblib` and inspected:

- **Artifact Path:** `model/static_lsm_pipeline.joblib`
- **File Size:** `3,086,396 bytes` (~2.94 MB)
- **SHA-256:** `E3B7B89F40601D61C78F14CDFEEB1324511DF1E7B680F7ACE640E9C2073BF3F5`
- **Pipeline Architecture:** `sklearn.pipeline.Pipeline` with 2 sequential steps:
  1. `preprocessor`: `sklearn.compose.ColumnTransformer`
     - **Numeric Transformer (`num`):** `SimpleImputer(strategy='median')` applied to 8 columns:
       `['elevation_m', 'slope_deg', 'aspect_deg', 'relief_std_5x5_m', 'clay_percent', 'sand_percent', 'silt_percent', 'bulk_density_kg_dm3']`
     - **Categorical Transformer (`cat`):** `Pipeline` containing `SimpleImputer(strategy='most_frequent')` and `OneHotEncoder(handle_unknown='ignore', sparse_output=False)` applied to 2 columns:
       `['soil_class', 'landcover_class']`
  2. `classifier`: `sklearn.ensemble.RandomForestClassifier`
     - `n_estimators`: 150
     - `max_depth`: 16
     - `min_samples_split`: 4
     - `min_samples_leaf`: 2
     - `class_weight`: `'balanced_subsample'`
     - `criterion`: `'gini'`
     - `max_features`: `'sqrt'`
     - `bootstrap`: `True`
     - `random_state`: 42
     - `n_features_in_`: 27 (8 numeric + 19 one-hot categories)
     - `classes_`: `[0, 1]`
- **Live Prediction Test:**
  - Input: Kohima typical terrain (`elevation_m=1400`, `slope_deg=25`, `aspect_deg=180`, `relief_std=40`, `clay=25`, `sand=40`, `silt=35`, `bdod=1.2`, `soil_class='Luvisols'`, `landcover_class='Tree cover'`)
  - Output: `predict() = [1]`, `predict_proba() = [[0.3972, 0.6028]]`
  - Status: **FITTED, OPERATIONAL, DETERMINISTIC**

---

## 5. Dataset $\rightarrow$ Feature Traceability Matrix

```
[RAW DATASETS]
 ├── data/raw/landslides/2014/*.geojson (ISRO Bhuvan 2014)
 ├── data/inspection/landslide_validation/gadm41_IND_1.json (GADM41)
 ├── data/raw/dem/copernicus_glo30/downloads/*.tif (Copernicus GLO-30)
 ├── data/raw/soil/*.tif (SoilGrids 250m)
 ├── data/raw/worldcover/esa_worldcover_v200/*.tif (ESA WorldCover 10m)
 └── data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.shp (OSM Roads)
                       ↓
[PREPROCESSING & FEATURE EXTRACTION]
 ├── scripts/build_landslide_training_samples.py  → landslide_training_samples.csv
 ├── scripts/regenerate_gadm_negatives.py        → landslide_training_samples_gadm_corrected.csv
 ├── scripts/extract_terrain_features.py         → landslide_training_samples_terrain.csv
 ├── scripts/extract_soil_features.py            → landslide_training_samples_soil.csv
 ├── scripts/extract_worldcover_features.py      → landslide_training_samples_lulc.csv
 └── scripts/build_proximity_features.py         → landslide_training_samples_proximity.csv
                       ↓
[DEFINITIVE TRAINING TABLE]
 data/processed/landslides/landslide_training_samples_proximity.csv (4,016 rows, 39 cols)
                       ↓
[TRAINING PIPELINE & ABLATION]
 scripts/train_static_lsm.py (1.0° Spatial Block Cross-Validation, 41 blocks, 5 folds)
                       ↓
[DEPLOYED PRODUCTION MODEL]
 model/static_lsm_pipeline.joblib (Model A: 10 Environmental Features)
```

### Feature-Level Traceability Table
| Feature Column | Source Raw Dataset | Extraction Script | Training Table Column | Consumed by Model A? | Consumed by Runtime Profiler? | Missing Handling Strategy |
|:---|:---|:---|:---|:---:|:---:|:---|
| `elevation_m` | Copernicus GLO-30 DEM | `extract_terrain_features.py` | `elevation_m` | **YES** | **YES** | SimpleImputer(median = 583.6m) |
| `slope_deg` | Copernicus GLO-30 DEM | `extract_terrain_features.py` | `slope_deg` | **YES** | **YES** | SimpleImputer(median = 24.5°) |
| `aspect_deg` | Copernicus GLO-30 DEM | `extract_terrain_features.py` | `aspect_deg` | **YES** | **YES** | SimpleImputer(median = 165.1°) |
| `relief_std_5x5_m` | Copernicus GLO-30 DEM | `extract_terrain_features.py` | `relief_std_5x5_m` | **YES** | **YES** | SimpleImputer(median = 17.8m) |
| `clay_percent` | SoilGrids 250m (`clay`) | `extract_soil_features.py` | `clay_percent` | **YES** | **YES** | SimpleImputer(median = 29.0%) |
| `sand_percent` | SoilGrids 250m (`sand`) | `extract_soil_features.py` | `sand_percent` | **YES** | **YES** | SimpleImputer(median = 36.9%) |
| `silt_percent` | SoilGrids 250m (`silt`) | `extract_soil_features.py` | `silt_percent` | **YES** | **YES** | SimpleImputer(median = 34.4%) |
| `bulk_density_kg_dm3` | SoilGrids 250m (`bdod`) | `extract_soil_features.py` | `bulk_density_kg_dm3` | **YES** | **YES** | SimpleImputer(median = 1.13 kg/dm³) |
| `soil_class` | SoilGrids 250m (`wrb`) | `extract_soil_features.py` | `soil_class` | **YES** | **YES** | SimpleImputer(most_frequent) + OneHot |
| `landcover_class` | ESA WorldCover 10m | `extract_worldcover_features.py` | `landcover_class` | **YES** | **YES** | SimpleImputer(most_frequent) + OneHot |
| `distance_to_road_m` | OSM Roads shapefile | `build_proximity_features.py` | `distance_to_road_m` | **NO (Ablated)** | Optional | Kept out of Model A (Model B1 feature) |
| `distance_to_river_m` | HydroSHEDS rivers | `build_proximity_features.py` | `distance_to_river_m` | **NO (Ablated)** | Optional | Kept out of Model A (Model B1 feature) |
| `distance_to_nearest_other_landslide_m` | 2014 Inventory | `build_proximity_features.py` | `distance_to_nearest_other_landslide_m` | **NO (Leakage)** | No | **REJECTED:** Spatial clustering leakage |
| `rainfall_24h` / `rainfall_3d` | CWC Telemetry | Runtime query | *None in Static Table* | **NO** | Tier 2 Only | Separated to Dynamic Trigger Tier |

---

## 6. Training Data Quality Audit

Computed across all 4,016 rows of `landslide_training_samples_proximity.csv`:

| Feature | Missing Count (%) | Unique Values | Min | Mean | Median | Max | Std Dev | Physical Reality Check |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `elevation_m` | 1 (0.02%) | 3,969 | 13.00 m | 883.67 m | 583.62 m | 7,203.00 m | 915.68 m | Valid montane elevation range |
| `slope_deg` | 1 (0.02%) | 3,971 | 0.00° | 24.07° | 24.47° | 84.92° | 13.65° | Valid slope range (steep mountain relief) |
| `aspect_deg` | 17 (0.42%) | 3,970 | 0.01° | 172.90° | 165.12° | 359.97° | 86.44° | NaN only on flat terrain (slope ~ 0°) |
| `relief_std_5x5_m` | 1 (0.02%) | 3,960 | 0.00 m | 19.28 m | 17.82 m | 254.50 m | 12.80 m | Valid local roughness range |
| `clay_percent` | 29 (0.72%) | 225 | 11.40% | 28.85% | 29.00% | 39.10% | 3.57% | Consistent with SoilGrids NEI |
| `sand_percent` | 29 (0.72%) | 320 | 15.50% | 36.55% | 36.90% | 58.50% | 5.67% | Consistent with SoilGrids NEI |
| `silt_percent` | 29 (0.72%) | 250 | 20.90% | 34.60% | 34.40% | 50.70% | 4.57% | Consistent with SoilGrids NEI |
| `bulk_density_kg_dm3` | 29 (0.72%) | 51 | 0.83 | 1.12 | 1.13 | 1.35 | 0.08 | Valid soil bulk density |
| `soil_class` | 46 (1.15%) | 11 classes | N/A | N/A | Cambisols | N/A | N/A | Top: Cambisols (1566), Acrisols (1186), Luvisols (886) |
| `landcover_class` | 0 (0.00%) | 8 classes | N/A | N/A | Tree cover | N/A | N/A | Top: Tree cover (3449), Grassland (287), Cropland (167) |

### Class-Wise Distributions (Positives vs Negatives)
- **Slope:** Landslides exhibit Mean: **28.20°** (Median: **28.79°**) vs Negatives Mean: **19.93°** (Median: **19.69°**). Landslides occur on significantly steeper terrain ($p < 10^{-15}$).
- **Local Relief (5x5):** Landslides Mean: **22.56 m** vs Negatives Mean: **15.99 m**. Landslides occur in areas with higher topographic dissection.
- **Aspect:** Positives have Median: **156.38°** (South-facing slopes intercepting monsoon moisture) vs Negatives Median: **183.04°**.
- **Data Integrity:** No infinite values (`inf`), zero-fill placeholders, or target leakage detected. Missing data is $<1.2\%$ across all features and handled via scikit-learn imputers.

---

## 7. Label Quality & Geographic Balance

### State-Wise Distribution Table
| State Code | State Name | Positive Samples | Negative Samples | Total Samples | Positive % | Minimum Negative Separation |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| `AR` | Arunachal Pradesh | 723 | 723 | 1,446 | 50.0% | $> 1,000\text{ m}$ |
| `AS` | Assam | 252 | 252 | 504 | 50.0% | $> 1,000\text{ m}$ |
| `ML` | Meghalaya | 507 | 507 | 1,014 | 50.0% | $> 1,000\text{ m}$ |
| `MN` | Manipur | 131 | 131 | 262 | 50.0% | $> 1,000\text{ m}$ |
| `MZ` | Mizoram | 354 | 354 | 708 | 50.0% | $> 1,000\text{ m}$ |
| `NL` | Nagaland | 8 | 8 | 16 | 50.0% | $> 1,000\text{ m}$ |
| `SK` | Sikkim | 21 | 21 | 42 | 50.0% | $> 1,000\text{ m}$ |
| `TR` | Tripura | 12 | 12 | 24 | 50.0% | $> 1,000\text{ m}$ |
| **TOTAL** | **All 8 NER States** | **2,008** | **2,008** | **4,016** | **50.0%** | **1,015.54 m (Min)** |

### Spatial Separation Verification:
- **Minimum distance from any negative to nearest positive:** **1,015.54 meters** (100.00% satisfy the strict $\ge 1,000\text{ m}$ buffer).
- **Median distance from negative to nearest positive:** **10,138.95 meters** (~10.1 km).
- **Zero Label Leakage:** Negative points are geographically decoupled from landslide scars, eliminating boundary contamination.

---

## 8. Geographic Leakage & Spatial Cross-Validation Audit

### Random Splitting Danger:
Standard random train/test splitting on spatial geospatial data leaks spatial autocorrelation: points from the same mountain slope or drainage basin appear in both training and test folds, artificially inflating accuracy metrics.

### Applied Methodology: 1.0° Regular Geographic Grid-Block Clustering
1. The Northeast India study area was partitioned into regular $1.0^\circ \times 1.0^\circ$ geographic grid blocks ($\sim 111\text{ km} \times 100\text{ km}$).
2. 41 distinct non-empty spatial blocks were identified.
3. Blocks were clustered into **5 balanced spatial folds** using weighted KMeans clustering on block centroids.
4. Models were strictly trained on 4 geographic folds and tested on the 5th completely held-out geographic region.

### Proximity Feature Ablation Results:
| Model Variant | Feature Set | Mean Spatial ROC-AUC | Mean Spatial PR-AUC | Mean Balanced Accuracy | Assessment |
|:---|:---|:---:|:---:|:---:|:---|
| **Model A** | **Environmental Only (Terrain + Soil + Land Cover)** | **0.8057 ± 0.0708** | **0.7950 ± 0.0545** | **0.7233 ± 0.0806** | **Scientifically Valid, Causative, Generalizable** |
| **Model B1** | Model A + Road/River Proximity | 0.8099 ± 0.0682 | 0.7981 ± 0.0521 | 0.7285 ± 0.0791 | Marginal gain (+0.0042 AUC); neutral |
| **Model B2** | Model B1 + Distance to Nearest Landslide | 0.9549 ± 0.0312 | 0.9512 ± 0.0284 | 0.8920 ± 0.0345 | **LEAKAGE:** Surges by +0.15 AUC due to inventory clustering |

**Decision:** Model A was officially selected. It relies exclusively on direct physical and environmental drivers of slope instability, ensuring robust generalization to unmapped mountain valleys.

---

## 9. Model Performance Audit

### Honest 5-Fold Spatial Cross-Validation Performance (Model A)
- **Mean Spatial ROC-AUC:** **0.8057 ± 0.0708**
  - Fold 0 (West NER - Sikkim/West Assam): `0.7024`
  - Fold 1 (Central NER - Meghalaya/Central Assam): `0.8790`
  - Fold 2 (South NER - Mizoram/Tripura): `0.7693`
  - Fold 3 (North-East NER - Arunachal Pradesh): `0.8914`
  - Fold 4 (East NER - Nagaland/Manipur): `0.7865`
- **Mean Spatial PR-AUC:** **0.7950 ± 0.0545** (Baseline prior is 0.500)
- **Mean Spatial Balanced Accuracy:** **0.7233 ± 0.0806**
- **Mean Spatial F1-Score:** **0.6885 ± 0.1206**
- **Permutation Feature Importance (Top Predictors):**
  1. `slope_deg` (Mean AUC drop: `+0.1420`)
  2. `relief_std_5x5_m` (Mean AUC drop: `+0.0485`)
  3. `elevation_m` (Mean AUC drop: `+0.0310`)
  4. `soil_class` (Mean AUC drop: `+0.0195`)
  5. `clay_percent` (Mean AUC drop: `+0.0142`)
  6. `landcover_class` (Mean AUC drop: `+0.0118`)

### Probability Calibration Evaluation:
- **Raw Random Forest Brier Score:** **0.1928**
- **Sigmoid Calibrated Brier Score:** **0.2016**
- **Finding:** Post-hoc Platt scaling / Sigmoid calibration worsened the Brier score on spatial holdouts. Consequently, post-hoc calibration was explicitly rejected. The model output is correctly documented as an **uncalibrated Random Forest susceptibility score/probability estimate**, categorized into operational tiers:
  - `LOW`: 0.00–0.25
  - `MODERATE`: 0.25–0.50
  - `HIGH`: 0.50–0.75
  - `VERY_HIGH`: 0.75–1.00

---

## 10. Classification of Retraining Necessity

Following the rigorous checklist defined in Phase 9:
- [x] Are any intended static training datasets missing from the model? **NO.** (All DEM, soil, and landcover rasters are ingested).
- [x] Is the current training data stale or corrupted? **NO.** (Authoritative Bhuvan 2014, GADM41, Copernicus GLO-30, SoilGrids 2020, ESA WorldCover 2021).
- [x] Is the training pipeline broken? **NO.** (`scripts/train_static_lsm.py` executes end-to-end with zero errors).
- [x] Does the model artifact fail to correspond to the current data? **NO.** (`static_lsm_pipeline.joblib` corresponds exactly to the 4,016 samples).
- [x] Does geographic or temporal leakage exist? **NO.** (Spatial block cross-validation and two-tier dynamic separation prevent leakage).
- [x] Are labels or features incorrect? **NO.** (Verified positive inventory, $\ge 1\text{ km}$ negative buffer, GADM containment).
- [x] Is the model artifact unfitted or failing predictions? **NO.** (Fully fitted, evaluates instantly, test suite 100% green).

### Official Classification:
```text
CLASSIFICATION: A. TRAINING COMPLETE AND VALID
RETRAINING REQUIRED: NO
```

Retraining is **scientifically unwarranted**. Retraining would provide zero functional or scientific improvement, while introducing unnecessary risk of non-deterministic parameter shifts.

---

## 11. Final Dataset & Feature Coverage Tables

### Master Dataset Inventory Table
| Dataset | Exists | Processed | Used in Training | Used in Runtime | Missing / Issues |
|:---|:---:|:---:|:---:|:---:|:---|
| **ISRO Bhuvan 2014 Landslide Inventory** | YES | YES | YES (Positives) | YES (Validation) | None; 2,008 polygons across 8 states |
| **GADM41 Administrative Boundaries** | YES | YES | YES (Negatives) | YES (Domain Check) | None; Official v4.1 geometry |
| **Copernicus GLO-30 DEM** | YES | YES | YES (Terrain) | YES (Elevation/Slope) | None; Authoritative 30m World DEM |
| **SoilGrids 250m Rasters** | YES | YES | YES (Soil) | YES (Soil Profiling) | None; ISRIC 2020 0-5cm properties |
| **ESA WorldCover 10m Rasters** | YES | YES | YES (LULC) | YES (Landcover) | None; ESA 2021 v200 global land cover |
| **OpenStreetMap Road Network** | YES | YES | YES (Model B Ablation) | Optional | Kept out of Model A to avoid bias |
| **CWC Hourly Telemetry Features** | YES | YES | NO (Tier 2 Trigger) | YES (Operational Rain) | Validated: 50km radius / 6h freshness |
| **IMD Districtwise & Statewise Daily** | YES | YES | NO (Tier 2 Context) | YES (Macro Context) | Operational current telemetry (Aug-Sep 2026) |
| **NESAC 2021 Historical Landslides** | YES | YES | NO (Validation/Overlay) | YES (3D GIS Layer) | 75 verified events from NESAC-SR-277-2022 |
| **Legacy Landslide Training CSV** | YES | NO | NO (Superseded) | NO | 1,200-row prototype; replaced by Model A |

### Feature Source & Runtime Traceability Table
| Feature | Source Dataset | Training Used | Runtime Used | Missing Value Handling |
|:---|:---|:---:|:---:|:---|
| `elevation_m` | Copernicus GLO-30 DEM | YES | YES | Median imputer (training: 583.6m; runtime: focal grid center) |
| `slope_deg` | Copernicus GLO-30 DEM | YES | YES | Median imputer (training: 24.5°; runtime: Horn's algorithm) |
| `aspect_deg` | Copernicus GLO-30 DEM | YES | YES | Median imputer (training: 165.1°; runtime: circular radians) |
| `relief_std_5x5_m` | Copernicus GLO-30 DEM | YES | YES | Median imputer (training: 17.8m; runtime: 5x5 moving window std) |
| `clay_percent` | SoilGrids 250m | YES | YES | Median imputer (training: 29.0%; runtime: bilinear sample) |
| `sand_percent` | SoilGrids 250m | YES | YES | Median imputer (training: 36.9%; runtime: bilinear sample) |
| `silt_percent` | SoilGrids 250m | YES | YES | Median imputer (training: 34.4%; runtime: bilinear sample) |
| `bulk_density_kg_dm3`| SoilGrids 250m | YES | YES | Median imputer (training: 1.13; runtime: bilinear sample) |
| `soil_class` | SoilGrids 250m | YES | YES | Mode imputer + OneHot (handle_unknown='ignore') |
| `landcover_class` | ESA WorldCover 10m | YES | YES | Mode imputer + OneHot (handle_unknown='ignore') |

### Active Production Model Status
| Model Name | Artifact Path | Training Samples | Features | Validation Strategy | Status |
|:---|:---|:---:|:---:|:---|:---:|
| **Model A (Environmental Only LSM)** | `model/static_lsm_pipeline.joblib` | 4,016 (2,008 pos, 2,008 neg) | 10 (8 numeric, 2 categorical) | 1.0° Spatial Block 5-Fold CV (ROC-AUC: 0.8057 ± 0.0708) | **ACTIVE & VERIFIED** |
| **Model B1 (Infrastructure Proximity)**| Serialized in CV report | 4,016 | 12 (+ roads, rivers) | Spatial Block 5-Fold CV (ROC-AUC: 0.8099) | Ablation Reference |
| **Model B2 (Inventory Proximity)** | Serialized in CV report | 4,016 | 13 (+ landslide dist) | Spatial Block 5-Fold CV (ROC-AUC: 0.9549) | Rejected (Leakage) |
| **Legacy Multiclass Model** | `model/landslide_model.pkl` | 1,200 | 8 | Random 5-Fold CV | Deprecated Prototype |

---

## 12. 8-Location Operational Regression Verification

The 8 operational NER state locations were evaluated against `model/static_lsm_pipeline.joblib` and runtime data layers:

| Location | Coordinates | Static Score | Susceptibility Category | Rainfall Telemetry Status | Final Risk Level | Provenance Check |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Kohima NH-29 (Nagaland)** | (25.6740°N, 94.1120°E) | 0.4595 | `MODERATE` | `NO_RELIABLE_LOCAL_DATA` (Bokajan 50.2 km > 50km) | `WATCH` (0.4595) | Genuine GLO-30 (569–2984m) |
| **Shillong Peak (Meghalaya)**| (25.5788°N, 91.8933°E) | 0.3995 | `MODERATE` | `NO_RELIABLE_LOCAL_DATA` (Guwahati 70.1 km > 50km) | `WATCH` (0.3995) | Genuine GLO-30 (851–1947m) |
| **Tezpur Sonitpur (Assam)** | (26.6338°N, 92.7926°E) | 0.1571 | `LOW` | CWC Tezpur (2.0 km, Normal) | `LOW` (0.0785) | Genuine GLO-30 (58–114m) |
| **Namchi Ridge (Sikkim)** | (27.1667°N, 88.3500°E) | 0.9005 | `VERY_HIGH` | CWC Majitar (7.2 km, Normal) | `WATCH` (0.4600) | Genuine GLO-30 (225–2622m) |
| **Imphal Valley (Manipur)** | (24.8170°N, 93.9368°E) | 0.1105 | `LOW` | CWC Amraghat (26.2 km, Normal) | `LOW` (0.0747) | Genuine GLO-30 (770–1089m) |
| **Lunglei Ridge (Mizoram)** | (22.8872°N, 92.7388°E) | 0.7638 | `VERY_HIGH` | `NO_RELIABLE_LOCAL_DATA` (GUMTI 111.4 km > 50km) | `HIGH` (0.7638) | Genuine GLO-30 (77–1521m) |
| **Agartala Baramura (Tripura)**| (23.8315°N, 91.2868°E)| 0.2441 | `LOW` | CWC Sonamura (40.0 km, Normal) | `LOW` (0.1270) | Genuine GLO-30 (0–68m) |
| **Itanagar Foothills (Arunachal)**|(27.0844°N, 93.6053°E)| 0.6347 | `HIGH` | CWC Badatighat (38.4 km, Normal) | `WATCH` (0.3271) | Genuine GLO-30 (111–2343m) |

All 8 locations return realistic, distinct susceptibility scores driven by true Copernicus GLO-30 elevation/slope and SoilGrids data, strictly enforcing the 50 km CWC distance rule and zero-synthetic-elevation policy.

---

## 13. Audit Conclusion & Recommended Next Steps

1. **Retraining Status:** **REJECTED (UNNECESSARY).** The current production model `model/static_lsm_pipeline.joblib` is scientifically sound, correctly trained, free of data leakage, and passes 100% of validation checks.
2. **Action on Evaluation PDFs:** Restore the 10 milestone evaluation walkthrough PDFs (`docs/*.pdf`) staged for deletion before committing.
3. **Commit Optimization:** Stage verified code, test, documentation, and packaging updates and proceed to git commit.
