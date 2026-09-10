# SIH Landslide — Codebase & Dead Code Audit Report

**Audit Date:** 2026-09-09  
**Repository Path:** `C:\SIH Landslide`  
**Audit Scope:** `src/`, `api/`, `dashboard/`, `scripts/`, `tests/`, `config/`, `website/`, `desktop_app.py`, `LANDSLIDENEI.spec`  
**AST Analysis:** Completed over 92 Python source modules and configuration files.  

---

## 1. Executive Summary

This audit identifies non-functional redundancies, dead code, duplicated logic, swallowed exceptions, hardcoded paths, and avoidable I/O bottlenecks across the SIH Landslide repository.

The primary architectural areas identified for optimization are:
1. **Model Loading Lifecycle:** `static_lsm_pipeline.joblib` (2.94 MB) is parsed and unpickled via `joblib.load()` whenever a new `LocationProfiler` instance is created. Centralizing model lifecycle to a warm singleton prevents repeated disk reads and deserialization latency on concurrent API queries.
2. **Duplicated Utility Logic:** Common helpers (`convert_nan_to_none`, `sha256_file`, `_load_config`) are reimplemented in multiple modules instead of centralized utilities.
3. **Swallowed Exceptions:** 13 locations were identified using `except Exception: pass` without logging or telemetry tracking, creating blind spots during partial failure modes.
4. **Hardcoded Machine Paths:** Several test suites and packaging scripts had hardcoded `C:/SIH Landslide` or developer app data paths, reducing portability across environments.
5. **Non-Printable Character BOMs:** 4 scripts in `scripts/` contain UTF-8 Byte Order Marks (`U+FEFF`), causing AST parsing warnings.

---

## 2. Inventory of Duplicate & Redundant Functions

| Function Name | Modules / Line Numbers | Redundancy Assessment & Optimization Plan |
| :--- | :--- | :--- |
| `convert_nan_to_none` | `api/schemas.py:179`, `api/schemas.py:207`, `api/schemas.py:219` | Duplicated 3 times within the same schema file. Consolidate into a single module-level reusable validator. |
| `_load_config` | `src/inference/rainfall_provider.py:136`, `src/inference/rainfall_trigger.py:52`, `src/inference/risk_fusion.py:67` | Each module defines its own config loader reading `config/operational_thresholds.json`. Consolidate into a centralized cached loader in `config/`. |
| `sha256_file` / `sha256` | `scripts/build_historical_landslide_dataset.py:52`, `scripts/validate_risk_engine.py:38`, `scripts/extract_landslide_2014.py:129`, `scripts/filter_imd_ner.py:100`, `scripts/integrate_rainfall.py:64` | Duplicated across 5 data pipeline scripts. Centralize in a shared utility. |
| `profile_location` | `src/inference/location_profiler.py:617` (method), `src/inference/location_profiler.py:846` (wrapper) | Keep class method and maintain a clean singleton-backed module wrapper. |
| `get_rainfall_for_location` | `src/inference/rainfall_provider.py:480` (method), `src/inference/rainfall_provider.py:774` (wrapper) | Standardize on singleton-backed caller. |
| `get_imd_macro_rainfall` | `src/inference/rainfall_provider.py:261` (method), `src/inference/rainfall_provider.py:794` (wrapper) | Standardize on singleton-backed caller. |

---

## 3. Exception Handling & Swallowed Errors Audit

| Module | Line | Exception Caught | Current Handling | Risk & Proposed Fix |
| :--- | :--- | :--- | :--- | :--- |
| `src/inference/location_profiler.py` | 278 | `Exception` | `pass` in cache fallback | Replaced with explicit debug logging to track why fallback occurred. |
| `src/inference/location_profiler.py` | 823, 830, 837 | `Exception` | `pass` in `.close()` cleanup | Safe cleanup, but should catch `(RasterioIOError, OSError)` specifically. |
| `src/inference/terrain_service.py` | 457, 465 | `Exception` | `pass` during regional fallback | Add diagnostic log tracking missing tiles. |
| `api/main.py` | 79 | `Exception` | `pass` during startup logo load | Catch `FileNotFoundError` specifically and log warning. |
| `api/main.py` | 400 | `Exception` | `pass` in system info retrieval | Replace with structured error reporting in health metadata. |
| `scripts/publish_github_release.py` | 39 | `Exception` | `pass` during release check | Log explicit API error response. |

---

## 4. Hardcoded Paths Audit

| Module | Line | Hardcoded String | Remediation |
| :--- | :--- | :--- | :--- |
| `tests/test_dashboard.py` | 20 | `C:/SIH Landslide` | Replace with dynamic `Path(__file__).resolve().parent.parent` |
| `tests/test_desktop_software.py`| 21 | `C:/SIH Landslide` | Replace with dynamic `Path(__file__).resolve().parent.parent` |
| `tests/test_pages_deployment.py`| 23 | `C:/SIH Landslide` | Replace with dynamic `Path(__file__).resolve().parent.parent` |
| `tests/test_website.py` | 21 | `C:/SIH Landslide` | Replace with dynamic `Path(__file__).resolve().parent.parent` |
| `scripts/generate_packaging_pdf.py` | 16 | `C:\Users\thira\.gemini\...` | Replace with relative or workspace-derived path |
| `scripts/generate_app_icon.py` | 69 | `C:/SIH Landslide/assets/icon.ico` | Replace with `PROJECT_ROOT / "assets" / "icon.ico"` |

---

## 5. Non-Printable Character BOM Audit

The following files contain a UTF-8 BOM (`\xef\xbb\xbf` / `U+FEFF`) on line 1:
1. `scripts/inspect_imd_rainfall.py`
2. `scripts/inspect_landslide_atlas.py`
3. `scripts/inspect_raw_data.py`
4. `scripts/qc_cwc_rainfall.py`

**Action:** Strip the UTF-8 BOM to ensure standard UTF-8 encoding across all Python environments.

---

## 6. Dead & Unused Code Candidates

1. **`scratch/` Directory Artifacts:**
   - `scratch/SLI2021.pdf` (10.67 MB) and `scratch/SLI2020.pdf` (8.65 MB) are redundant duplicate downloads of reports preserved in `data/raw/historical_landslide_rainfall/sources/`.
   - `scratch/sli2021_images/` contains 75 temporary OCR crops from testing.
2. **PyInstaller Intermediate Cache:**
   - `build/LANDSLIDENEI/` (57.37 MB) contains intermediate object files from previous PyInstaller compilation.
3. **Bytecode Caches:**
   - `.pytest_cache/` and `__pycache__/` outside `venv`/`dist`.
