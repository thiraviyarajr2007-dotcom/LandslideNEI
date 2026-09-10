# SIH Landslide — Dependency Audit & Classification Report

**Audit Date:** 2026-09-09  
**Python Version:** Python 3.10.11 (64-bit)  
**Environment:** `C:\SIH Landslide\venv`  
**Mandate:** Phase 12 Dependency Audit  

---

## 1. Executive Summary

This audit inspects all dependencies installed in the virtual environment (`venv`) and declared in `requirements.txt`. Every package was evaluated against the active runtime call graphs of:
- `src/` (Scientific inference: DEM, Soil, Rainfall, Fusion)
- `api/` (FastAPI REST service)
- `desktop_app.py` & `LANDSLIDENEI.spec` (Desktop distribution)
- `tests/` (Test suite)
- `scripts/` (Offline data ingestion & QC)

In strict accordance with Phase 12 guidelines:
> *"IMPORTANT: Do NOT uninstall anything immediately. Create docs/DEPENDENCY_AUDIT.md. Classify: REQUIRED RUNTIME, REQUIRED DEVELOPMENT, OPTIONAL, UNUSED, NEEDS VERIFICATION. Only remove a dependency after confirming that source imports do not use it, scripts do not use it, tests do not use it, packaging does not use it."*

---

## 2. Dependency Classification Matrix

### Category A: REQUIRED RUNTIME (Core Application, Scientific Inference & Desktop EXE)
These packages are critical for live execution, Model A evaluation, spatial GIS processing, and the API server.

| Package | Version | Primary Usage & Module Callers |
| :--- | :---: | :--- |
| **`fastapi`** | 0.141.1 | REST API framework (`api/main.py`) |
| **`uvicorn`** | 0.52.4 | ASGI web server for API and Desktop embedded server (`desktop_app.py`) |
| **`pydantic`** | 2.13.5 | Strict input validation and contract serialization (`api/schemas.py`) |
| **`python-multipart`** | 0.0.32 | Form parsing for file and multipart API requests |
| **`scikit-learn`** | 1.7.2 | Model A Random Forest susceptibility pipeline (`src/inference/location_profiler.py`) |
| **`joblib`** | 1.6.0 | Serialized model artifact unpickling (`model/static_lsm_pipeline.joblib`) |
| **`numpy`** | 2.2.6 | Numerical matrix operations, terrain gradients, micro-topography calculations |
| **`scipy`** | 1.15.3 | `RegularGridInterpolator` for 3D terrain resampling (`src/inference/terrain_service.py`) |
| **`pandas`** | 2.3.3 | CWC rainfall parsing, CSV loading, historical landslide event management |
| **`rasterio`** | 1.4.4 | Copernicus DEM GLO-30 and SoilGrids v2.0 GeoTIFF raster sampling |
| **`pyproj`** | 3.7.1 | Geodetic coordinate transformation (EPSG:4326 to SoilGrids Homolosine) |
| **`shapely`** | 2.1.2 | GADM level-1 administrative boundaries and spatial point-in-polygon verification |

---

### Category B: REQUIRED DEVELOPMENT & PACKAGING
These packages are required for testing, automated verification, and standalone binary packaging.

| Package | Version | Usage & Role |
| :--- | :---: | :--- |
| **`pytest`** | 9.1.1 | Test execution harness (233+ test suite in `tests/`) |
| **`pyinstaller`** | 6.22.2 | Standalone Windows distribution compiler (`LANDSLIDENEI.spec`) |
| **`httpx`** | 0.28.1 | High-speed ASGI test client for FastAPI endpoint testing |
| **`reportlab`** | 5.0.1 | Automated PDF technical report and walkthrough generation (`scripts/`) |

---

### Category C: OPTIONAL / DIAGNOSTIC
These packages are used for exploratory data analysis, plotting, and offline document processing.

| Package | Version | Usage & Role |
| :--- | :---: | :--- |
| **`requests`** | 2.34.2 | HTTP queries for remote Open-Meteo telemetry fallback and deployment checks |
| **`matplotlib`** | 3.10.9 | Diagnostic ROC/PR curve plotting, SHAP figure rendering |
| **`pymupdf`** | 1.28.2 | Offline PDF text extraction for historical landslide reports |
| **`pypdf`** | 6.17.0 | Secondary PDF parsing utility |

---

### Category D: UNUSED / HEAVY EXPERIMENTAL CANDIDATES
These packages were installed for exploratory NLP experiments on unstructured Geological Survey of India (GSI) bulletins. They are **never imported or referenced** by `src/`, `api/`, `desktop_app.py`, `tests/`, or the packaged `LANDSLIDENEI.exe`.

| Package | Size on Disk | Reason for Non-Usage in Runtime / Packaging |
| :--- | :---: | :--- |
| **`torch`** | ~1,520 MB | Deep learning framework; Model A is a CPU Scikit-Learn Random Forest. PyTorch is not used at runtime. |
| **`transformers`** | ~180 MB | Hugging Face transformer models; not used in operational inference. |
| **`peft`** | ~25 MB | Parameter-efficient fine-tuning; exploratory only. |
| **`accelerate`** | ~15 MB | PyTorch multi-GPU training utility; unused. |
| **`gliner2`** | ~35 MB | Generalist Named Entity Recognition for historical text mining; not part of core inference. |
| **`sentencepiece`**| ~10 MB | Tokenizer for LLMs; unused by Random Forest or CWC pipeline. |
| **`protobuf`** | ~8 MB | Serializer for neural net graphs; unused. |

> [!NOTE]
> While these experimental packages account for over **1.8 GB** of virtual environment disk space, they are already **excluded** from `LANDSLIDENEI.spec` and are NOT packaged into `LANDSLIDENEI.exe`. As per safety rules, they will remain untouched in the local virtual environment to preserve historical experiment reproducibility.

---

## 3. Production Deployment Recommendation

For a clean, lightweight production server deployment (e.g. Docker or cloud VM), a streamlined `requirements-production.txt` containing only Category A packages would reduce installation size from ~3.2 GB to under ~250 MB while preserving 100% of operational functionality.
