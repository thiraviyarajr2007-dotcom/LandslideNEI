# Phase 8J — Operational Dashboard & GIS Risk Visualization

**Project**: SIH Landslide AI Early-Warning & Decision-Support System  
**Repository**: `thiraviyarajr2007-dotcom/LandslideNEI`  
**Base Checkpoint**: `cf84a8f` (`feat: add unified risk API contract`)  
**Route**: `/dashboard/` (or `/` via browser)

---

## 1. Overview & Architecture

Phase 8J implements an interactive Emergency Operations Center (EOC) Command Dashboard that transforms the backend risk models into an intuitive, map-first operational interface.

```
CLIENT BROWSER (Single-Page Application)
   │
   ├─► GIS Map: Leaflet.js (CartoDB Dark Matter / OpenStreetMap / OpenTopoMap)
   │     • 8 Northeast India States vector boundaries (GeoJSON)
   │     • 73 CWC Telemetry Stations layer with metadata popups
   │     • Interactive click-to-query pin with risk-colored radar pulse
   │     • 50 km CWC station range ring
   │
   ├─► SIH Demo Presets Bar:
   │     • 6 one-click scenarios (Guwahati, Tawang, Mangan, Cherrapunji, Aizawl, Delhi)
   │
   ├─► Operational Decision Panel:
   │     • Authoritative Risk Verdict (LOW / WATCH / HIGH / CRITICAL)
   │     • Operational Fusion Score gauge with non-probabilistic disclaimer
   │     • Static Susceptibility (Phase 8F Model A) & uncalibrated disclaimer
   │     • Dynamic Rainfall Telemetry (1h, 24h, 3d, 7d) & freshness badges
   │     • IMD Macro Administrative Context block
   │     • Physical Environmental Features (DEM terrain, SoilGrids, WorldCover LULC)
   │     • Explainability reason codes ("Why this risk?")
   │
   └─► Bilingual Localization (i18n):
         • Instant toggle between English (EN) and Tamil (தமிழ்)
```

The frontend does not duplicate any machine learning or risk fusion math. All predictions are fetched asynchronously via `fetch('/api/v1/predict')` and `fetch('/api/v1/profile')`.

---

## 2. Interactive GIS Map Features

1. **8 Northeast Indian States Coverage**:
   - High-resolution vector polygon boundaries extracted from GADM data (`Arunachal Pradesh`, `Assam`, `Manipur`, `Meghalaya`, `Mizoram`, `Nagaland`, `Sikkim`, `Tripura`).
   - Interactive hover highlights with domain boundary tooltips.
2. **73 CWC Telemetry Stations**:
   - Placed across the 8 NER states with radar markers.
   - Clicking any station displays its name, state, exact coordinates, and altitude.
3. **Pulsing Query Marker & 50 km Buffer**:
   - When a location is queried, a dynamic pulsing radar ring is placed at the coordinates.
   - The ring color corresponds directly to the authoritative risk level:
     - 🟢 **LOW**: Emerald Green (`#22c55e`)
     - 🟡 **WATCH**: Amber Yellow (`#eab308`)
     - 🟠 **HIGH**: Vivid Orange (`#f97316`)
     - 🔴 **CRITICAL**: Crimson Red (`#ef4444`)
   - A dashed 50 km radius ring visually illustrates the CWC station proximity cap.

---

## 3. SIH Demonstration Presets

The dashboard includes 6 predefined scenarios for live judging and technical presentations:

| Preset Name | Coordinates | Static Predisposition | Telemetry Context | Authoritative Risk | Scenario Narrative |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Guwahati Urban** | `26.1445°N, 91.7362°E` | `LOW (0.0467)` | CWC station 4.2 km away | **`LOW`** | Gentle Brahmaputra valley floor, low gravitational shear stress. |
| **Tawang Alpine** | `27.5925°N, 91.6087°E` | `HIGH (0.6842)` | No CWC within 50 km (`NO_DATA`) | **`WATCH`** | Steep Himalayan terrain (>30° slope); triggers precautionary WATCH due to lack of local telemetry. |
| **Mangan / Chungthang** | `27.5028°N, 88.5284°E` | `HIGH (0.7105)` | Teesta valley | **`HIGH`** | High local relief (>50m std), fragile geology, severe terrain hazard. |
| **Cherrapunji / Sohra** | `25.2986°N, 91.7317°E` | `MODERATE / HIGH` | Meghalaya escarpment | **`WATCH`** | World's wettest plateau edge; demonstrates orographic rainfall handling. |
| **Aizawl Ridge City** | `23.7271°N, 92.7176°E` | `HIGH (0.6120)` | Ridge-crest urban zone | **`HIGH`** | Densely built-up ridge with alternating shale/sandstone sequences. |
| **New Delhi (Domain Rejection)** | `28.6139°N, 77.2090°E` | Outside NER | N/A | **`REJECTED`** | Demonstrates domain enforcement; returns HTTP 400 with `OUTSIDE_SUPPORTED_DOMAIN` modal. |

---

## 4. Bilingual Support (English & Tamil)

The dashboard includes a zero-dependency internationalization module (`dashboard/js/i18n.js`):
- All UI labels, risk categories, metric titles, explainability headers, and disclaimers are translated.
- Switch between **English** and **தமிழ்** with a single click in the top header.
- Switching language updates the DOM dynamically without reloading the page or losing current evaluation data.

---

## 5. Running the Dashboard

To launch the dashboard locally:

```powershell
cd "C:\SIH Landslide"
.\venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open a web browser and navigate to:
- `http://127.0.0.1:8000/` (automatically redirects to the dashboard)
- or `http://127.0.0.1:8000/dashboard/`
