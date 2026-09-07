# LandslideNEI Sentinel Monitor - Chrome & Edge Browser Extension (Manifest V3)

Run the **LandslideNEI Emergency Operations Center (EOC)** directly inside your web browser toolbar and side panel.

---

## Features
- **Instant Toolbar Risk Badge**: Displays current hazard level (`LOW`, `WATCH`, `HIGH`, `CRIT`) with live color coding (Green, Amber, Orange, Red).
- **Tactical Sentinel Popup**:
  - Strategic mountain corridor selector (Kohima NH-29, Gangtok NH-10, Cherrapunji, Tawang Pass, Aizawl Ridge, Guwahati Foothills).
  - Custom coordinates evaluator with GPS location support.
  - Live 4-Pillar telemetry cards:
    1. **Precipitation**: 24h rainfall & Doppler Radar reflectivity ($Z\text{ dBZ}$)
    2. **Soil Mechanics**: Factor of Safety ($FoS$), positive pore water pressure ($u\text{ kPa}$), and saturation %
    3. **Micro-Topography**: Horn slope gradient, plan/profile curvature, and Topographic Wetness Index (TWI)
    4. **Anthropogenic Factors**: Road toe cut severity, drainage blockage hydrostatic surcharge, and retaining wall status
- **Docked Side Panel**: Run the full interactive GIS dashboard in Chrome's side panel while monitoring weather models or browsing satellite feeds.
- **Offline Resilience**: Automatically falls back to high-fidelity demo telemetry if the local backend server is offline.

---

## Quick Installation Instructions (Load Unpacked)

### Google Chrome / Chromium / Brave / Opera:
1. Open your browser and navigate to:
   ```text
   chrome://extensions
   ```
2. Toggle **Developer mode** to **ON** (toggle located in the top-right corner).
3. Click the **Load unpacked** button (top-left).
4. Browse to and select the `c:\SIH Landslide\extension` folder.
5. Click the **Puzzle Piece (Extensions)** icon in your browser toolbar and pin **LandslideNEI Sentinel Monitor**.
6. Click the green LandslideNEI badge to open your operational monitor!

### Microsoft Edge:
1. Open Edge and navigate to:
   ```text
   edge://extensions
   ```
2. Turn on **Developer mode** in the left sidebar.
3. Click **Load unpacked** and select the `extension` folder.

---

## Standalone Distribution (.zip)
To build a standalone zip archive ready for distribution or the Chrome Web Store:
```bash
python scripts/package_extension.py
```
This packages everything into `dist/LandslideNEI_Chrome_Extension_v1.0.0.zip`.
