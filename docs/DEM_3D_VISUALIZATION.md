# LANDSLIDENEI — 3D DEM Terrain Visualization Module

## Technical Specification & Operational Architecture Report

```
================================================================================
PROJECT:       LANDSLIDENEI
SUBSYSTEM:     3D Digital Elevation Model (DEM) Terrain Visualization Module
ENGINE:        Native Sovereign WebGL (Three.js r128 + OrbitControls)
AUTHORITY:     Copernicus GLO-30 DSM (30m, EPSG:4326)
DATE:          September 2026
STATUS:        Production Operational (Phase 8P)
================================================================================
```

---

## 1. Executive Summary

The **3D DEM Terrain Visualization Module** provides Emergency Operations Center (EOC) commanders, geotechnical engineers, and disaster managers with a native, high-fidelity 3D spatial interface for inspecting slope, aspect, relief, and operational landslide risk across Northeast India (NER).

Built on strict principles of scientific integrity, the module guarantees:
1. **Real Terrain Only:** All elevation geometry is derived directly from authoritative Copernicus GLO-30 rasters.
2. **Zero Synthetic Fabrication:** When coordinates fall outside DEM coverage or on missing tiles, the system strictly displays `TERRAIN DATA UNAVAILABLE`. It **never** fabricates elevation, synthetic contours, fake landslides, or imaginary villages.
3. **100% Offline & Sovereign:** Completely self-contained within the Windows standalone workstation (`LANDSLIDENEI.exe`). Zero external cloud dependencies, zero external tileservers, zero API tokens required.
4. **Seamless 2D/3D Synchronization:** Operators can instantly switch between `[ 2D MAP ]` and `[ 3D TERRAIN ]` views without losing active coordinates, telemetry feeds, or operational risk synthesis evaluations.

---

## 2. Authoritative DEM Source & Spatial Parameters

| Parameter | Specification | Verification Details |
| :--- | :--- | :--- |
| **Data Product** | Copernicus DEM GLO-30 Public | COP-DEM_GLO-30-DGED (AWS Open Data / ESA) |
| **Product Type** | Digital Surface Model (DSM) | Captures canopy/ground reflective surface |
| **Spatial Reference System (CRS)** | **EPSG:4326** (WGS 84 Geographic 2D) | Ellipsoidal WGS84 coordinates (Latitude, Longitude) |
| **Horizontal Resolution** | **1.0 arc-second** (~30 meters at equator) | Cell spacing: `0.0002777777777777778°` |
| **Vertical Units** | Metric Meters above EGM2008 Geoid | Elevation range verified from ~19m to 8,564m |
| **Tile Structure** | 1° × 1° Cloud-Optimized GeoTIFFs (COGs) | 3600 × 3600 pixels per tile |
| **Geographic Coverage** | Bounding Box: `[88.0° E, 21.0° N]` to `[98.0° E, 30.0° N]` | 41 tiles covering all 8 Northeast India states |
| **Nodata Handling** | Explicit NaN / Mask handling | Nodata never replaced with synthetic filler |

---

## 3. 3D WebGL Engine Evaluation & Architectural Decision

### 3.1 Evaluation of CesiumJS
Per the project mandate, CesiumJS was comprehensively audited for feasibility:
- **Cloud Dependency:** Standard Cesium World Terrain requires an active internet connection and Cesium Ion access tokens, directly violating sovereign offline EOC operational requirements.
- **Offline Quantized-Mesh Overhead:** Serving offline terrain in CesiumJS requires pre-generating multi-level quantized-mesh pyramids (`.terrain` tiles with oct-encoded normals and index buffers) using external C++ toolchains (`ctb-tile`), requiring gigabytes of storage for multi-scale pyramids.
- **Installer Footprint Bloat:** The full CesiumJS build (`Cesium.js`, workers, assets, widgets, third-party libraries) adds ~45 MB to the application bundle, conflicting with desktop workstation size constraints.

### 3.2 Selected Engine: Native Three.js Sovereign WebGL
A specialized WebGL terrain engine was implemented using a locally vendored build of **Three.js (r128)** and **OrbitControls**:
- **Bundle Footprint:** ~615 KB total (`three.min.js` + `OrbitControls.js`), vendored directly inside `dashboard/assets/vendor/`.
- **100% Offline Integrity:** Zero external HTTP requests, zero cloud tokens, 100% functional on isolated military/disaster management networks.
- **Direct Raster Streaming:** The FastAPI backend serves real Copernicus GLO-30 elevation grids directly to the WebGL canvas, allowing instantaneous sub-100ms loading.
- **High Performance:** Smooth 60 FPS rendering on standard Windows EOC workstations (Intel UHD Graphics / dedicated GPUs) with 16,384 vertices per corridor.

---

## 4. DEM Optimization & Offline Packaging Strategy

Bundling all 41 raw Copernicus GLO-30 GeoTIFFs (~1.8 GB) directly into the standalone Windows installer would cause massive packaging bloat, slow installation, and high memory usage.

### 4.1 Chosen Dual-Layer Representation

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LANDSLIDENEI 3D ARCHITECTURE                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   [LAYER 1: Standalone Offline Bundled Corridors]                      │
│   Preprocessed 128×128 GLO-30 Elevation, Horn's Slope & Aspect Grids    │
│   Location: data/processed/dem/terrain_cache/ (<1 MB total)           │
│   Corridors: Kohima NH-29, Gangtok NH-10, Cherrapunji, Tawang, etc.    │
│                                                                        │
│   [LAYER 2: Dynamic Sovereign Workstation Mode]                        │
│   On-the-fly rasterio window extraction across 41 COG GeoTIFFs         │
│   Location: data/raw/dem/copernicus_glo30/downloads/ (1.8 GB)         │
│   Allows dynamic 3D inspection anywhere in Northeast India             │
│                                                                        │
│   [OUT-OF-BOUNDS / MISSING ASSET FALLBACK]                             │
│   Strictly returns: TERRAIN DATA UNAVAILABLE                           │
│   Synthetic elevation generation is strictly prohibited.               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Authoritative Strategic Focal Corridors (16 Hubs)

The system packages 16 authoritative strategic focal corridors covering **all 8 Northeast India states** and the West Bengal border corridor:

| Corridor ID | Name | Sector | State | Center (Lat, Lon) | Elev Range (m) | Cache Size (GZ) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `corridor_nagaland_kohima` | Kohima & Zubza Axis (NH-29) | `nagaland` | Nagaland | 25.6740° N, 94.1120° E | 569m – 2,984m | 97.7 KB |
| `corridor_nagaland_mokokchung` | Mokokchung Ridge Corridor | `mokokchung` | Nagaland | 26.3256° N, 94.5165° E | 408m – 1,677m | 96.3 KB |
| `corridor_sikkim_gangtok` | Gangtok NH-10 Teesta Gorge | `sikkim` | Sikkim | 27.3389° N, 88.6065° E | 493m – 3,777m | 100.1 KB |
| `corridor_sikkim_namchi` | Namchi & South Sikkim Spur | `namchi` | Sikkim | 27.1667° N, 88.3500° E | 225m – 2,622m | 98.7 KB |
| `corridor_meghalaya_cherrapunji` | Cherrapunji-Shella Escarpment | `cherrapunji` | Meghalaya | 25.2702° N, 91.7323° E | 19m – 1,729m | 97.2 KB |
| `corridor_meghalaya_shillong` | Shillong Peak & Urban Axis | `shillong` | Meghalaya | 25.5788° N, 91.8933° E | 851m – 1,947m | 93.3 KB |
| `corridor_arunachal_tawang` | Bhalukpong-Tawang Spur | `tawang` | Arunachal Pradesh | 27.5861° N, 91.8594° E | 1,245m – 4,588m | 100.5 KB |
| `corridor_arunachal_itanagar` | Itanagar Capital Foothills | `itanagar` | Arunachal Pradesh | 27.0844° N, 93.6053° E | 111m – 2,343m | 95.2 KB |
| `corridor_mizoram_aizawl` | Aizawl Ridge | `aizawl` | Mizoram | 23.7271° N, 92.7176° E | 67m – 1,337m | 96.7 KB |
| `corridor_mizoram_lunglei` | Lunglei Southern Ridge | `lunglei` | Mizoram | 22.8872° N, 92.7388° E | 77m – 1,521m | 96.5 KB |
| `corridor_assam_guwahati` | Guwahati Urban Foothills | `guwahati` | Assam | 26.1445° N, 91.7362° E | 42m – 449m | 78.3 KB |
| `corridor_assam_silchar` | Silchar & Cachar (Barak Valley)| `silchar` | Assam | 24.8333° N, 92.7789° E | 24m – 472m | 73.3 KB |
| `corridor_assam_tezpur` | Tezpur & Sonitpur Corridor | `tezpur` | Assam | 26.6338° N, 92.7926° E | 58m – 114m | 59.0 KB |
| `corridor_manipur_imphal` | Imphal Valley & Kangpokpi Axis | `imphal` | Manipur | 24.8170° N, 93.9368° E | 770m – 1,089m | 72.2 KB |
| `corridor_tripura_agartala` | Agartala & Baramura Range | `agartala` | Tripura | 23.8315° N, 91.2868° E | 0.5m – 68m | 73.5 KB |
| `corridor_westbengal_kalimpong` | Kalimpong-Teesta Confluence | `kalimpong` | West Bengal | 27.0667° N, 88.4667° E | 230m – 2,146m | 98.2 KB |

Total focal corridors cache: **1.39 MB** (compressed GZ).
Total 41 regional base tiles cache: **3.59 MB** (compressed GZ).
Total offline terrain cache: **4.98 MB (5,103.4 KB)**.
For complete architectural details, see [DEM_3D_COVERAGE_ARCHITECTURE.md](DEM_3D_COVERAGE_ARCHITECTURE.md).

---

## 5. 3D Camera & Visual Terrain Exaggeration Controls

### 5.1 Camera Controls
- **Zoom In / Zoom Out:** Smooth exponential scale adjustment along optical camera vector.
- **Top View (Nadir):** Sets camera directly overhead pointing down (`[0, 1, dist]`), providing a planimetric map perspective with true 3D relief shading.
- **Perspective View:** Sets tactical oblique 45° angle with 30° heading for optimal 3D ridge and valley comprehension.
- **Orbit Pan & Tilt:** Left-click drag rotates around target; Right-click drag pans along terrain tangent plane; Mouse wheel zooms.
- **Reset:** Instantly re-centers camera framing on the active corridor.

### 5.2 Visual Terrain Exaggeration
- Supported Multipliers: `1.0x`, `1.5x`, `2.0x`, `3.0x`.
- **Prominent Labeling:** Clearly marked as `VISUAL TERRAIN EXAGGERATION (NON-PHYSICAL)`.
- **Sub-caption:** *"Non-physical geometric scaling for topographic relief. Actual elevation values unchanged."*
- **Mathematical Implementation:** Scales vertex $Z = (Z_{\text{raw}} - Z_{\text{mean}}) \times \text{factor}$, followed by vertex normal recomputation for lighting fidelity.

---

## 6. Real-Time Terrain Inspection HUD & Location Profile

### 6.1 Hover Inspection HUD
When the operator moves the cursor across the 3D surface, a high-frequency raycaster samples the intersected mesh and displays:
- `LATITUDE:` Decimal degrees (e.g. `25.6740° N`)
- `LONGITUDE:` Decimal degrees (e.g. `94.1120° E`)
- `ELEVATION:` Genuine Copernicus DEM elevation (e.g. `1,428 m`)
- `SLOPE:` Metric Horn's slope in degrees (e.g. `32.4°`)
- `ASPECT:` Cardinal compass azimuth (e.g. `215° (SW)`)

If cursor is outside DEM coverage:
- `SLOPE: UNAVAILABLE`
- `ASPECT: UNAVAILABLE`

### 6.2 Location Profile Card & Synchronous Risk Synthesis
Clicking any point on the 3D surface:
1. Places an illuminated 3D query marker at that exact coordinate and elevation.
2. Displays the **Location Profile Card** with coordinates, elevation, slope, aspect, data source, and observation timestamp.
3. Automatically triggers `window.handleMapClick(lat, lon)` which synchronizes the 2D Leaflet marker and invokes `/api/v1/predict` and `/api/v1/profile` on the backend, updating the right-hand operational risk synthesis panel synchronously.

---

## 7. 3D Layer Architecture & Truth-in-Data Enforcement

| Layer Name | Status | Authoritative Data Source | Visual Representation |
| :--- | :--- | :--- | :--- |
| **Terrain Surface** | **AVAILABLE** | Copernicus GLO-30 (30m, EPSG:4326) | Natural earthen relief hillshade |
| **Elevation** | **AVAILABLE** | Hypsometric DEM gradient | Cyan-to-rose hypsometric color ramp |
| **Slope Gradient** | **AVAILABLE** | Horn's 3x3 formula ($0^\circ$ to $90^\circ$) | Green (<15°) $\to$ Yellow $\to$ Orange $\to$ Crimson (>35°) |
| **Aspect Direction** | **AVAILABLE** | Maximum slope azimuth ($0^\circ$ to $360^\circ$) | Compass wheel: North (Blue), East (Amber), South (Red), West (Green) |
| **Historical Landslides** | **CONNECTED** | NESAC/NERDRR SLI 2021 (75 Verified Events) | 3D tactical cones; hover displays ID, date, fatalities |
| **Rainfall Stations** | **AVAILABLE** | Central Water Commission (CWC, 55 Stations) | 3D cyan sensor cylinders with station names |
| **Rainfall Intensity** | **AVAILABLE** | CWC Telemetry / Open-Meteo GFS-HRRR | Dynamic meteorological precipitation surface halo |
| **Risk Zones** | **AVAILABLE** | LANDSLIDENEI Risk Fusion Engine | Synthesized risk tier rings (LOW, WATCH, HIGH, CRITICAL) |
| **Villages & Settlements** | **DATA UNAVAILABLE** | Pending sovereign village integration | **Disabled / Unchecked; displays `DATA UNAVAILABLE`** |

> [!CAUTION]
> **Strict Operational Rule:**
> No synthetic villages, fake landslide points, or fabricated hazard polygons are rendered. If data is not yet integrated, the system explicitly reports `DATA UNAVAILABLE`.

---

## 8. 2D Map & 3D Terrain View Switching

Switching between `[ 2D MAP ]` and `[ 3D TERRAIN ]` is handled by `switchMapView(mode)`:
- Preserves `window.currentCoordinates` without reset.
- Preserves `window.lastPredictionData` and current operational verdict banner.
- Preserves active corridor preset selection.
- In 2D mode, calls `mapInstance.invalidateSize()` to redraw Leaflet tiles seamlessly.
- In 3D mode, calls `Terrain3D.onWindowResize()` to frame the WebGL canvas correctly.

---

## 9. Future Village Dataset Integration Roadmap

When the verified sovereign village registry dataset is integrated in a subsequent phase:
1. Ingest village records containing official LGD (Local Government Directory) codes, census population, and surveyed boundaries.
2. Expose `/api/v1/layers/villages` with authentic settlement locations.
3. Update `layers_status` endpoint to transition `villages` from `DATA UNAVAILABLE` to `CONNECTED`.
4. Render settlements as 3D civilian habitation pins with population exposure tooltips.
