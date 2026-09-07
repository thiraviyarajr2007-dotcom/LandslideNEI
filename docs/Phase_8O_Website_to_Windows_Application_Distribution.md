# Phase 8O: Public Website & Standalone Windows Application Architecture Specification
===================================================================================================

This document provides the authoritative technical architecture, separation boundaries, installation pipeline, and runtime specifications for **LANDSLIDENEI Phase 8O**.

---

## 1. Executive Summary & Separation of Concerns

LANDSLIDENEI separates public dissemination from operational mission-critical command into two distinct products:

```
                                  LANDSLIDENEI PLATFORM
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
             PUBLIC WEBSITE                              WINDOWS DESKTOP SOFTWARE
                    │                                               │
       Marketing & Dissemination                     Tactical EOC Command Workstation
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
                                LANDSLIDENEI_Setup_x64.exe
```

### Architectural Guarantees:
1. **Zero UI Leaks**: The website never embeds the desktop application inside an iframe or web view; the desktop software never redirects to the marketing site.
2. **True Standalone Distribution**: Clicking "Download for Windows" on the public website directly initiates the download of the 73.8 MB executable installer `LANDSLIDENEI_Setup_x64.exe`.
3. **Dedicated Operational Flow**: The desktop software follows a strict multi-tier operational flow:
   `First Launch / Setup Check` $\rightarrow$ `Duty Officer Login / Register` $\rightarrow$ `Home / EOC Dashboard` $\rightarrow$ `Location Analysis` $\rightarrow$ `Risk Map` $\rightarrow$ `Rainfall Telemetry` $\rightarrow$ `Alerts` $\rightarrow$ `Reports` $\rightarrow$ `Settings`.
4. **Real Machine Learning Inference**: Both products use the verified scikit-learn Random Forest model (`model/static_lsm_pipeline.joblib`) and physics engines (Saxton-Rawls pore-water pressure, Doppler weather radar reflectivity, and anthropogenic slope cuts). No fake data or fabricated percentage chances.

---

## 2. Public Website Architecture (`website/`)

* **Purpose**: Public product landing, capabilities showcase, scientific methodology transparency, and secure distribution channel for the Windows desktop software.
* **Theme Source**: `theme/website_theme.zip` (Dark Glass Tactical Dissemination).
* **Language**: English only (strict single-language standard).
* **Light Mode**: Disabled (high-contrast dark theme only).
* **Hosted URL**: `https://thiraviyarajr2007-dotcom.github.io/LandslideNEI/`

### Content Sections:
1. **Header & Navigation**: Brand typography, section jump links (Product Overview, How It Works, Technology, Dashboard Showcase, About), and primary `Download for Windows` CTA.
2. **Hero Section**: Regional mission overview ("AI-Powered Landslide Intelligence for Northeast India"), live telemetry sync indicators, and direct download trigger.
3. **How It Works**: 4-stage physics pipeline (Copernicus DEM $\rightarrow$ Soil Hydrology $\rightarrow$ IMD Radar $\rightarrow$ Risk Matrix).
4. **Technology & Multi-Source Data**: Copernicus 30m DEM, SoilGrids 250m, ESA WorldCover 10m, CWC river gauging telemetry, Open-Meteo regional re-fetch.
5. **Operational Dashboard Showcase**: High-fidelity tactical screenshot preview of the desktop software interface.
6. **Scientific Transparency & Limitations**: Explicit disclosures separating static susceptibility from dynamic hazard.
7. **Windows Desktop Download Section**: Technical specs bar (Windows 10/11 x64, DirectX 11+, Offline GIS cache supported) and primary download button.
8. **Footer**: Operational coverage across all 8 Northeast Indian states, datum standards (WGS84), and copyright.

---

## 3. Windows Desktop Application Architecture (`dashboard/` + `desktop_app.py`)

* **Purpose**: Dedicated local Emergency Operations Center (EOC) Command Workstation for control room duty officers and disaster response agencies (NDRF, SDMA, CWC).
* **Theme Source**: `theme/software_theme.zip` (Obsidian Dark Glass with Cyan/Amber/Red tactical status indicators).
* **Runtime**: Embedded Python runtime + FastAPI backend on localhost + Microsoft Edge `--app` container.

### Software Lifecycle Flow:
```
                               +----------------------------+
                               |     First Application      |
                               |          Launch            |
                               +--------------+-------------+
                                              |
                                              v
                               +----------------------------+
                               |   System Readiness Check   |
                               |    (Offline GIS, Engine)   |
                               +--------------+-------------+
                                              |
                                              v
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
        +-------------------------+                       +-------------------------+
        |   Duty Officer Login    |<--------------------->|  Register Duty Officer  |
        |   (ID, PIN, Sector)     |                       |  (Name, Agency, Sector) |
        +------------+------------+                       +-------------------------+
                     |
                     v
        +-------------------------+
        |   Home / EOC Overview   |
        |   (Regional GIS Map)    |
        +------------+------------+
                     |
     +---------------+---------------+---------------+---------------+
     |               |               |               |               |
     v               v               v               v               v
+----------+   +-----------+   +-----------+   +----------+   +------------+
| Location |   | Risk Map  |   | Rainfall  |   | Alerts   |   | Reports &  |
| Analysis |   | (8 States)|   | Telemetry |   | Stream   |   | Settings   |
+----------+   +-----------+   +-----------+   +----------+   +------------+
```

### Authentication & Session Management:
* **Session Storage**: Saved in `localStorage.setItem('landslidenei_auth_session', ...)` with encrypted officer identity, agency, and sector command.
* **Workstation Lock**: Clicking `Logout` in the header immediately locks the workstation, displays a toast notification, and prompts for credentials.

---

## 4. Installer Architecture (`installer/LANDSLIDENEI_Setup_x64.exe`)

* **Format**: Standalone 7-Zip LZMA2 ultra-compressed self-extracting archive with Windows shortcut hooks (`Create_Desktop_Shortcut.vbs`).
* **Binary Size**: `73,851,100 bytes` (~73.8 MB).
* **SHA-256 Hash**: `bc7a6adceb87bbd2674c98e76f2e834f02ae848125fc9319b3f75c992970aaaf`.
* **Zero External Dependencies**:
  * Python runtime bundled.
  * Required dependencies pre-compiled.
  * Random Forest LSM model (`model/static_lsm_pipeline.joblib`) bundled.
  * Regional geojson boundaries (`gadm41_IND_1.json`) bundled.
  * GIS dashboard assets bundled.
* **Installation Targets**:
  * Extracts to user-selected directory or `%LOCALAPPDATA%\LandslideNEI`.
  * Creates Start Menu shortcut: `Programs\LANDSLIDENEI.lnk`.
  * Creates Desktop shortcut: `Desktop\LANDSLIDENEI.lnk`.

---

## 5. GitHub Release Asset Distribution

* **Official Repository**: `thiraviyarajr2007-dotcom/LandslideNEI`
* **Release Tag**: `v1.0.0`
* **Release Asset Name**: `LANDSLIDENEI_Setup_x64.exe`
* **Expected Release Asset URL**:
  ```
  https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/download/v1.0.0/LANDSLIDENEI_Setup_x64.exe
  ```
* **Local / Self-Hosted Resolution**:
  The website's `downloadReleasePackage()` in `website/js/app.js` dynamically checks environment:
  1. If running on `localhost` or local server: streams binary directly from `/download/installer`.
  2. If running offline file protocol (`file:///`): accesses adjacent `downloads/LANDSLIDENEI_Setup_x64.exe`.
  3. If hosted on `github.io`: directs to the authoritative GitHub Release binary.

---

## 6. Real Machine Learning Inference & Geotechnical Processing

When a duty officer selects any coordinate in the desktop software:
1. **Coordinate Validation**: Checks geographic bounding box for Northeast India ($21.5^\circ\text{N} - 29.5^\circ\text{N}, 89.5^\circ\text{E} - 97.5^\circ\text{E}$).
2. **Copernicus DEM 30m Query**: Extracts surface elevation, slope gradient, planform curvature, profile curvature, and topographic wetness index ($TWI$).
3. **SoilGrids & Saxton-Rawls**: Evaluates clay, sand, silt fraction, bulk density, saturated hydraulic conductivity ($K_{sat}$), and effective cohesion.
4. **Meteorological Telemetry**: Retrieves live CWC river gauge rainfall ($P_{1h}, P_{24h}, P_{7d}$); automatically executes Open-Meteo re-fetch for remote uninstrumented catchments.
5. **Transient Pore-Water Pressure ($u$)**: Calculates positive pore pressure buildup under continuous rainfall saturation.
6. **Limit Equilibrium Factor of Safety ($FoS$)**: Evaluates Mohr-Coulomb shear strength vs driving shear stress.
7. **Random Forest LSM**: Generates uncalibrated static terrain susceptibility score.
8. **Deterministic Risk Fusion**: Fuses static susceptibility tier with dynamic rainfall trigger level into authoritative operational decision (`LOW`, `WATCH`, `HIGH`, `CRITICAL`).

### Scientific Score Display Standards:
* **Never use**: "88% probability of landslide" or "chance of landslide".
* **Always use**:
  ```
  Operational Fusion Score : 0.742
  Static Susceptibility    : 0.685 (HIGH)
  Factor of Safety (FoS)   : 1.12
  ```
* **Authoritative Disclaimer**:
  `"Engineering synthesis score used for ordering and visualization; not an empirical probability of slope failure."`

---

## 7. Verification & Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| Clicking "Download" does nothing | Browser popup/download blocker active | Use the direct fallback link in the download modal dialog |
| Port 8000 already in use | Previous instance still running | The application dynamically allocates the next free port (8001-8050) |
| Missing model error box | Corrupted extraction | Re-run `LANDSLIDENEI_Setup_x64.exe` to restore `model/` folder |
| Telemetry shows null | Catchment >50 km from river station | Automatic secondary Open-Meteo re-fetch engages transparently |
