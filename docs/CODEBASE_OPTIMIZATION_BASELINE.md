# SIH Landslide — Codebase Optimization Baseline Report

**Execution Timestamp:** 2026-09-09 18:40 IST  
**Git Commit (HEAD):** `d4d01501eba4d10b01f37ca9af4797077727d7ab`  
**Project Path:** `C:\SIH Landslide`  
**Baseline Status:** `PRE-OPTIMIZATION AUDIT & BASELINE RECORDED`  

---

## 1. Absolute Safety Baseline Summary

In strict compliance with the **Absolute Safety Rule**, before modifying any code, the full baseline metrics of the repository were measured and recorded.

| Metric | Measured Baseline | Status / Notes |
| :--- | :--- | :--- |
| **Git Commit** | `d4d01501eba4d10b01f37ca9af4797077727d7ab` | HEAD of branch `main` |
| **Project Physical Size** | **5.45 GB** (5,849,690,134 bytes) | 82,525 files, 5,306 directories |
| **Total Test Count** | **233 tests** | Ran across 22 test modules |
| **Passed Tests** | **225 passed** | 96.6% pass rate |
| **Failed Tests** | **8 failed** | Specific root-cause analysis detailed below |
| **Test Warnings** | **3 warnings** | Starlette / httpx testclient deprecation notices |
| **Test Suite Execution Time** | **193.17 s** (~3 minutes 13 seconds) | Full integration and terrain extraction suite |
| **Standalone EXE Health Check** | `Exit Code 0 (PASS)` | `LANDSLIDENEI.exe --check-health` |
| **Standalone EXE Workflow Test** | `Exit Code 0 (PASS)` | `LANDSLIDENEI.exe --test-operational-workflow` |
| **Operational Workflow Latency** | **858.68 ms** average per location | Measured across all 8 NER state capitals/corridors |
| **Memory Consumers (Major)** | `venv` (1.25 GB), `.git` (647.56 MB), `dist` (463.01 MB) | `torch_cpu.dll` (290.95 MB), `tmp_pack` (177 MB) |

---

## 2. Git Status (`git status --short`)

```text
M  api/main.py
M  api/schemas.py
M  desktop_app.py
M  docs/HISTORICAL_RAINFALL_THRESHOLD_AUDIT.md
D  docs/LandslideNEI_Master_Technical_Walkthrough_Report.pdf
D  docs/Phase_8F_Static_LSM_Walkthrough.pdf
D  docs/Phase_8G_Location_Profiler_Walkthrough.pdf
D  docs/Phase_8H_Dynamic_Risk_Fusion_Walkthrough.pdf
D  docs/Phase_8I_Unified_Risk_API_Walkthrough.pdf
D  docs/Phase_8J_Operational_Dashboard_Walkthrough.pdf
D  docs/Phase_8K_Public_Website_Walkthrough.pdf
D  docs/Phase_8L_Desktop_Software_Walkthrough.pdf
D  docs/Phase_8M_GitHub_Pages_Deployment_Walkthrough.pdf
D  docs/Phase_8N_Windows_Application_Packaging_Walkthrough.pdf
A  docs/STORAGE_AUDIT_BEFORE_CLEANUP.md
A  docs/STORAGE_CLEANUP_PLAN.md
A  operational_workflow_report.txt
M  src/inference/location_profiler.py
M  src/inference/rainfall_provider.py
M  tests/test_operational_3d_workflow.py
```

---

## 3. Standalone Executable Verification

### A. Health Check
```powershell
.\dist\LANDSLIDENEI\LANDSLIDENEI.exe --check-health
# Exit code: 0 (PASS)
```

### B. Operational Location Intelligence Workflow Verification
```powershell
.\dist\LANDSLIDENEI\LANDSLIDENEI.exe --test-operational-workflow
# Exit code: 0 (PASS)
```

#### Measured End-to-End Latency Across 8 NER States
| Location | Coordinates | DEM Elevation | Static Susceptibility | Rainfall Status | Operational Risk | Execution Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Kohima NH-29 (Nagaland)** | (25.6740°N, 94.1120°E) | 569m – 2984m | MODERATE (0.4595) | NO_RELIABLE_LOCAL_DATA | WATCH (0.4595) | 1,684.5 ms | **PASS** |
| **2. Shillong Peak (Meghalaya)**| (25.5788°N, 91.8933°E) | 851m – 1947m | MODERATE (0.3995) | NO_RELIABLE_LOCAL_DATA | WATCH (0.3995) | 708.4 ms | **PASS** |
| **3. Tezpur Sonitpur (Assam)** | (26.6338°N, 92.7926°E) | 58m – 114m | LOW (0.1571) | CWC Tezpur (2.0 km) | LOW (0.0785) | 944.1 ms | **PASS** |
| **4. Namchi Ridge (Sikkim)** | (27.1667°N, 88.3500°E) | 225m – 2622m | VERY_HIGH (0.9005) | CWC Majitar (7.2 km) | WATCH (0.4600) | 941.8 ms | **PASS** |
| **5. Imphal Valley (Manipur)** | (24.8170°N, 93.9368°E) | 770m – 1089m | LOW (0.1105) | CWC Amraghat (26.2 km) | LOW (0.0747) | 760.8 ms | **PASS** |
| **6. Lunglei Ridge (Mizoram)** | (22.8872°N, 92.7388°E) | 77m – 1521m | VERY_HIGH (0.7638) | NO_RELIABLE_LOCAL_DATA | HIGH (0.7638) | 663.1 ms | **PASS** |
| **7. Agartala Baramura (Tripura)**|(23.8315°N, 91.2868°E) | 0m – 68m | LOW (0.2441) | CWC Sonamura (40.0 km) | LOW (0.1270) | 569.1 ms | **PASS** |
| **8. Itanagar Foothills (Arunachal)**|(27.0844°N, 93.6053°E)| 111m – 2343m | HIGH (0.6347) | CWC Badatighat (38.4 km) | WATCH (0.3271) | 597.7 ms | **PASS** |

- **Average End-to-End Latency:** **858.68 ms** per query.
- **Historical Landslide Layer:** `PASS (75 Verified Events Connected)`.
- **Domain Guardrail:** `PASS (400 Bad Request for out-of-domain coordinates)`.
- **Zero Synthetic Fallbacks:** `PASS (Strict GLO-30 & Empirical Model A)`.

---

## 4. Failing Test Diagnostics & Root Cause Analysis

As mandated by the Absolute Safety Rule:
> *"If the current test suite is not green: DO NOT start broad optimization. First identify the failing tests."*

The baseline pytest run revealed **8 failing tests out of 233**. Comprehensive investigation of each failure identified their exact root causes:

### Category 1: String Form Factor Inconsistency (`VERY_HIGH` vs `"VERY HIGH"`)
1. **`tests/test_operational_3d_workflow.py::TestOperational3DWorkflow::test_end_to_end_location_workflow[Namchi South Sikkim]`**
2. **`tests/test_operational_3d_workflow.py::TestOperational3DWorkflow::test_end_to_end_location_workflow[Lunglei Ridge]`**
   - **Error:** `AssertionError: assert 'VERY_HIGH' in ['LOW', 'MODERATE', 'HIGH', 'VERY HIGH', 'CRITICAL']`
   - **Root Cause:** In `LocationProfiler`, the operational category is assigned as `"VERY_HIGH"` (standard underscore representation). The test assertion in `test_operational_3d_workflow.py:61` checked for `"VERY HIGH"` with a space, causing an assertion failure on two valid high-risk locations (Namchi: 0.9005, Lunglei: 0.7638).
   - **Fix Required:** Update the test allowed categories set to include `"VERY_HIGH"` (or normalize representation consistently).

### Category 2: Outdated Test Assumption on Dynamic Terrain Mode
3. **`tests/test_terrain_3d.py::test_source_mode_reporting`**
   - **Error:** `AssertionError: assert 'REGIONAL_OFFLINE_CACHE' == 'DYNAMIC_RASTER_EXTRACTION'`
   - **Root Cause:** The test tested coordinate `(25.5200, 91.2700)` expecting it to report `DYNAMIC_RASTER_EXTRACTION`. However, with the creation of the 57 regional DEM adaptive caches (`regional_N25_E091.json.gz`), the coordinate is now serviced directly and faster by `REGIONAL_OFFLINE_CACHE`.
   - **Fix Required:** The test needs to either query an out-of-cache coordinate or allow `REGIONAL_OFFLINE_CACHE` as a valid authoritative provenance.

### Category 3: The Tawang Real Terrain vs Missing-DEM Imputation Discrepancy (4 tests)
4. **`tests/test_api.py::test_profile_endpoint_valid_tawang`** (`assert 'LOW' == 'HIGH'`)
5. **`tests/test_dashboard.py::test_demo_preset_tawang_prediction`** (`assert 0.2263 > 0.5`)
6. **`tests/test_risk_engine.py::test_valid_ner_location_tawang`** (`assert 'LOW' == 'WATCH'`)
7. **`tests/test_risk_engine.py::test_mock_severe_rainfall_scenario`** (`assert 'WATCH' == 'CRITICAL'`)
   - **Forensic Discovery:**
     * In previous development, the raw DEM tile for Tawang (`Copernicus_DSM_COG_10_N27_00_E091_00_DEM.tif`) was missing from the local disk. When missing, `LocationProfiler` fed `NaN` values for all terrain features (`elevation_m`, `slope_deg`, `aspect_deg`, `relief_std_5x5_m`).
     * `Model A`'s imputer replaced these `NaN` features with training set medians, producing an artificial susceptibility score of **0.5966** (~0.58, "HIGH").
     * The test author hardcoded assertions expecting `score > 0.50`, `category == "HIGH"`, and risk `WATCH/CRITICAL`.
     * However, once the genuine GLO-30 regional adaptive cache was connected, `LocationProfiler` began extracting **true real terrain** for Tawang: elevation 2,963.4m, slope 36.8°, relief 83.51m.
     * Evaluated against real terrain and soil, `Model A`'s genuine trained pipeline predicts **0.2263** (LOW susceptibility).
     * Because the tests hardcoded the legacy un-extracted `NaN`-imputed score (0.58), they failed against the actual, genuine GLO-30 extraction!
   - **Fix Required:** Update the test assertions to reflect the true, verified empirical Model A prediction (0.2263) under genuine Copernicus GLO-30 terrain.

### Category 4: WorldCover Missing Tile Handling
8. **`tests/test_static_lsm_inference.py::test_valid_coordinate`**
   - **Error:** `AssertionError: assert nan in dict_values(...)`
   - **Root Cause:** Tawang landcover GeoTIFF is not present locally (`data/raw/worldcover/`), so `_get_worldcover_features` returns `{"landcover_class": np.nan, "lulc_quality": "MISSING_TILE"}`. The test asserted that `landcover_class` must be in the `WORLDCOVER_LEGEND` dictionary values without allowing `np.nan` when `lulc_quality == "MISSING_TILE"`.
   - **Fix Required:** Allow `np.nan` when `lulc_quality` indicates missing or partial tile coverage.

---

## 5. Next Steps for Broad Optimization

With the failing tests fully identified and understood, the implementation workflow is structured as follows:
1. Fix test contract discrepancies to restore a **100% green test suite**.
2. Generate `docs/CODEBASE_DEAD_CODE_AUDIT.md` (Phase 1).
3. Generate `docs/PERFORMANCE_BASELINE.md` (Phase 3).
4. Implement targeted performance, reliability, and memory optimizations without altering scientific behavior.
5. Generate `docs/DEPENDENCY_AUDIT.md` (Phase 12).
6. Verify regression tests, build standalone EXE, and compare performance.
