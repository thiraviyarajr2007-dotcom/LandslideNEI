# LANDSLIDENEI: Operational Landslide Early Warning & Risk Intelligence System for Northeast India

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Pytest Suite](https://img.shields.io/badge/Tests-202%20Passed-success.svg)](tests/)
[![Windows Standalone](https://img.shields.io/badge/Windows-x64%20Installer-informational.svg)](https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/tag/v1.0.0)
[![GitHub Pages](https://img.shields.io/badge/Website-GitHub%20Pages-brightgreen.svg)](https://thiraviyarajr2007-dotcom.github.io/LandslideNEI/)

**LANDSLIDENEI** is an end-to-end operational geotechnical intelligence and landslide early-warning platform purpose-built for the eight states of **Northeast India** (Arunachal Pradesh, Assam, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, and Tripura).

The platform couples high-resolution terrain morphometry, multi-layer soil hydrology, real-time hydrological telemetry, and machine learning into an authoritative decision-support system for state disaster management authorities (SDMAs), the Central Water Commission (CWC), the National Disaster Response Force (NDRF), and regional emergency operation centers (EOCs).

---

## Architecture Overview

```
                                  LANDSLIDENEI PLATFORM
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
             PUBLIC WEBSITE                              WINDOWS DESKTOP SOFTWARE
                    │                                               │
       Marketing & Dissemination                    Tactical EOC Command Workstation
                    │                                               │
         theme/website_theme.zip                         theme/software_theme.zip
                    │                                               │
        Product Overview & Showcase                     Duty Officer Auth & Sector Command
                    │                                               │
        Download for Windows (.exe)                     Real ML / Geotechnical Risk Engine
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            │
                                     GitHub Release
                                            │
                                LANDSLIDENEI_Setup_x64.exe (73.8 MB)
```

---

## Key Features

- **Multi-Source Geotechnical Synthesis**:
  - **Copernicus DEM (30m)**: Elevation, slope gradient, plan/profile curvature, aspect, and Topographic Wetness Index ($TWI$).
  - **ISRIC SoilGrids (250m)**: Sand, silt, clay percentages, bulk density, saturated hydraulic conductivity ($K_{sat}$), and effective soil cohesion ($c'$).
  - **ESA WorldCover (10m)**: High-resolution land use / land cover classification and root cohesion reinforcement factors.
  - **Central Water Commission (CWC) Telemetry**: Hourly precipitation feeds from 73 automated hydrological stations with spatial Haversine KD-Tree nearest-neighbor indexing.
  - **IMD Macro-Scale Rainfall Integration**: District- and state-level daily rainfall departures and historical normal baselines.

- **Dual-Layer Physical & Machine Learning Fusion**:
  - **Static Susceptibility Engine (Model A)**: Calibrated Random Forest pipeline (`model/static_lsm_pipeline.joblib`) evaluated with spatial cross-validation.
  - **Transient Pore-Water Pressure Model**: Dynamic Saxton-Rawls unsaturated soil mechanics estimating pore pressure ($u$) buildup during antecedent rainfall.
  - **Deterministic Risk Fusion**: Synthesizes static susceptibility classes with dynamic rainfall trigger tiers into an operational matrix (`LOW`, `WATCH`, `HIGH`, `CRITICAL`).

- **Two Distinct Presentation Layers**:
  1. **Public Product Website** (`website/`): High-contrast dark glass product showcase hosted live on GitHub Pages at `https://thiraviyarajr2007-dotcom.github.io/LandslideNEI/`.
  2. **EOC Workstation Desktop Application** (`dashboard/` + `desktop_app.py`): Dedicated command control room software featuring duty officer authentication, Leaflet GIS mapping, real-time coordinate profiling, and PDF report export.

- **Standalone Offline Windows Installer**:
  - Bundled as `LANDSLIDENEI_Setup_x64.exe` (73.8 MB) using 7-Zip LZMA2 ultra-compression.
  - Includes embedded Python runtime, pre-compiled dependencies, frozen machine learning model, and offline boundary datasets. No external installation or command-line setup required.

---

## Repository Structure

```
c:\SIH Landslide\
├── api/                           # Unified FastAPI REST backend
│   ├── main.py                    # API entrypoint, routes, static mounts
│   └── schemas.py                 # Pydantic v2 request/response contracts
├── assets/                        # Icons, branding, application icons
├── config/                        # Operational thresholds and API settings
│   ├── api.json                   # Host, port, rate limiting, and CORS configs
│   └── risk_thresholds.json       # Geotechnical and rainfall trigger parameters
├── dashboard/                     # Tactical GIS EOC Workstation (HTML5/Vanilla CSS/JS)
│   ├── index.html                 # EOC Command Workstation interface
│   ├── css/                       # Obsidian dark theme stylesheets
│   └── js/                        # Leaflet GIS, state management, audio alerts
├── data/                          # Spatial boundaries, validation sets, and samples
│   ├── inspection/                # Validation reports, GADM boundary JSONs, and metrics
│   ├── processed/                 # Processed features and CWC station seed catalogs
│   └── raw/                       # Raw input data (git-ignored)
├── desktop_app.py                 # Windows desktop launcher with embedded Uvicorn server
├── docs/                          # Technical walkthroughs, architecture specs, and PDFs
├── installer/                     # Standalone Windows executable installer artifact
├── model/                         # Frozen Random Forest pipeline and metadata
│   ├── static_lsm_pipeline.joblib # Production model checkpoint
│   └── static_lsm_metadata.json   # Model performance metrics and hyperparameters
├── scripts/                       # Training, evaluation, packaging, and release scripts
│   ├── build_desktop_app.py       # PyInstaller standalone executable compilation
│   ├── build_windows_installer.ps1# 7-Zip SFX installer packager
│   ├── port80_redirect.py         # Local port 80 to 8000 HTTP redirect service
│   └── publish_github_release.py  # Automated GitHub Release verification & upload
├── src/                           # Core geotechnical and machine learning engine
│   └── inference/                 # Location profiler, rainfall provider, risk engine
├── tests/                         # Pytest automated test suite (202 test cases)
└── website/                       # Public product website (deployed to GitHub Pages)
```

---

## Quickstart Guide

### 1. Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.10+ (for source development)
- Microsoft Edge or Google Chrome (for native desktop workstation view)

### 2. Setting Up Development Environment

```powershell
# Clone repository
git clone https://github.com/thiraviyarajr2007-dotcom/LandslideNEI.git
cd LandslideNEI

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Launching the Services

#### Option A: Run the Desktop Workstation Application

Launches the embedded local API and opens the native Windows EOC Command Workstation:

```powershell
python desktop_app.py
```

To run a headless diagnostic health check:

```powershell
python desktop_app.py --check-health
```

#### Option B: Run the FastAPI Service & Dashboard Directly

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

- **EOC Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Public Website**: [http://127.0.0.1:8000/website/](http://127.0.0.1:8000/website/)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Option C: Optional Port 80 Redirector

If you want users on your local network to access the platform at `http://localhost/` or `http://127.0.0.1/` without specifying `:8000`:

```powershell
python scripts\port80_redirect.py
```

---

## Automated Test Suite

The repository contains 202 comprehensive unit and integration tests covering data extraction, inference physics, API contracts, dashboard UI, packaging integrity, and GitHub Pages integration:

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

All 202 tests pass with zero regressions.

---

## Standalone Windows Installer

The official Windows installer `LANDSLIDENEI_Setup_x64.exe` is hosted and verified on GitHub Releases:

- **Release Tag**: `v1.0.0`
- **Direct Download**: [Download LANDSLIDENEI_Setup_x64.exe](https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/download/v1.0.0/LANDSLIDENEI_Setup_x64.exe)
- **Binary Size**: 73.8 MB (73,851,100 bytes)
- **SHA-256 Hash**: `bc7a6adceb87bbd2674c98e76f2e834f02ae848125fc9319b3f75c992970aaaf`

To rebuild the installer from source:

```powershell
# 1. Compile PyInstaller distribution
python scripts\build_desktop_app.py

# 2. Package into self-extracting 7-Zip installer
.\scripts\build_windows_installer.ps1
```

---

## API Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System readiness, loaded model checkpoint, and telemetry provider status |
| `POST` | `/api/v1/profile/static` | Extracts 30m DEM terrain morphometry and static susceptibility score |
| `POST` | `/api/v1/predict/risk` | Full geotechnical risk fusion (DEM + SoilGrids + CWC + Mohr-Coulomb) |
| `GET` | `/api/v1/stations/rainfall` | Live spatial CWC telemetry station registry across Northeast India |
| `GET` | `/download/windows` | Download endpoint resolving official desktop installer |
| `GET` | `/dashboard/` | Interactive Leaflet GIS EOC Command Workstation |
| `GET` | `/website/` | Public dissemination website |

---

## Scientific Transparency & Disclaimers

1. **Susceptibility Score vs. Empirical Probability**: Static susceptibility scores are normalized terrain vulnerability indices $[0.0, 1.0]$ derived from statistical machine learning. They represent spatial susceptibility ordering, not an empirical probability of instantaneous slope failure.
2. **Operational Decision Support**: The system is designed to provide actionable early-warning alerts for civil defense and disaster response personnel. Evacuation decisions should incorporate field geotechnical surveys and local civil authority directives.

---

## License

This project is licensed under the [MIT License](LICENSE).
