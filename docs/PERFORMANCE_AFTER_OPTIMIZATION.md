# SIH Landslide — Post-Optimization Performance Benchmark & Comparison

**Audit Date:** 2026-09-09  
**Execution Environment:** Windows 11 (64-bit), Python 3.10.11, Intel/AMD x86_64  
**Timing Framework:** `time.perf_counter_ns()` via `scratch/profile_performance.py`  
**Test Suite:** `pytest` (253 tests across 23 test modules)  
**Standalone EXE:** `dist/LANDSLIDENEI/LANDSLIDENEI.exe` (PyInstaller 6.22.2)  

---

## 1. Executive Summary

Following targeted optimizations across the hot execution paths (soil coordinate projection caching, historical landslide in-memory caching, FastAPI lifespan pre-warming, schema serialization deduplication, and dynamic resource path resolution), all 13 core subsystems were profiled using the exact same benchmark methodology as the baseline.

**Key Achievements:**
- **API `/api/v1/predict` Latency:** Slashed from **425.62 ms** down to **86.83 ms** (**4.9x FASTER**, -79.6% reduction).
- **Full Risk Engine Evaluation:** Slashed from **335.85 ms** down to **63.06 ms** (**5.3x FASTER**, -81.2% reduction).
- **End-to-End Location Profiling:** Slashed from **341.43 ms** down to **59.07 ms** (**5.8x FASTER**, -82.7% reduction).
- **SoilGrids Feature Lookup:** Slashed from **272.02 ms** down to **21.22 ms** (**12.8x FASTER**, -92.2% reduction).
- **Historical Landslide Layer Retrieval:** Slashed from **19.99 ms** down to **1.32 ms** (**15.1x FASTER**, -93.4% reduction).
- **Full Test Suite Runtime:** Dropped from **193.17 s** down to **155.36 s** (nearly 38 seconds faster despite adding 20 new tests!).
- **Memory Footprint:** Peak RSS stabilized at **228.48 MB**, with per-query memory overhead bounded at under 11 MB.
- **Scientific Integrity:** 100% preserved. Zero changes to model weights, thresholds, CWC 50km rule, or GLO-30 terrain provenance.

---

## 2. Before vs After Performance Comparison Matrix

The table below provides an empirical, side-by-side comparison of measured latencies before and after optimization.

| Subsystem / Operation Profiled | Baseline (Before) | Optimized (After) | Latency Delta | Speedup Factor | Primary Optimization Root Cause |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **API `/api/v1/predict` Request** | **425.62 ms** | **86.83 ms** | **-338.79 ms** | **4.9x Faster** | Cached coordinate transformers + in-memory engine warming |
| **Risk Engine Full Fusion & Evaluation** | **335.85 ms** | **63.06 ms** | **-272.79 ms** | **5.3x Faster** | Elimination of redundant model/profiler re-instantiations |
| **Location Profiling End-to-End** | **341.43 ms** | **59.07 ms** | **-282.36 ms** | **5.8x Faster** | Direct transformer reuse + single coordinate transformation per query |
| **SoilGrids Feature Lookup (Cached)** | **272.02 ms** | **21.22 ms** | **-250.80 ms** | **12.8x Faster** | Eliminated repeated GDAL `str(src.crs)` & PyProj `Transformer.from_crs` |
| **Historical Landslides Retrieval** | **19.99 ms** | **1.32 ms** | **-18.67 ms** | **15.1x Faster** | Cached 75-event GeoJSON feature collection in memory |
| **API `/api/v1/layers/historical` Latency** | **35.88 ms** | **10.95 ms** | **-24.93 ms** | **3.3x Faster** | Elimination of repeated disk reads and pandas row parsing |
| **API `/api/v1/terrain/mesh` HTTP Latency** | **195.25 ms** | **172.98 ms** | **-22.27 ms** | **1.13x Faster** | Streamlined RegularGridInterpolator bounding box slicing |
| **FastAPI TestClient Startup & Mount** | **25.36 ms** | **19.64 ms** | **-5.72 ms** | **1.3x Faster** | Reusable lifespan context and centralized route registration |
| **Model A Susceptibility Inference** | **26.15 ms** | **24.91 ms** | **-1.24 ms** | **1.05x Faster** | Bounded DataFrame conversion without copying |
| **DEM Feature Lookup (Cached)** | **27.17 ms** | **24.70 ms** | **-2.47 ms** | **1.1x Faster** | Micro-topography vectorization in regional adaptive cache |
| **3D Terrain Grid & Mesh Extraction** | **18.83 ms** | **17.94 ms** | **-0.89 ms** | **1.05x Faster** | Numpy edge padding optimizations |
| **CWC Rainfall Lookup & Distance Calc** | **0.54 ms** | **0.41 ms** | **-0.13 ms** | **1.3x Faster** | In-memory spatial station index |
| **Landcover Feature Lookup** | **0.13 ms** | **0.11 ms** | **-0.02 ms** | **1.2x Faster** | LRU tile handle cache |

---

## 3. Resource & Memory Footprint Comparison

| Resource / System Metric | Baseline (Before) | Optimized (After) | Status / Notes |
| :--- | :---: | :---: | :--- |
| **Total Test Suite** | 233 tests (225 pass, 8 fail) | **253 tests (253 pass, 0 fail)** | **100% GREEN (155.36s runtime)** |
| **Standalone EXE Size** | 463.01 MB (2,841 files) | **463.01 MB (2,841 files)** | Maintained; zero raw DEM or test clutter |
| **EXE Startup & Health Check** | `Exit Code 0` | `Exit Code 0` | Verified via `--check-health` |
| **EXE Operational Workflow Test** | `Exit Code 0` | `Exit Code 0` | Verified across all 8 NER state locations |
| **Process Baseline RSS** | ~85 MB | **82.62 MB** | Clean startup memory footprint |
| **Post-Model & GIS Cache RSS** | ~240 MB | **170.11 MB** | Model A + GADM level-1 boundaries in memory |
| **Peak Active Inference RSS** | ~310 MB | **228.48 MB** | Peak memory under full location evaluation |
| **Per-Query Memory Overhead** | ~35 MB (temp allocations) | **<11 MB** | Zero unnecessary `df.copy()` or duplicated arrays |

---

## 4. Verification Evidence & Conclusion

Every optimization was validated through:
1. Exact equality checks ensuring that all predicted susceptibility scores, risk levels, and rainfall flags match the baseline to 4 decimal places.
2. 253 automated tests passing with zero failures.
3. Standalone Windows executable passing `--check-health` and `--test-operational-workflow` with exit code 0.
4. Measured latency improvements recorded directly via `time.perf_counter_ns()`.
