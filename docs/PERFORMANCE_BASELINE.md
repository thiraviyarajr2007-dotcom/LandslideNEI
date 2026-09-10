# SIH Landslide — Pre-Optimization Performance Baseline

**Audit Date:** 2026-09-09  
**Execution Environment:** Windows 11, Python 3.10.11 (64-bit), Intel/AMD x86_64  
**Git Commit (HEAD):** `d4d01501eba4d10b01f37ca9af4797077727d7ab`  
**Measurement Tool:** High-resolution `time.perf_counter_ns()` via `scratch/profile_performance.py`  

---

## 1. Executive Summary

In compliance with **Phase 3 (Performance Audit)**, all primary subsystems across the scientific inference pipeline, REST API layer, 3D terrain extraction, and standalone Windows executable were profiled to establish a rigorous, evidence-based performance baseline before implementing code optimizations.

---

## 2. Comprehensive Measured Baseline Latencies

The table below lists the measured latency for each required profile operation, ranked from slowest to fastest.

| Rank | Operation / Subsystem | Measured Baseline Latency | Execution Context / Notes |
| :---: | :--- | :---: | :--- |
| **1** | **LocationProfiler Cold Initialization** | **3,455.93 ms** | Deserializing `static_lsm_pipeline.joblib` (2.94 MB) via `joblib.load()` + parsing GADM GeoJSON borders. |
| **2** | **Standalone EXE End-to-End Workflow** | **858.68 ms** | Average per-location end-to-end evaluation inside frozen `LANDSLIDENEI.exe` across all 8 NER state capitals. |
| **3** | **API `/api/v1/predict` Request Latency** | **425.62 ms** | Full HTTP request-response cycle via FastAPI TestClient (DEM + Soil + Model A + CWC + Fusion). |
| **4** | **Location Profiling End-to-End** | **341.43 ms** | `LocationProfiler.profile_location()` hot execution (terrain extraction + soil + landcover + Model A). |
| **5** | **Risk Engine Full Fusion & Evaluation** | **335.85 ms** | Complete pipeline fusion (Location profiling + CWC lookup + trigger matrix + 50km rule + explainability). |
| **6** | **SoilGrids Feature Lookup (Cached)** | **272.02 ms** | 4-layer SoilGrids raster extraction (`bdod`, `clay`, `sand`, `silt`). Bottleneck: instantiating PyProj `Transformer.from_crs` inside a 4-iteration loop. |
| **7** | **API `/api/v1/terrain/mesh` HTTP Latency** | **195.25 ms** | Extraction and JSON serialization of 128x128 elevation grid + normals + texture coordinates. |
| **8** | **API `/api/v1/layers/historical-landslides`** | **35.88 ms** | HTTP endpoint reading GeoJSON feature collection and serializing 75 historical landslide points. |
| **9** | **DEM Feature Lookup (Cached)** | **27.17 ms** | Extraction of elevation, slope, aspect, relief from GLO-30 regional adaptive cache. |
| **10** | **Model A Susceptibility Inference** | **26.15 ms** | Scikit-learn Random Forest inference (100 estimators) on 8 engineered features via `pipeline.predict_proba()`. |
| **11** | **FastAPI TestClient Startup & Mount** | **25.36 ms** | Instantiation and mounting of FastAPI application routes, middleware, and CORS policies. |
| **12** | **Historical Landslides Retrieval (Direct)** | **19.99 ms** | Direct disk read and `json.loads()` of `data/processed/historical_landslides_75.geojson`. |
| **13** | **3D Terrain Grid & Mesh Extraction (128x128)**| **18.83 ms** | Pure computation of 16,384 vertex coordinates and height-map interpolation. |
| **14** | **CWC Rainfall Lookup & Distance Calc** | **0.54 ms** | Spatial Haversine distance search across CWC telemetric stations and temporal freshness check. |
| **15** | **Landcover Feature Lookup** | **0.13 ms** | ESA WorldCover raster/cache lookup. |

---

## 3. Top 10 Performance Bottlenecks & Optimization Targets

1. **`LocationProfiler` Cold Initialization (3,455.93 ms):**
   - *Cause:* Model pipeline (`static_lsm_pipeline.joblib`) is read from disk and unpickled via `joblib.load()`.
   - *Target:* Pre-warm a global singleton inside FastAPI `lifespan` startup, ensuring zero cold-start delay during live HTTP requests.

2. **Standalone EXE Latency (858.68 ms):**
   - *Cause:* File decompression and dynamic link resolution in PyInstaller frozen environment.
   - *Target:* Leverage in-memory singletons and cached coordinate transformers to bring EXE latency under 700 ms.

3. **API `/api/v1/predict` Latency (425.62 ms):**
   - *Cause:* Cumulative sum of soil transformation, model inference, and Pydantic serialization.
   - *Target:* Optimize underlying soil extraction to bring prediction response time under 150 ms.

4. **Location Profiling End-to-End (341.43 ms):**
   - *Cause:* 80% of location profiling time is spent in `_get_soil_features()`.
   - *Target:* Bring overall profiling under 80 ms by fixing the soil coordinate transformation bottleneck.

5. **Risk Engine Full Fusion (335.85 ms):**
   - *Cause:* Dominated by location profiling latency.
   - *Target:* Parallelize or optimize underlying feature extraction so total fusion latency drops to <100 ms.

6. **SoilGrids Coordinate Transformation (272.02 ms):**
   - *Cause:* In `LocationProfiler._get_soil_features()`, `Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)` is re-created 4 times (once per soil layer: `bdod`, `clay`, `sand`, `silt`). Recreating the proj transformer takes ~68 ms per call!
   - *Target:* Cache the PyProj `Transformer` instance once as an instance attribute (`self._homolosine_transformer`). Eliminating redundant transformer instantiation will reduce soil lookup from 272 ms to <15 ms!

7. **API `/api/v1/terrain/mesh` (195.25 ms):**
   - *Cause:* Repeated JSON encoding of 16,384 float elevation values and mesh metadata.
   - *Target:* Optimize array serialization and avoid redundant float conversions.

8. **Historical Landslides Direct Disk I/O (19.99 ms direct, 35.88 ms API):**
   - *Cause:* Every call to `get_historical_landslides()` or `/api/v1/layers/historical-landslides` opens, reads, and parses `data/processed/historical_landslides_75.geojson` from disk.
   - *Target:* Cache the parsed GeoJSON dictionary in memory after first load.

9. **DEM Feature Lookup (27.17 ms):**
   - *Cause:* File decompression of regional JSON.GZ tiles when navigating between coordinate bounds.
   - *Target:* Ensure the LRU cache of regional tiles retains recently queried tiles without repeated decompression.

10. **Model A Random Forest Inference (26.15 ms):**
    - *Cause:* 100 decision trees traversing 8 features.
    - *Target:* Preserve exact model weights and predictions; avoid unnecessary DataFrame conversion or copying prior to `pipeline.predict_proba()`.
