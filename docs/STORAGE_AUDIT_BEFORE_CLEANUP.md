# SIH Landslide — Safe Project Storage Audit (Before Cleanup)

**Audit Timestamp:** 2026-09-09
**Root Directory:** `C:\SIH Landslide`
**Audit Status:** `READ-ONLY COMPREHENSIVE AUDIT — NO FILES MODIFIED`

---

## Executive Summary

- **Total Storage Consumption:** **5.45 GB** (5,849,690,134 bytes)
- **Total Files:** **82,525**
- **Total Directories:** **5,306**
- **Git Repository Footprint (`.git`):** **647.56 MB** (679,020,439 bytes, 32,335 objects/files)
- **Virtual Environment (`venv`):** **1.25 GB** (1,340,958,476 bytes, 46,842 files)
- **Raw Copernicus DEM GeoTIFFs:** **1.73 GB** (1,853,221,330 bytes, 41 tiles)
- **Packaged Standalone Build (`dist/LANDSLIDENEI`):** **463.01 MB** (Verified Operational)
- **Intermediate Build Folder (`build/`):** **57.37 MB** (Regenerable)

---

## Section A: Total Project Size

| Metric | Value | Notes |
| :--- | :--- | :--- |
| **Physical Disk Size** | `5.45 GB` | 5,849,690,134 bytes |
| **Total File Count** | `82,525` | Across all folders |
| **Total Folder Count** | `5,306` | Directory nodes |
| **Active Drive C: Free Space** | `127.91 GB` | Drive C: has 347.55 GB used / 475.46 GB total |
| **Target Drive D: Availability** | `NOT FOUND` | Drive D: does not exist on this system |

---

## Section B: Size by Top-Level Directory

| Directory / Item | Size | Size (Bytes) | File Count | % of Total | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data` | **2.95 GB** | 3,170,613,906 | 280 | 54.20% | Datasets (raw Copernicus DEM, ESA WorldCover, OSM, soil, processed terrain cache) |
| `venv` | **1.25 GB** | 1,340,958,476 | 46,842 | 22.92% | Python 3.10.11 virtual environment (46k files, PyTorch/SciPy/GDAL) |
| `.git` | **647.56 MB** | 679,020,439 | 32,335 | 11.61% | Git VCS repository (includes 177MB pack garbage and historical blobs) |
| `dist` | **463.03 MB** | 485,517,211 | 2,620 | 8.30% | Standalone production distribution (LANDSLIDENEI.exe workstation) |
| `installer` | **70.43 MB** | 73,851,100 | 1 | 1.26% | Generated Inno Setup 64-bit installer executable |
| `build` | **57.37 MB** | 60,152,820 | 16 | 1.03% | PyInstaller intermediate compilation build tree |
| `scratch` | **22.74 MB** | 23,849,061 | 202 | 0.41% | Temporary OCR experiments, test scripts, and duplicated PDFs |
| `model` | **8.31 MB** | 8,717,543 | 6 | 0.15% | Static LSM Pipeline model artifacts (static_lsm_pipeline.joblib) |
| `theme` | **3.36 MB** | 3,523,561 | 2 | 0.06% | UI themes and styling ZIP archives |
| `dashboard` | **1.06 MB** | 1,109,499 | 11 | 0.02% | Web GIS workstation dashboard interface |
| `tests` | **701.19 KB** | 718,022 | 64 | 0.01% | Pytest operational and regression test suites |
| `scripts` | **641.93 KB** | 657,334 | 58 | 0.01% | Root configuration / metadata |
| `src` | **264.79 KB** | 271,146 | 22 | 0.00% | Core Python application and inference source code |
| `event_duplicate_review.csv` | **108.79 KB** | 111,406 | 1 | 0.00% | Root configuration / metadata |
| `CCM Optical.zip` | **87.28 KB** | 89,379 | 1 | 0.00% | Root configuration / metadata |
| `api` | **86.36 KB** | 88,428 | 4 | 0.00% | FastAPI backend REST endpoints and schemas |
| `docs` | **83.49 KB** | 85,491 | 7 | 0.00% | Technical documentation, architecture reports, and walkthroughs |
| `website` | **82.42 KB** | 84,395 | 6 | 0.00% | Landing page and public portal |
| `extension` | **43.05 KB** | 44,081 | 12 | 0.00% | Root configuration / metadata |
| `historical_landslide_events.csv` | **41.31 KB** | 42,305 | 1 | 0.00% | Root configuration / metadata |
| `candidate_control_periods.csv` | **38.61 KB** | 39,540 | 1 | 0.00% | Root configuration / metadata |
| `event_rainfall_windows.csv` | **24.05 KB** | 24,626 | 1 | 0.00% | Root configuration / metadata |
| `desktop_app.py` | **22.70 KB** | 23,244 | 1 | 0.00% | Root configuration / metadata |
| `.pytest_cache` | **17.36 KB** | 17,778 | 6 | 0.00% | Root configuration / metadata |
| `event_rainfall_alignment.csv` | **14.46 KB** | 14,811 | 1 | 0.00% | Root configuration / metadata |
| `README.md` | **11.44 KB** | 11,712 | 1 | 0.00% | Root configuration / metadata |
| `source_register.csv` | **7.92 KB** | 8,109 | 1 | 0.00% | Root configuration / metadata |
| `HISTORICAL_LANDSLIDE_RAINFALL_QC.md` | **6.70 KB** | 6,863 | 1 | 0.00% | Root configuration / metadata |
| `__pycache__` | **6.35 KB** | 6,500 | 1 | 0.00% | Root configuration / metadata |
| `assets` | **5.43 KB** | 5,563 | 1 | 0.00% | Icons, logos, and UI imagery |
| `FULL_PROJECT_CODE.txt` | **4.85 KB** | 4,963 | 1 | 0.00% | Root configuration / metadata |
| `.idea` | **4.57 KB** | 4,683 | 6 | 0.00% | Root configuration / metadata |
| `.github` | **4.10 KB** | 4,202 | 2 | 0.00% | Root configuration / metadata |
| `LANDSLIDENEI.spec` | **3.13 KB** | 3,206 | 1 | 0.00% | Root configuration / metadata |
| `config` | **2.77 KB** | 2,837 | 2 | 0.00% | Runtime configuration files |
| `operational_workflow_report.txt` | **2.66 KB** | 2,726 | 1 | 0.00% | Root configuration / metadata |
| `LICENSE` | **1.07 KB** | 1,093 | 1 | 0.00% | Root configuration / metadata |
| `input` | **987 B** | 987 | 1 | 0.00% | Root configuration / metadata |
| `.gitignore` | **576 B** | 576 | 1 | 0.00% | Root configuration / metadata |
| `pytest.ini` | **184 B** | 184 | 1 | 0.00% | Root configuration / metadata |
| `output` | **181 B** | 181 | 1 | 0.00% | Root configuration / metadata |
| `requirements.txt` | **147 B** | 147 | 1 | 0.00% | Root configuration / metadata |

---

## Section C: Size by Second-Level Directory (Top 35)

| Directory Path | Size | File Count | Description |
| :--- | :--- | :--- | :--- |
| `data/raw` | **2.77 GB** | 103 | Second-level node |
| `venv/Lib` | **1.24 GB** | 46,792 | Second-level node |
| `.git/objects` | **647.48 MB** | 32,303 | Second-level node |
| `dist/LANDSLIDENEI` | **463.01 MB** | 2,619 | Second-level node |
| `data/processed` | **104.49 MB** | 142 | Second-level node |
| `data/inspection` | **78.23 MB** | 32 | Second-level node |
| `installer/LANDSLIDENEI_Setup_x64.exe` | **70.43 MB** | 1 | Second-level node |
| `build/LANDSLIDENEI` | **57.37 MB** | 16 | Second-level node |
| `scratch/SLI2021.pdf` | **10.67 MB** | 1 | Second-level node |
| `scratch/SLI2020.pdf` | **8.65 MB** | 1 | Second-level node |
| `model/landslide_model.pkl` | **5.36 MB** | 1 | Second-level node |
| `venv/Scripts` | **4.77 MB** | 47 | Second-level node |
| `model/static_lsm_pipeline.joblib` | **2.94 MB** | 1 | Second-level node |
| `scratch/sli2021_images` | **2.18 MB** | 75 | Second-level node |
| `theme/software_theme.zip` | **1.80 MB** | 1 | Second-level node |
| `theme/website_theme.zip` | **1.56 MB** | 1 | Second-level node |
| `scratch/all_cards_ocr.json` | **883.36 KB** | 1 | Second-level node |
| `dashboard/assets` | **831.94 KB** | 4 | Second-level node |
| `tests/__pycache__` | **544.51 KB** | 42 | Second-level node |
| `src/inference` | **264.79 KB** | 22 | Second-level node |
| `dashboard/js` | **125.15 KB** | 5 | Second-level node |
| `dashboard/index.html` | **111.73 KB** | 1 | Second-level node |
| `scripts/__pycache__` | **83.77 KB** | 9 | Second-level node |
| `website/index.html` | **68.62 KB** | 1 | Second-level node |
| `scratch/annexure_img_p57_x409.png` | **61.58 KB** | 1 | Second-level node |
| `scripts/build_historical_landslide_dataset.py` | **51.56 KB** | 1 | Second-level node |
| `data/landslide_atlas_inspection.json` | **46.42 KB** | 1 | Second-level node |
| `api/__pycache__` | **37.68 KB** | 2 | Second-level node |
| `.git/index` | **36.97 KB** | 1 | Second-level node |
| `scripts/train_static_lsm.py` | **36.78 KB** | 1 | Second-level node |
| `data/cwc_qc_report.json` | **34.14 KB** | 1 | Second-level node |
| `api/main.py` | **34.07 KB** | 1 | Second-level node |
| `scratch/img_292.png` | **33.52 KB** | 1 | Second-level node |
| `scratch/img_291.png` | **32.46 KB** | 1 | Second-level node |
| `scratch/img_293.png` | **30.46 KB** | 1 | Second-level node |

---

## Section D: Top 100 Largest Files

| Rank | File Path | Size | Category | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `venv/Lib/site-packages/torch/lib/torch_cpu.dll` | **290.95 MB** | Venv Binary | PyTorch CPU runtime (not bundled into EXE) |
| 2 | `.git/objects/pack/tmp_pack_zdkbHR` | **177.00 MB** | Git Garbage | Unfinished git pack garbage file (177 MB) |
| 3 | `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.shp` | **133.99 MB** | Raw Dataset | OpenStreetMap NEI road network shapefile |
| 4 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E087_Map.tif` | **112.02 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 5 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E090_Map.tif` | **94.25 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 6 | `.git/objects/32/720d956e125b8a271ba8411c72683402af885d` | **93.07 MB** | Git Blob | Git historical object |
| 7 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E096_Map.tif` | **91.67 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 8 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N21E093_Map.tif` | **90.07 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 9 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E087_Map.tif` | **84.72 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 10 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E090_Map.tif` | **80.91 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 11 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E093_Map.tif` | **75.40 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 12 | `installer/LANDSLIDENEI_Setup_x64.exe` | **70.43 MB** | Installer | Inno Setup compiled installer (Tracked by Git) |
| 13 | `.git/objects/a3/33a64226d5680ea43f21bd2b974bd1b431d615` | **70.35 MB** | Git Blob | Git historical object |
| 14 | `data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Processed Feature | Core operational CWC rainfall dataset |
| 15 | `dist/LANDSLIDENEI/_internal/data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Processed Feature | Core operational CWC rainfall dataset |
| 16 | `data/inspection/landslide_pdfs/Landslides_Atlas_of_India_Updated_25Aug2023.pdf` | **63.83 MB** | Reference PDF | ISRO Landslide Atlas of India document |
| 17 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N21E090_Map.tif` | **56.22 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 18 | `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.dbf` | **53.06 MB** | Raw Dataset | OpenStreetMap NEI road network shapefile |
| 19 | `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E093_Map.tif` | **52.87 MB** | Raw Dataset | 10m Landcover GeoTIFF tile |
| 20 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N23_00_E091_00_DEM.tif` | **50.13 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 21 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N24_00_E091_00_DEM.tif` | **49.28 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 22 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N24_00_E092_00_DEM.tif` | **49.05 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 23 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N21_00_E092_00_DEM.tif` | **48.31 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 24 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N22_00_E092_00_DEM.tif` | **47.54 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 25 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N23_00_E092_00_DEM.tif` | **47.39 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 26 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E090_00_DEM.tif` | **47.10 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 27 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E089_00_DEM.tif` | **45.14 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 28 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N23_00_E094_00_DEM.tif` | **44.93 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 29 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E089_00_DEM.tif` | **44.81 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 30 | `.git/objects/8f/67bb1ba2dc3b88d2b969c649beb646758aeca2` | **44.67 MB** | Git Blob | Git historical object |
| 31 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E091_00_DEM.tif` | **44.45 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 32 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E093_00_DEM.tif` | **44.28 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 33 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N24_00_E094_00_DEM.tif` | **43.83 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 34 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N24_00_E093_00_DEM.tif` | **43.64 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 35 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E092_00_DEM.tif` | **43.61 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 36 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E095_00_DEM.tif` | **43.48 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 37 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E094_00_DEM.tif` | **43.43 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 38 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E090_00_DEM.tif` | **43.37 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 39 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E091_00_DEM.tif` | **43.12 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 40 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N22_00_E093_00_DEM.tif` | **43.08 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 41 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N23_00_E093_00_DEM.tif` | **42.79 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 42 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E093_00_DEM.tif` | **42.53 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 43 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E096_00_DEM.tif` | **42.33 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 44 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E093_00_DEM.tif` | **42.30 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 45 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E097_00_DEM.tif` | **42.26 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 46 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif` | **42.21 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 47 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E094_00_DEM.tif` | **42.12 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 48 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E095_00_DEM.tif` | **41.78 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 49 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N26_00_E092_00_DEM.tif` | **41.72 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 50 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E095_00_DEM.tif` | **41.48 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 51 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E094_00_DEM.tif` | **41.34 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 52 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E092_00_DEM.tif` | **40.78 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 53 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E091_00_DEM.tif` | **40.38 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 54 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E096_00_DEM.tif` | **40.19 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 55 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N27_00_E088_00_DEM.tif` | **40.03 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 56 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N29_00_E095_00_DEM.tif` | **39.90 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 57 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E093_00_DEM.tif` | **39.89 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 58 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E097_00_DEM.tif` | **39.15 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 59 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N29_00_E094_00_DEM.tif` | **38.38 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 60 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N29_00_E096_00_DEM.tif` | **38.23 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 61 | `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N28_00_E092_00_DEM.tif` | **37.61 MB** | Raw DEM | Copernicus GLO-30 30m DEM GeoTIFF tile |
| 62 | `venv/Lib/site-packages/torch/lib/torch_cpu.lib` | **27.89 MB** | Venv File | Python environment package component |
| 63 | `venv/Lib/site-packages/pymupdf/mupdfcpp64.dll` | **25.08 MB** | Venv File | Python environment package component |
| 64 | `venv/Lib/site-packages/pyogrio.libs/gdal-9fa6a5301668010b1474299a888c26da.dll` | **20.91 MB** | Venv/Dist DLL | GDAL C++ dynamic library |
| 65 | `dist/LANDSLIDENEI/_internal/numpy.libs/libscipy_openblas64_-13e2df515630b4a41f92893938845698.dll` | **19.45 MB** | Venv/Dist DLL | SciPy OpenBLAS runtime binary |
| 66 | `venv/Lib/site-packages/numpy.libs/libscipy_openblas64_-13e2df515630b4a41f92893938845698.dll` | **19.45 MB** | Venv/Dist DLL | SciPy OpenBLAS runtime binary |
| 67 | `dist/LANDSLIDENEI/_internal/scipy.libs/libscipy_openblas-f07f5a5d207a3a47104dca54d6d0c86a.dll` | **19.22 MB** | Venv/Dist DLL | SciPy OpenBLAS runtime binary |
| 68 | `venv/Lib/site-packages/scipy.libs/libscipy_openblas-f07f5a5d207a3a47104dca54d6d0c86a.dll` | **19.22 MB** | Venv/Dist DLL | SciPy OpenBLAS runtime binary |
| 69 | `dist/LANDSLIDENEI/_internal/rasterio.libs/gdal-06c8a783fc258d4e4739c3a67902a55f.dll` | **18.78 MB** | Venv/Dist DLL | GDAL C++ dynamic library |
| 70 | `venv/Lib/site-packages/rasterio.libs/gdal-06c8a783fc258d4e4739c3a67902a55f.dll` | **18.78 MB** | Venv/Dist DLL | GDAL C++ dynamic library |
| 71 | `venv/Lib/site-packages/torch/lib/torch_python.dll` | **18.43 MB** | Venv File | Python environment package component |
| 72 | `data/raw/cwc_telemetry_hourly/2021_2025/rainfall_tel_hr_cwc_as_2021_2025.csv` | **18.28 MB** | Other |  |
| 73 | `data/raw/osm/geofabrik_nei/gis_osm_waterways_free_1.shp` | **16.93 MB** | Other |  |
| 74 | `data/raw/soil/silt_0-5cm_mean_nei.tif` | **16.89 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 75 | `dist/LANDSLIDENEI/_internal/data/raw/soil/silt_0-5cm_mean_nei.tif` | **16.89 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 76 | `build/LANDSLIDENEI/LANDSLIDENEI.exe` | **16.76 MB** | EXE Binary | PyInstaller standalone workstation binary |
| 77 | `dist/LANDSLIDENEI/LANDSLIDENEI.exe` | **16.76 MB** | EXE Binary | PyInstaller standalone workstation binary |
| 78 | `build/LANDSLIDENEI/LANDSLIDENEI.pkg` | **16.48 MB** | Other |  |
| 79 | `build/LANDSLIDENEI/PYZ-00.pyz` | **16.46 MB** | Other |  |
| 80 | `data/raw/soil/clay_0-5cm_mean_nei.tif` | **16.40 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 81 | `dist/LANDSLIDENEI/_internal/data/raw/soil/clay_0-5cm_mean_nei.tif` | **16.40 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 82 | `data/raw/soil/sand_0-5cm_mean_nei.tif` | **16.35 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 83 | `dist/LANDSLIDENEI/_internal/data/raw/soil/sand_0-5cm_mean_nei.tif` | **16.35 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 84 | `.git/objects/48/36fe40eae5fd2efebb84aae5a88d9567c54802` | **14.52 MB** | Git Blob | Git historical object |
| 85 | `data/raw/cwc_telemetry_hourly/1991_2020/rainfall_tel_hr_cwc_as_1991_2020.csv` | **14.41 MB** | Other |  |
| 86 | `venv/Lib/site-packages/pymupdf/_mupdf.pyd` | **12.46 MB** | Venv File | Python environment package component |
| 87 | `data/raw/historical_landslide_rainfall/sources/NESAC_SR_277_2022_SLI2021.pdf` | **10.67 MB** | Reference PDF | NESAC Landslide Inventory Report |
| 88 | `scratch/SLI2021.pdf` | **10.67 MB** | Reference PDF | NESAC Landslide Inventory Report |
| 89 | `data/inspection/landslide_pdfs/LandslideAtlas_new_2023.pdf` | **10.57 MB** | Other |  |
| 90 | `.git/objects/6c/7bcdf800117af261c51394da18c2a60f22aabf` | **9.79 MB** | Git Blob | Git historical object |
| 91 | `venv/Lib/site-packages/pyogrio/proj_data/proj.db` | **9.73 MB** | Venv File | Python environment package component |
| 92 | `data/raw/soil/bdod_0-5cm_mean_nei.tif` | **9.49 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 93 | `dist/LANDSLIDENEI/_internal/data/raw/soil/bdod_0-5cm_mean_nei.tif` | **9.49 MB** | Raw Dataset | SoilGrids 250m GeoTIFF layer |
| 94 | `venv/Lib/site-packages/hf_xet/hf_xet.pyd` | **9.06 MB** | Venv File | Python environment package component |
| 95 | `data/processed/rainfall/rainfall_daily_integrated.csv` | **8.99 MB** | Other |  |
| 96 | `dist/LANDSLIDENEI/_internal/data/processed/rainfall/rainfall_daily_integrated.csv` | **8.99 MB** | Dist File | Bundled standalone executable file |
| 97 | `dist/LANDSLIDENEI/_internal/rasterio/proj_data/proj.db` | **8.93 MB** | Dist File | Bundled standalone executable file |
| 98 | `venv/Lib/site-packages/rasterio/proj_data/proj.db` | **8.93 MB** | Venv File | Python environment package component |
| 99 | `dist/LANDSLIDENEI/_internal/pyproj/proj_dir/share/proj/proj.db` | **8.83 MB** | Dist File | Bundled standalone executable file |
| 100 | `venv/Lib/site-packages/pyproj/proj_dir/share/proj/proj.db` | **8.83 MB** | Venv File | Python environment package component |

---

## Section E: Top 50 Largest Directories

| Rank | Directory Path | Cumulative Size | File Count | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `data` | **2.95 GB** | 280 | Recursive tree size |
| 2 | `data/raw` | **2.77 GB** | 103 | Recursive tree size |
| 3 | `data/raw/dem/copernicus_glo30` | **1.73 GB** | 43 | Recursive tree size |
| 4 | `data/raw/dem` | **1.73 GB** | 43 | Recursive tree size |
| 5 | `data/raw/dem/copernicus_glo30/downloads` | **1.73 GB** | 41 | Recursive tree size |
| 6 | `venv` | **1.25 GB** | 46,842 | Recursive tree size |
| 7 | `venv/Lib/site-packages` | **1.24 GB** | 46,792 | Recursive tree size |
| 8 | `venv/Lib` | **1.24 GB** | 46,792 | Recursive tree size |
| 9 | `data/raw/worldcover/esa_worldcover_v200` | **738.13 MB** | 9 | Recursive tree size |
| 10 | `data/raw/worldcover` | **738.13 MB** | 9 | Recursive tree size |
| 11 | `.git` | **647.56 MB** | 32,335 | Recursive tree size |
| 12 | `.git/objects` | **647.48 MB** | 32,303 | Recursive tree size |
| 13 | `venv/Lib/site-packages/torch` | **472.28 MB** | 14,078 | Recursive tree size |
| 14 | `dist` | **463.03 MB** | 2,620 | Recursive tree size |
| 15 | `dist/LANDSLIDENEI` | **463.01 MB** | 2,619 | Recursive tree size |
| 16 | `dist/LANDSLIDENEI/_internal` | **446.25 MB** | 2,618 | Recursive tree size |
| 17 | `venv/Lib/site-packages/torch/lib` | **351.38 MB** | 23 | Recursive tree size |
| 18 | `data/raw/osm/geofabrik_nei` | **208.39 MB** | 10 | Recursive tree size |
| 19 | `data/raw/osm` | **208.39 MB** | 10 | Recursive tree size |
| 20 | `.git/objects/pack` | **177.03 MB** | 4 | Recursive tree size |
| 21 | `dist/LANDSLIDENEI/_internal/data` | **167.17 MB** | 150 | Recursive tree size |
| 22 | `venv/Lib/site-packages/scipy` | **111.05 MB** | 2,444 | Recursive tree size |
| 23 | `data/processed` | **104.49 MB** | 142 | Recursive tree size |
| 24 | `dist/LANDSLIDENEI/_internal/data/processed` | **104.49 MB** | 142 | Recursive tree size |
| 25 | `.git/objects/32` | **96.45 MB** | 131 | Recursive tree size |
| 26 | `venv/Lib/site-packages/transformers` | **79.65 MB** | 5,275 | Recursive tree size |
| 27 | `data/inspection` | **78.23 MB** | 32 | Recursive tree size |
| 28 | `data/inspection/landslide_pdfs` | **75.02 MB** | 6 | Recursive tree size |
| 29 | `.git/objects/a3` | **70.84 MB** | 134 | Recursive tree size |
| 30 | `installer` | **70.43 MB** | 1 | Recursive tree size |
| 31 | `venv/Lib/site-packages/transformers/models` | **67.82 MB** | 4,698 | Recursive tree size |
| 32 | `dist/LANDSLIDENEI/_internal/scipy` | **61.23 MB** | 96 | Recursive tree size |
| 33 | `data/raw/soil` | **61.16 MB** | 5 | Recursive tree size |
| 34 | `dist/LANDSLIDENEI/_internal/data/raw/soil` | **61.16 MB** | 5 | Recursive tree size |
| 35 | `dist/LANDSLIDENEI/_internal/data/raw` | **61.16 MB** | 5 | Recursive tree size |
| 36 | `build/LANDSLIDENEI` | **57.37 MB** | 16 | Recursive tree size |
| 37 | `build` | **57.37 MB** | 16 | Recursive tree size |
| 38 | `venv/Lib/site-packages/pandas` | **52.45 MB** | 2,967 | Recursive tree size |
| 39 | `dist/LANDSLIDENEI/_internal/rasterio.libs` | **51.81 MB** | 34 | Recursive tree size |
| 40 | `venv/Lib/site-packages/rasterio.libs` | **51.81 MB** | 34 | Recursive tree size |
| 41 | `venv/Lib/site-packages/pymupdf` | **51.45 MB** | 124 | Recursive tree size |
| 42 | `.git/objects/8f` | **49.22 MB** | 135 | Recursive tree size |
| 43 | `venv/Lib/site-packages/sympy` | **48.38 MB** | 3,093 | Recursive tree size |
| 44 | `venv/Lib/site-packages/pyogrio.libs` | **47.89 MB** | 23 | Recursive tree size |
| 45 | `data/raw/cwc_telemetry_hourly` | **40.29 MB** | 16 | Recursive tree size |
| 46 | `venv/Lib/site-packages/torch/include` | **37.43 MB** | 9,375 | Recursive tree size |
| 47 | `venv/Lib/site-packages/sklearn` | **36.52 MB** | 1,644 | Recursive tree size |
| 48 | `venv/Lib/site-packages/numpy` | **28.49 MB** | 1,505 | Recursive tree size |
| 49 | `venv/Lib/site-packages/matplotlib` | **24.17 MB** | 796 | Recursive tree size |
| 50 | `venv/Lib/site-packages/torch/include/ATen` | **23.38 MB** | 7,768 | Recursive tree size |

---

## Section F: File Count and Size by Extension

| Extension | Total Size | File Count | Purpose in Project |
| :--- | :--- | :--- | :--- |
| `.tif` | **2.57 GB** | 60 | Copernicus DEM & ESA WorldCover GeoTIFF rasters |
| `<no_ext>` | **656.65 MB** | 35,477 | Git objects, license files, extensionless binaries |
| `.dll` | **600.98 MB** | 147 | Compiled Windows dynamic link libraries (Torch, GDAL, BLAS) |
| `.pyd` | **285.82 MB** | 594 | Python C-extension compiled shared modules |
| `.py` | **250.46 MB** | 16,433 | Python source code files (src, tests, scripts, venv) |
| `.csv` | **216.40 MB** | 333 | Landslide events, CWC rainfall features, validation tabular data |
| `.pyc` | **198.18 MB** | 16,223 | Compiled Python bytecode cache |
| `.shp` | **151.09 MB** | 3 | ESRI shapefile geometric vectors (OSM roads) |
| `.pdf` | **113.53 MB** | 19 | Reference landslide atlases and NESAC reports |
| `.exe` | **113.31 MB** | 65 | Executables (LANDSLIDENEI.exe, installer, venv scripts) |
| `.dbf` | **55.09 MB** | 3 | Shapefile attribute database tables |
| `.db` | **45.25 MB** | 5 | SQLite and metadata databases |
| `.lib` | **43.75 MB** | 215 | Static library files (inside venv site-packages) |
| `.h` | **39.61 MB** | 9,464 | C/C++ header files (numpy, torch, scipy dev packages in venv) |
| `.json` | **35.73 MB** | 241 | Pre-computed 3D terrain cache and GeoJSON feature layers |
| `.c` | **18.09 MB** | 84 | General asset |
| `.pkg` | **16.48 MB** | 1 | General asset |
| `.pyz` | **16.46 MB** | 1 | General asset |
| `.pkl` | **10.73 MB** | 13 | Trained ML pipelines (static_lsm_pipeline.joblib) |
| `.gz` | **10.70 MB** | 297 | Compressed 3D terrain cache payloads (.json.gz) |
| `.ttf` | **6.84 MB** | 43 | General asset |
| `.joblib` | **5.89 MB** | 2 | Trained ML pipelines (static_lsm_pipeline.joblib) |
| `.html` | **5.45 MB** | 13 | General asset |
| `.zip` | **5.23 MB** | 7 | General asset |
| `.pyi` | **4.79 MB** | 482 | General asset |
| `.geojson` | **4.19 MB** | 11 | General asset |
| `.png` | **3.99 MB** | 202 | General asset |
| `.npz` | **3.66 MB** | 25 | General asset |
| `.pyx` | **3.07 MB** | 137 | General asset |
| `.txt` | **2.64 MB** | 244 | General asset |

---

## Section G: Large Files by Threshold

- **Files > 500 MB:** `0 files`
- **Files > 100 MB:** `4 files`
- **Files > 50 MB:** `20 files`
- **Files > 10 MB:** `89 files`

### All Files Greater Than 50 MB

| File Path | Size | Functional Category | Action Candidate |
| :--- | :--- | :--- | :--- |
| `venv/Lib/site-packages/torch/lib/torch_cpu.dll` | **290.95 MB** | Python Virtual Environment | REGENERABLE DEV ENV |
| `.git/objects/pack/tmp_pack_zdkbHR` | **177.00 MB** | Git Garbage | SAFE CLEANUP VIA GIT GC |
| `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.shp` | **133.99 MB** | Raw Road Vector | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E087_Map.tif` | **112.02 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E090_Map.tif` | **94.25 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `.git/objects/32/720d956e125b8a271ba8411c72683402af885d` | **93.07 MB** | Git Historical Object | KEEP (Git Blob - Prunable) |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E096_Map.tif` | **91.67 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N21E093_Map.tif` | **90.07 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E087_Map.tif` | **84.72 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E090_Map.tif` | **80.91 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N27E093_Map.tif` | **75.40 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `installer/LANDSLIDENEI_Setup_x64.exe` | **70.43 MB** | Installer Binary | KEEP (or Archive Outside) |
| `.git/objects/a3/33a64226d5680ea43f21bd2b974bd1b431d615` | **70.35 MB** | Git Historical Object | KEEP (Git Blob - Prunable) |
| `data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Processed Feature | KEEP (Core Operational Dataset) |
| `dist/LANDSLIDENEI/_internal/data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Standalone Runtime | KEEP (Active Standalone Executable) |
| `data/inspection/landslide_pdfs/Landslides_Atlas_of_India_Updated_25Aug2023.pdf` | **63.83 MB** | Inspection PDF Document | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N21E090_Map.tif` | **56.22 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.dbf` | **53.06 MB** | Raw Road Vector | RECOMMEND MOVE OUTSIDE |
| `data/raw/worldcover/esa_worldcover_v200/ESA_WorldCover_10m_2021_v200_N24E093_Map.tif` | **52.87 MB** | Raw Landcover GeoTIFF | RECOMMEND MOVE OUTSIDE |
| `data/raw/dem/copernicus_glo30/downloads/Copernicus_DSM_COG_10_N23_00_E091_00_DEM.tif` | **50.13 MB** | Raw DEM GeoTIFF | RECOMMEND MOVE OUTSIDE |

---

## Section H: Functional Repository Category Breakdown

| Category | Total Size | File Count | Role & Policy |
| :--- | :--- | :--- | :--- |
| **Raw Datasets (Soil, Landcover, OSM, Historical Sources)** | **274.16 MB** | 46 | Must preserve raw source integrity; candidate for offline archive |
| **Raw DEM Files (Copernicus GLO-30 30m Rasters)** | **2.51 GB** | 57 | 41 tiles (1.73 GB). Runtime relies on 19.68MB cache; candidate for external move |
| **Processed Datasets (CWC features, village profiles, landslide layers)** | **163.06 MB** | 58 | CRITICAL: Actively required by risk engine and dashboard |
| **Model Artifacts (static_lsm_pipeline.joblib)** | **8.31 MB** | 6 | CRITICAL: NEVER MODIFY OR RETRAIN. Required for inference |
| **Terrain Caches (data/processed/dem/terrain_cache)** | **19.65 MB** | 116 | CRITICAL: 16 corridors + 57 regional tiles (19.68 MB). Used by runtime EXE |
| **Python Virtual Environment (venv/)** | **1.25 GB** | 46,842 | REGENERABLE: Can be recreated via requirements.txt with Python 3.10.11 |
| **PyInstaller Intermediate Build Artifacts (build/)** | **57.37 MB** | 16 | REGENERABLE: Safely deletable after verifying dist/ executable |
| **Packaged Standalone Executable (dist/LANDSLIDENEI/)** | **520.39 MB** | 2,636 | CRITICAL: Preserved. Verified 100% operational across all 8 NER states |
| **Compiled Inno Setup Installer (installer/)** | **70.43 MB** | 1 | Contains LANDSLIDENEI_Setup_x64.exe (70.43 MB). Tracked by Git |
| **Python Bytecode & Pytest Caches (__pycache__, .pytest_cache)** | **792.92 KB** | 71 | SAFE TO DELETE: Regenerated automatically on test/run execution |
| **Temporary & Scratch Artifacts (scratch/, temp_*)** | **3.36 MB** | 167 | SAFE TO DELETE / CLEANUP: Scratch scripts and duplicate test PDFs |
| **Application Runtime Logs (*.log)** | **26.71 KB** | 4 | SAFE TO DELETE: Operational and startup log files |
| **Test Suite Files & Fixtures (tests/)** | **156.68 KB** | 22 | CRITICAL: Must keep automated verification tests intact |
| **Theme & Asset Archives (*.zip)** | **3.45 MB** | 3 | Candidates for archiving outside project |
| **Core Source Code (src/, api/, dashboard/, website/, scripts/)** | **2.02 MB** | 117 | CRITICAL: Must be preserved 100% untouched |
| **Project Documentation & Reports (docs/, README.md)** | **19.45 MB** | 18 | CRITICAL: Must be preserved and updated |
| **Git Repository Data & VCS Objects (.git/)** | **647.85 MB** | 32,361 | Git tracking, commit history, and packfiles (647.56 MB) |

---

## Section I: Duplicate Files Analysis (SHA-256 Exact Matches)

Total exact duplicate groups detected: **432 groups**.

### Key High-Impact Duplicate Groups

| SHA-256 (Prefix) | File Size | Redundant Copies | Space Wasted | File Paths | Analysis & Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `a60f971f7b...` | **68.78 MB** | 2 | **68.78 MB** | `data/processed/cwc_rainfall_features.csv`<br>`dist/LANDSLIDENEI/_internal/data/processed/cwc_rainfall_features.csv` | Bundled into dist/ by PyInstaller. Keep data/processed copy for source development, keep dist/ copy for standalone runtime. |
| `6547e9fb96...` | **19.45 MB** | 2 | **19.45 MB** | `dist/LANDSLIDENEI/_internal/numpy.libs/libscipy_openblas64_-13e2df515630b4a41f92893938845698.dll`<br>`venv/Lib/site-packages/numpy.libs/libscipy_openblas64_-13e2df515630b4a41f92893938845698.dll` | PyInstaller binary bundling from venv. Required by standalone executable. |
| `6b2103f2ae...` | **19.22 MB** | 2 | **19.22 MB** | `dist/LANDSLIDENEI/_internal/scipy.libs/libscipy_openblas-f07f5a5d207a3a47104dca54d6d0c86a.dll`<br>`venv/Lib/site-packages/scipy.libs/libscipy_openblas-f07f5a5d207a3a47104dca54d6d0c86a.dll` | PyInstaller binary bundling from venv. Required by standalone executable. |
| `e6ad54e58d...` | **18.78 MB** | 2 | **18.78 MB** | `dist/LANDSLIDENEI/_internal/rasterio.libs/gdal-06c8a783fc258d4e4739c3a67902a55f.dll`<br>`venv/Lib/site-packages/rasterio.libs/gdal-06c8a783fc258d4e4739c3a67902a55f.dll` | PyInstaller binary bundling from venv. Required by standalone executable. |
| `4b9543a6f1...` | **16.89 MB** | 2 | **16.89 MB** | `data/raw/soil/silt_0-5cm_mean_nei.tif`<br>`dist/LANDSLIDENEI/_internal/data/raw/soil/silt_0-5cm_mean_nei.tif` | Bundled into dist/ by PyInstaller. Keep data/raw/soil copy, keep dist/ copy for standalone runtime. |
| `eb270709b3...` | **16.76 MB** | 2 | **16.76 MB** | `build/LANDSLIDENEI/LANDSLIDENEI.exe`<br>`dist/LANDSLIDENEI/LANDSLIDENEI.exe` | Intermediate PyInstaller build duplicate. Safe to delete `build/LANDSLIDENEI/LANDSLIDENEI.exe` (16.76 MB); retain `dist/`. |
| `59fde11773...` | **16.40 MB** | 2 | **16.40 MB** | `data/raw/soil/clay_0-5cm_mean_nei.tif`<br>`dist/LANDSLIDENEI/_internal/data/raw/soil/clay_0-5cm_mean_nei.tif` | Bundled into dist/ by PyInstaller. Keep data/raw/soil copy, keep dist/ copy for standalone runtime. |
| `9bbb9c5577...` | **16.35 MB** | 2 | **16.35 MB** | `data/raw/soil/sand_0-5cm_mean_nei.tif`<br>`dist/LANDSLIDENEI/_internal/data/raw/soil/sand_0-5cm_mean_nei.tif` | Bundled into dist/ by PyInstaller. Keep data/raw/soil copy, keep dist/ copy for standalone runtime. |
| `ea183dab08...` | **10.67 MB** | 2 | **10.67 MB** | `data/raw/historical_landslide_rainfall/sources/NESAC_SR_277_2022_SLI2021.pdf`<br>`scratch/SLI2021.pdf` | EXACT DUPLICATE: Delete `scratch/SLI2021.pdf` (10.67 MB); retain original in `data/raw/historical_landslide_rainfall/sources/`. |
| `0a7bbb8435...` | **9.49 MB** | 2 | **9.49 MB** | `data/raw/soil/bdod_0-5cm_mean_nei.tif`<br>`dist/LANDSLIDENEI/_internal/data/raw/soil/bdod_0-5cm_mean_nei.tif` | Bundled into dist/ by PyInstaller. Keep data/raw/soil copy, keep dist/ copy for standalone runtime. |
| `f058109ef6...` | **8.99 MB** | 2 | **8.99 MB** | `data/processed/rainfall/rainfall_daily_integrated.csv`<br>`dist/LANDSLIDENEI/_internal/data/processed/rainfall/rainfall_daily_integrated.csv` | Redundant copy across directories. Safe to consolidate. |
| `7f5956f66a...` | **8.93 MB** | 2 | **8.93 MB** | `dist/LANDSLIDENEI/_internal/rasterio/proj_data/proj.db`<br>`venv/Lib/site-packages/rasterio/proj_data/proj.db` | Redundant copy across directories. Safe to consolidate. |
| `47a7205d83...` | **8.83 MB** | 2 | **8.83 MB** | `dist/LANDSLIDENEI/_internal/pyproj/proj_dir/share/proj/proj.db`<br>`venv/Lib/site-packages/pyproj/proj_dir/share/proj/proj.db` | Redundant copy across directories. Safe to consolidate. |
| `7487d4f134...` | **8.65 MB** | 2 | **8.65 MB** | `data/raw/historical_landslide_rainfall/sources/NESAC_SR_261_2021_SLI2020.pdf`<br>`scratch/SLI2020.pdf` | Redundant copy across directories. Safe to consolidate. |
| `df0c617422...` | **7.53 MB** | 2 | **7.53 MB** | `dist/LANDSLIDENEI/_internal/PIL/_avif.cp310-win_amd64.pyd`<br>`venv/Lib/site-packages/PIL/_avif.cp310-win_amd64.pyd` | Redundant copy across directories. Safe to consolidate. |

---

## Section J: Phase 2 Git Safety Audit

### 1. Git Repository Metrics
- **`.git` Directory Size:** **647.56 MB** (679,020,439 bytes)
- **Total Git Tracked Files:** **323 files**
- **Loose Git Objects:** 32,292 objects (470.43 MiB)
- **Unfinished Pack Garbage:** `.git/objects/pack/tmp_pack_zdkbHR` (**177.00 MiB**)

### 2. Large Files Tracked vs Untracked

#### Tracked Large Files (> 10 MB)
| Tracked File Path | Size | Status | Notes |
| :--- | :--- | :--- | :--- |
| `installer/LANDSLIDENEI_Setup_x64.exe` | **70.43 MB** | TRACKED IN GIT | Installer executable previously committed to git index |

> [!NOTE]
> Only **ONE** file greater than 10 MB is tracked by Git: `installer/LANDSLIDENEI_Setup_x64.exe` (70.43 MB). All other 88 large files in the repository are properly untracked and excluded by `.gitignore`.

#### Raw Dataset Git Tracking Verification
| Checked Directory | Tracked Files Found | Audit Finding |
| :--- | :--- | :--- |
| `data/raw/` | `['data/raw/landslide_training.csv']` | **CLEAN.** Only `landslide_training.csv` (56 KB) is tracked. Zero raw DEM, zero WorldCover rasters, zero shapefiles are committed! |
| `data/raw/dem/copernicus_glo30/downloads/` | `NONE (0 files)` | **CLEAN.** All 41 raw DEM GeoTIFFs (1.73 GB) are untracked. |
| `data/raw/worldcover/` | `NONE (0 files)` | **CLEAN.** All 9 ESA WorldCover GeoTIFFs (727 MB) are untracked. |
| `data/raw/osm/` | `NONE (0 files)` | **CLEAN.** All OSM road vectors (187 MB) are untracked. |

### 3. Historical Git Blobs Inspection
- Large historical blobs detected in Git objects include:
  1. `.git/objects/pack/tmp_pack_zdkbHR` (177.00 MB): Temporary packfile left behind by an interrupted `git repack` or `git gc` command.
  2. `32720d956e125b...` (93.07 MB): Unreferenced dangling Windows PE DLL blob in git object database.
  3. `a333a64226d568...` (70.35 MB): Historical blob of `installer/LANDSLIDENEI_Setup_x64.exe`.
- **Policy Compliance:** In strict accordance with instructions, **NO Git history rewriting** (`git filter-repo`, `git reset --hard`) has been executed or proposed.

---

## Section K: Phase 3 Classification Table (Every Large Item)

Allowed Actions: `KEEP`, `DELETE`, `MOVE_OUTSIDE_PROJECT`, `REGENERABLE`.

| Path | Size | Type | Required? | Action | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data/raw/dem/copernicus_glo30/downloads/ (41 GeoTIFFs)` | **1.73 GB** | Raw DEM | NO (Runtime uses 19.7MB terrain cache) | **MOVE_OUTSIDE_PROJECT** | Runtime standalone EXE and API query pre-generated terrain_cache. Raw DEM only needed for offline recalculation. Recommend move to external archive once destination confirmed. |
| `venv/` | **1.25 GB** | Python Dev Env | YES (For active python development) | **REGENERABLE** | Contains 46,842 files including PyTorch (300MB DLL). Recreatable via requirements.txt using Python 3.10.11. |
| `.git/objects/pack/tmp_pack_zdkbHR` | **177.00 MB** | Git Garbage | NO (Interrupted packfile) | **DELETE (via git prune)** | Unfinished temporary packfile created during interrupted git operation. Safe to prune. |
| `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.shp` | **133.99 MB** | Raw Vector | NO (Runtime uses extracted road buffers) | **MOVE_OUTSIDE_PROJECT** | Original OSM raw road shapefile. Not queried during operational runtime. |
| `data/raw/worldcover/esa_worldcover_v200/ (9 GeoTIFFs)` | **727.67 MB** | Raw Landcover | NO (Offline training only) | **MOVE_OUTSIDE_PROJECT** | ESA WorldCover 10m rasters used during model training. Not required for packaged application runtime. |
| `installer/LANDSLIDENEI_Setup_x64.exe` | **70.43 MB** | Installer Binary | YES (Production distribution) | **KEEP** | Compiled Inno Setup desktop installer. Required for end-user distribution. |
| `data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Processed Dataset | YES (Active Operational Feature) | **KEEP** | Core operational CWC rainfall dataset with station alignments. Mandatory for risk fusion. |
| `dist/LANDSLIDENEI/_internal/data/processed/cwc_rainfall_features.csv` | **68.78 MB** | Bundled Runtime Data | YES (Standalone Executable Dependency) | **KEEP** | Bundled copy inside standalone application distribution. Required for LANDSLIDENEI.exe. |
| `data/inspection/landslide_pdfs/Landslides_Atlas_of_India_Updated_25Aug2023.pdf` | **63.83 MB** | Inspection PDF | NO (Reference documentation) | **MOVE_OUTSIDE_PROJECT** | Authoritative ISRO reference document. Can be archived outside working project tree. |
| `build/LANDSLIDENEI/` | **57.37 MB** | PyInstaller Build Tree | NO (Intermediate compiler cache) | **DELETE** | Intermediate compilation directory from PyInstaller. Standalone executable in dist/ is verified operational. |
| `data/raw/osm/geofabrik_nei/gis_osm_roads_free_1.dbf` | **53.06 MB** | Raw Vector DBF | NO (Offline reference) | **MOVE_OUTSIDE_PROJECT** | Road attributes table. Not required for operational inference. |
| `data/raw/soil/ (5 GeoTIFFs)` | **68.61 MB** | Raw Soil Layers | YES (Runtime point query) | **KEEP** | SoilGrids rasters bundled into dist/ and accessed by LocationProfiler for soil composition features. |
| `dist/LANDSLIDENEI/LANDSLIDENEI.exe` | **16.76 MB** | Standalone Executable | YES (Primary Desktop Application) | **KEEP** | Verified 100% operational across all 8 NER states. Mandatory to preserve. |
| `model/static_lsm_pipeline.joblib` | **2.94 MB** | ML Pipeline Model | YES (Core Risk Inference Engine) | **KEEP** | Production Random Forest Susceptibility Pipeline. NEVER MODIFY OR RETRAIN. |
| `data/processed/dem/terrain_cache/` | **19.68 MB** | Pre-computed 3D Terrain Cache | YES (Core 3D & Elevation Engine) | **KEEP** | Contains 16 corridors + 57 regional DEM tiles. Powers native 3D visualization and elevation queries. |
| `scratch/SLI2021.pdf` | **10.67 MB** | Duplicate Document | NO (Exact duplicate of data/raw/...) | **DELETE** | Exact duplicate of data/raw/historical_landslide_rainfall/sources/NESAC_SR_277_2022_SLI2021.pdf. |
| `scratch/SLI2020.pdf` | **8.65 MB** | Duplicate Document | NO (Exact duplicate of data/raw/...) | **DELETE** | Temporary scratch copy of NESAC report. |
| `scratch/sli2021_images/` | **2.18 MB** | Temporary OCR Extracted Images | NO (Scratch OCR experiment) | **DELETE** | Extracted PNGs from OCR testing in scratch directory. |
| `__pycache__ / *.pyc (outside venv/dist)` | **792.92 KB** | Python Bytecode Cache | NO (Auto-regenerable) | **DELETE** | Python compiled bytecode caches. Regenerates automatically on execution. |
| `.pytest_cache/` | **32 KB** | Test Cache | NO (Auto-regenerable) | **DELETE** | Pytest internal run cache. Regenerated when running pytest. |

---

## Section L: Operational Readiness Confirmation of Packaged Executable

Before formulating cleanup classifications, the standalone executable was executed directly against its built-in self-tests:
1. `.\dist\LANDSLIDENEI\LANDSLIDENEI.exe --check-health`
   - **Result:** `EXIT CODE 0 (PASS)`
2. `.\dist\LANDSLIDENEI\LANDSLIDENEI.exe --test-operational-workflow`
   - **Result:** `EXIT CODE 0 (PASS)`
   - **Report Summary:**
     * 8 NER State Capital / Key Corridors: `ALL 8 PASS`
     * 75 Historical Landslides Layer: `PASS (75 Verified Events Connected)`
     * Out-of-Domain 400 Guardrail: `PASS (400 Bad Request)`
     * Zero Synthetic Fallbacks: `PASS (Strict GLO-30 & Empirical Model A)`
     * Final Operational Readiness: `ALL 8 NER STATES FULLY OPERATIONAL`

Therefore, `dist/LANDSLIDENEI/` is fully verified and must be strictly preserved.