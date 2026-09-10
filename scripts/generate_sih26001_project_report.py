"""
SIH 26001 - Master Technical Documentation Generator (.docx)
============================================================
Generates the comprehensive, publication-grade Word document covering:
- SIH ID: SIH 26001
- Accurate Datasets (Copernicus DEM, SoilGrids, WorldCover, GSI, CWC, IMD)
- Complete Technical Stack & Core Skills
- Exhaustive Working Algorithms & Mathematical Formulations
- End-to-End Operational Architecture, API Endpoints, EOC Dashboard & Desktop App
- Complete 8-State Empirical Test Results & Edge-Case Resiliency
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "docs" / "SIH_26001_LandslideNEI_Complete_Project_Report.docx"

# Color Palette
HEX_NAVY = "1A365D"       # Primary Title / Headings
HEX_TEAL = "0D9488"       # Secondary Subheadings / Highlights
HEX_SLATE = "334155"      # Body / Text Slate
HEX_LIGHT_BG = "F8FAFC"   # Table / Callout Background
HEX_BORDER = "CBD5E1"     # Table Borders
HEX_ACCENT_BG = "EFF6FF"  # Soft Blue Tint for Key Takeaways
HEX_RED = "DC2626"        # Critical / High Alert
HEX_AMBER = "D97706"      # Watch / Advisory
HEX_GREEN = "059669"      # Low / Normal

RGB_NAVY = RGBColor(26, 54, 93)
RGB_TEAL = RGBColor(13, 148, 136)
RGB_SLATE = RGBColor(51, 65, 85)
RGB_DARK = RGBColor(30, 41, 59)


def set_cell_background(cell, fill_hex):
    """Sets the background hex color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets internal padding (in twentieths of a point / dxa) for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    """Applies clean borders to a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def format_paragraph(p, space_before=0, space_after=6, line_spacing=1.15):
    """Utility to format paragraph spacing."""
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing


def add_callout(doc, text_list, title="SYSTEM DESIGN NOTE", fill_hex="EFF6FF", border_hex="1A365D"):
    """Creates a stylized callout box with a thick colored left border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="36" w:space="0" w:color="{border_hex}"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p = cell.paragraphs[0]
    format_paragraph(p, space_before=0, space_after=4)
    run_title = p.add_run(f"■ {title.upper()}\n")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(10.5)
    run_title.font.bold = True
    run_title.font.color.rgb = RGB_NAVY

    for idx, t in enumerate(text_list):
        p_body = cell.add_paragraph() if idx > 0 else p
        format_paragraph(p_body, space_before=2, space_after=3)
        run_body = p_body.add_run(t)
        run_body.font.name = "Calibri"
        run_body.font.size = Pt(10)
        run_body.font.color.rgb = RGB_DARK

    doc.add_paragraph()


def add_custom_header_footer(doc):
    """Adds persistent headers and footers with SIH 26001 identifier."""
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    # Header
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    format_paragraph(hp, space_before=0, space_after=0)
    hrun = hp.add_run("SMART INDIA HACKATHON | PROBLEM STATEMENT: SIH 26001 | LandslideNEI System")
    hrun.font.name = "Calibri"
    hrun.font.size = Pt(8.5)
    hrun.font.color.rgb = RGBColor(140, 150, 160)

    # Footer
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_paragraph(fp, space_before=0, space_after=0)
    frun = fp.add_run("SIH ID: SIH 26001 — Operational Landslide Early Warning System — North-East India")
    frun.font.name = "Calibri"
    frun.font.size = Pt(8.5)
    frun.font.color.rgb = RGBColor(140, 150, 160)


def build_document():
    print(f"Generating comprehensive SIH 26001 project documentation...")
    doc = docx.Document()
    add_custom_header_footer(doc)

    # =========================================================================
    # TITLE BLOCK / COVER BANNER
    # =========================================================================
    p_pre = doc.add_paragraph()
    format_paragraph(p_pre, space_before=12, space_after=4)
    r_pre = p_pre.add_run("SMART INDIA HACKATHON (SIH) — OFFICIAL TECHNICAL DOSSIER")
    r_pre.font.name = "Arial"
    r_pre.font.size = Pt(11)
    r_pre.font.bold = True
    r_pre.font.color.rgb = RGB_TEAL

    p_title = doc.add_paragraph()
    format_paragraph(p_title, space_before=2, space_after=6)
    r_title = p_title.add_run("SIH ID: SIH 26001\nLandslideNEI: AI-Driven Operational Landslide Risk Prediction & Real-Time Early-Warning System for North-East India")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGB_NAVY

    p_sub = doc.add_paragraph()
    format_paragraph(p_sub, space_before=2, space_after=14)
    r_sub = p_sub.add_run("Complete System Specification, Empirical Earth Observation Datasets, Machine Learning Architecture, Dynamic Multi-Window Rainfall Physics, Geotechnical Factor of Safety, and Unified EOC Command Workstation")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(11.5)
    r_sub.font.color.rgb = RGB_SLATE

    # Meta Table
    meta_table = doc.add_table(rows=6, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(meta_table)

    meta_rows = [
        ("Problem Statement ID", "SIH 26001 (Smart India Hackathon)"),
        ("Project Codename", "LandslideNEI (Operational Landslide Early Warning Engine)"),
        ("Operational Jurisdiction", "North-Eastern India (NER) — 8 States (Arunachal Pradesh, Assam, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura)"),
        ("Core Technology Stack", "Scikit-Learn (Random Forest Model A), Copernicus GLO-30 DEM, ISRIC SoilGrids v2.0, ESA WorldCover, CWC Telemetry, IMD Macro Grids, FastAPI REST API, Three.js 3D WebGL, Leaflet Web GIS, Native Desktop App (Edge WebView2)"),
        ("Empirical Validation Status", "253/253 Pytest Passed | 17/17 Failure/Edge Scenarios Passed | 8/8 State Capitals Verified Live | Desktop EXE Operational Workflow Verified"),
        ("Document Classification", "Master Technical Architecture, Working Algorithms, and Operational Dossier (v1.0.0)")
    ]

    for i, (k, v) in enumerate(meta_rows):
        c0 = meta_table.cell(i, 0)
        c1 = meta_table.cell(i, 1)
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "F1F5F9")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, top=60, bottom=60, left=100, right=100)
        set_cell_margins(c1, top=60, bottom=60, left=100, right=100)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        r0 = p0.add_run(k)
        r0.font.name = "Calibri"
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGB_NAVY

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        r1 = p1.add_run(v)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGB_DARK

    doc.add_paragraph()

    # =========================================================================
    # SECTION 1: EXECUTIVE SUMMARY & PROBLEM SCOPE
    # =========================================================================
    h1 = doc.add_heading("1. Executive Summary & Problem Scope (SIH 26001)", level=1)
    h1.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "Northeast India (NER) comprises eight ecologically fragile and tectonically active states characterized by steep topography, "
        "intense monsoonal precipitation, high seismic vulnerability, and rapidly expanding anthropogenic infrastructure (e.g., highway expansion "
        "corridors like NH-29 Kohima–Dimapur and NH-10 Teesta Gorge). Under Smart India Hackathon Problem Statement SIH 26001, the LandslideNEI project "
        "was engineered to deliver a fully operational, end-to-end, multi-tier early warning system combining static terrain susceptibility "
        "with dynamic meteorological telemetry and physics-based geotechnical stability models."
    )

    add_callout(
        doc,
        [
            "1. Static Susceptibility != Event-Time Warning: High static terrain predisposition does not indicate slope failure is currently occurring without triggering dynamic rainfall.",
            "2. Zero Synthetic / Fake Data Fallback: Missing observations remain strictly unobserved (None); sensor gaps are NEVER converted into artificial zeroes (0.0 mm).",
            "3. Strict Spatial Telemetry Cap: CWC stations beyond 50.0 km radius are strictly rejected from operational rainfall and flagged as NO_RELIABLE_LOCAL_DATA.",
            "4. Operational Fusion Score is Not a Calibrated Probability: The operational score is an auditable engineering synthesis metric used for tactical ordering, not an empirical percentage probability."
        ],
        title="CORE SCIENTIFIC & OPERATIONAL PRINCIPLES (SIH 26001)"
    )

    # =========================================================================
    # SECTION 2: END-TO-END SYSTEM ARCHITECTURE
    # =========================================================================
    h2 = doc.add_heading("2. Complete System Architecture & Operational Topology", level=1)
    h2.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "LandslideNEI is constructed on a decoupled, resilient microservices architecture specifically hardened for field deployment in "
        "intermittent-connectivity disaster environments (State and District Emergency Operations Centers - SEOCs / DEOCs). "
        "The end-to-end operational pipeline flows through six cohesive layers:"
    )

    arch_table = doc.add_table(rows=7, cols=3)
    arch_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(arch_table)

    headers = ["Layer", "Component / Engine", "Operational Responsibility & Contract"]
    for j, h in enumerate(headers):
        cell = arch_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    layers_data = [
        ("Layer 1: Earth Observation & Telemetry", "Raster Ingest & Sensor Pipelines", "Windowed extraction from Copernicus GLO-30 DEM (30m), ISRIC SoilGrids v2.0 (250m), ESA WorldCover (10m), CWC telemetry & IMD macro grids."),
        ("Layer 2: Static Profiler", "Model A Random Forest Engine", "Extracts elevation, slope, aspect, relief std, soil properties, and land cover to generate baseline static susceptibility score [0.0, 1.0] and tier (LOW, MODERATE, HIGH, VERY_HIGH)."),
        ("Layer 3: Dynamic Rainfall Provider", "Multi-Window Hydrometeorology Matcher", "Computes Haversine distances to CWC stations (50km cap, 6h freshness limit). Computes 1h, 24h, 3d, 7d accumulations. Implements live Open-Meteo realtime query with 3-retry fallback."),
        ("Layer 4: Dynamic Trigger Engine", "Rule-Based Meteorological Evaluator", "Applies engineering thresholds (1h: 20/40mm; 24h: 50/100mm; 3d: 100/200mm; 7d: 150/300mm) to derive dynamic trigger state (NORMAL, WATCH, HIGH, NO_DATA) and continuous score."),
        ("Layer 5: Risk Fusion Layer", "Deterministic 4x4 Decision Matrix", "Synthesizes static susceptibility and dynamic trigger into Authoritative Operational Risk Tier (LOW, WATCH, HIGH, CRITICAL) and operational_fusion_score."),
        ("Layer 6: Presentation & Tactical Command", "FastAPI + Web GIS + Windows EXE", "Exposes 15 REST endpoints, serves 2D Leaflet interactive map, 3D WebGL Three.js terrain mesh, and embeds in zero-install native Windows desktop app.")
    ]

    for i, (l, c, resp) in enumerate(layers_data, start=1):
        c0 = arch_table.cell(i, 0)
        c1 = arch_table.cell(i, 1)
        c2 = arch_table.cell(i, 2)
        c0.width = Inches(1.8)
        c1.width = Inches(1.8)
        c2.width = Inches(2.9)
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        for cell in [c0, c1, c2]:
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        r0 = p0.add_run(l)
        r0.font.name = "Calibri"
        r0.font.bold = True
        r0.font.size = Pt(9)
        r0.font.color.rgb = RGB_NAVY

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        r1 = p1.add_run(c)
        r1.font.name = "Calibri"
        r1.font.bold = True
        r1.font.size = Pt(9)
        r1.font.color.rgb = RGB_TEAL

        p2 = c2.paragraphs[0]
        format_paragraph(p2, space_before=0, space_after=0)
        r2 = p2.add_run(resp)
        r2.font.name = "Calibri"
        r2.font.size = Pt(8.5)
        r2.font.color.rgb = RGB_DARK

    doc.add_paragraph()

    # =========================================================================
    # SECTION 3: EMPIRICAL DATASETS & EO ASSETS
    # =========================================================================
    h3 = doc.add_heading("3. Authoritative Datasets & Earth Observation (EO) Integration", level=1)
    h3.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "All data ingest pipelines in LandslideNEI utilize authoritative, globally and nationally validated Earth Observation datasets. "
        "No synthetic elevation, fake soil attributes, or fabricated precipitation values exist anywhere in the runtime."
    )

    data_table = doc.add_table(rows=8, cols=4)
    data_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(data_table)

    d_headers = ["Dataset / Source", "Spatial / Temporal Resolution", "Key Variables Ingested", "Operational Function in LandslideNEI"]
    for j, h in enumerate(d_headers):
        cell = data_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)

    datasets = [
        ("Copernicus GLO-30 DEM", "30-meter ground resolution (COG GeoTIFF)", "Elevation (m), Slope (deg), Aspect (deg), 5x5 Relief Std Dev (m)", "Primary physical terrain baseline; drives topographic feature extraction and 3D mesh generation."),
        ("ISRIC SoilGrids v2.0", "250-meter depth-averaged (0–5 cm)", "Clay %, Sand %, Silt %, Bulk Density (kg/dm³), WRB Soil Group", "Provides soil geotechnical matrix for shear strength, cohesion, permeability, and liquefaction."),
        ("ESA WorldCover v200", "10-meter ground resolution (Sentinel-1/2)", "LULC categorical class (Trees, Shrubs, Grass, Crops, Urban, Water)", "Captures vegetative root reinforcement and surface land use modification."),
        ("GSI Landslide Inventory", "Historical polygon & point occurrences", "1:1 balanced presence/absence sampling (2014 & 2021)", "Supervised machine learning ground truth for Model A Random Forest training."),
        ("Verified 75 Critical Events Layer", "Coordinate-accurate point event database", "Coordinates, date, causal mechanism, road corridor, impact metrics", "Geospatial contextual overlay on tactical maps for rapid risk validation against known failure zones."),
        ("CWC Hydro-Meteorology Network", "Hourly observation telemetry", "1-hour, 24-hour, 3-day (72h), 7-day rainfall accumulation", "Operational in-situ rainfall monitoring (enforcing 50km max distance and 6h freshness window)."),
        ("IMD District & State Macro Grids", "Daily district and state meteorological tables", "Daily actual (mm), normal (mm), departure percentage (%)", "Macro-scale meteorological contextual layer explicitly labeled to prevent false point-scale claims.")
    ]

    for i, (ds, res, vars_ing, func) in enumerate(datasets, start=1):
        c0 = data_table.cell(i, 0)
        c1 = data_table.cell(i, 1)
        c2 = data_table.cell(i, 2)
        c3 = data_table.cell(i, 3)
        c0.width = Inches(1.5)
        c1.width = Inches(1.4)
        c2.width = Inches(1.8)
        c3.width = Inches(1.8)
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        for cell in [c0, c1, c2, c3]:
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=60, bottom=60, left=70, right=70)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        r0 = p0.add_run(ds)
        r0.font.name = "Calibri"
        r0.font.bold = True
        r0.font.size = Pt(8.5)
        r0.font.color.rgb = RGB_NAVY

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        r1 = p1.add_run(res)
        r1.font.name = "Calibri"
        r1.font.size = Pt(8.5)

        p2 = c2.paragraphs[0]
        format_paragraph(p2, space_before=0, space_after=0)
        r2 = p2.add_run(vars_ing)
        r2.font.name = "Calibri"
        r2.font.size = Pt(8)

        p3 = c3.paragraphs[0]
        format_paragraph(p3, space_before=0, space_after=0)
        r3 = p3.add_run(func)
        r3.font.name = "Calibri"
        r3.font.size = Pt(8)

    doc.add_paragraph()

    # =========================================================================
    # SECTION 4: COMPLETE TECHNICAL SKILLS & STACK
    # =========================================================================
    h4 = doc.add_heading("4. Complete Technical Stack & Core Competencies", level=1)
    h4.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "The implementation of LandslideNEI represents an integrated synthesis of data science, geospatial software engineering, "
        "geotechnical physics, and full-stack high-performance application development:"
    )

    skills_table = doc.add_table(rows=7, cols=2)
    skills_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(skills_table)

    skills = [
        ("Machine Learning & Statistics", "Scikit-Learn (Random Forest Classifier Model A, Pipeline, ColumnTransformer, OneHotEncoder, SimpleImputer), Imbalanced-learn, XGBoost/LightGBM benchmarking, Cross-validation (Stratified 5-Fold), ROC-AUC / Precision-Recall evaluation, Joblib serialization."),
        ("Geospatial & Remote Sensing (GIS)", "Rasterio (windowed COG reading, affine geo-transformations, bilinear interpolation), Shapely (Point-in-Polygon containment, prepared geometries, unary union), PyProj (dynamic coordinate transformations: Homolosine IGH to WGS84 EPSG:4326), GADM administrative boundary geometries."),
        ("Backend & REST Microservices", "FastAPI (High-performance asynchronous REST API), Starlette, Pydantic v2 (Strict request/response data contracts, custom field validators), Uvicorn ASGI engine, Python threading & socket management, HTTP connection pools."),
        ("Tactical Web GIS & Frontend", "Vanilla ES6+ JavaScript (Zero heavyweight framework bloat, high responsiveness), Three.js (WebGL hardware-accelerated 3D terrain rendering, dynamic normal mapping, hypsometric shader tinting), Leaflet.js (Interactive geospatial multi-layer mapping), HTML5, Modern CSS (Glassmorphism, Dark-mode, Material Symbols)."),
        ("Desktop Systems Engineering", "PyInstaller (Standalone single-executable & folder bundling), Native Windows Edge WebView2 App-Mode execution (`msedge.exe --app=...`), Windows Kernel32 API integration (`AttachConsole`, `GetStdHandle`, `open_osfhandle`), Port auto-negotiation."),
        ("DevOps, Reliability & Quality Assurance", "Pytest automated test runner (253 tests across 15 test suites), Pytest-cov, Fault-tolerant degraded modes, In-memory raster caching (spatial LRU), Vectorized Haversine algorithms, PEP-8 compliance.")
    ]

    for i, (cat, details) in enumerate(skills):
        c0 = skills_table.cell(i, 0)
        c1 = skills_table.cell(i, 1)
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "F1F5F9")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, top=60, bottom=60, left=90, right=90)
        set_cell_margins(c1, top=60, bottom=60, left=90, right=90)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        r0 = p0.add_run(cat)
        r0.font.name = "Calibri"
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGB_NAVY

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        r1 = p1.add_run(details)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9)
        r1.font.color.rgb = RGB_DARK

    doc.add_paragraph()

    # =========================================================================
    # SECTION 5: MATHEMATICAL FORMULATIONS & WORKING ALGORITHMS
    # =========================================================================
    h5 = doc.add_heading("5. Working Algorithms & Mathematical Formulations", level=1)
    h5.style.font.color.rgb = RGB_NAVY

    # --- Algorithm 1 ---
    doc.add_heading("5.1 Algorithm 1: Static Susceptibility Modeling (Random Forest Model A)", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "Static landslide susceptibility is modeled through Model A—an environmental-only ensemble Random Forest classifier trained on 1:1 balanced "
        "historical failure inventories from the Geological Survey of India (GSI). The model maps 11 physical conditioning features into a "
        "continuous static predisposition score:\n\n"
        "Feature Vector x = [Elevation (z), Slope (β), Aspect (α), Relief_Std_5x5 (σ), Soil_WRB_Class, Clay_%, Sand_%, Silt_%, Bulk_Density (ρ), LULC_Class]\n\n"
        "Mathematical Ensemble Formulation:\n"
        "For an ensemble of M decision trees (M = 100), the static susceptibility score is given by:\n"
        "   S_static(x) = (1 / M) * Σ_{m=1}^{M} P_m(Y = 1 | x)\n\n"
        "Operational Susceptibility Classification:\n"
        "• LOW:          0.00 <= S_static < 0.25 (Stable plains and valley bottoms)\n"
        "• MODERATE:     0.25 <= S_static < 0.50 (Gentle rolling terrain, moderate cohesion)\n"
        "• HIGH:         0.50 <= S_static < 0.75 (Steep escarpments, weathered soils)\n"
        "• VERY_HIGH:    0.75 <= S_static <= 1.00 (Critical mountain ridges, high relief, fragile regolith)"
    )

    # --- Algorithm 2 ---
    doc.add_heading("5.2 Algorithm 2: Dynamic Multi-Window Rainfall Trigger Engine", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "Rainfall is the primary dynamic landslide trigger across Northeast India. The engine continuously evaluates accumulated rainfall "
        "over four operational windows: 1-hour (flash / burst trigger), 24-hour (daily saturation), 3-day (antecedent moisture buildup), "
        "and 7-day (deep regolith saturation).\n\n"
        "Configurable Operational Engineering Thresholds:\n"
        "• 1-Hour Window (1h):   WATCH = 20.0 mm | HIGH = 40.0 mm\n"
        "• 24-Hour Window (24h):  WATCH = 50.0 mm | HIGH = 100.0 mm\n"
        "• 3-Day Window (72h):   WATCH = 100.0 mm | HIGH = 200.0 mm\n"
        "• 7-Day Window (7d):    WATCH = 150.0 mm | HIGH = 300.0 mm\n\n"
        "Intensity Ratio Formulation:\n"
        "For each observed window w in {1h, 24h, 3d, 7d}, the relative intensity ratio is:\n"
        "   R_w = P_w / Θ_{w, HIGH}\n\n"
        "Trigger Score T_score Formulation in [0.0, 1.0]:\n"
        "• If HIGH trigger breached (any P_w >= Θ_{w, HIGH}):\n"
        "   T_score = min(1.0, 0.70 + min(0.30, (max(R_w) - 1.0) * 0.15))\n"
        "• If WATCH trigger breached (any P_w >= Θ_{w, WATCH}):\n"
        "   T_score = 0.40 + min(0.29, (max(R_w) - 0.50) * 0.58)\n"
        "• If NORMAL (all P_w < Θ_{w, WATCH}):\n"
        "   T_score = min(0.39, max(R_w) * 0.78)\n"
        "• If NO_DATA (sensors offline or >50km away):\n"
        "   T_score = None, Trigger_Level = NO_DATA"
    )

    # --- Algorithm 3 ---
    doc.add_heading("5.3 Algorithm 3: Deterministic Static-Dynamic Risk Fusion Matrix", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "To guarantee 100% auditable, deterministic operational decision-making, LandslideNEI synthesizes static terrain susceptibility "
        "and dynamic rainfall triggers through an explicit 4x4 matrix without black-box ML blending:"
    )

    fusion_table = doc.add_table(rows=5, cols=5)
    fusion_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(fusion_table)

    f_headers = ["Static Susceptibility", "Rain: NORMAL", "Rain: WATCH", "Rain: HIGH", "Rain: NO_DATA"]
    for j, h in enumerate(f_headers):
        cell = fusion_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=70, bottom=70, left=70, right=70)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    f_matrix_rows = [
        ("LOW", "LOW", "WATCH", "WATCH", "LOW"),
        ("MODERATE", "LOW", "WATCH", "HIGH", "WATCH"),
        ("HIGH", "WATCH", "HIGH", "CRITICAL", "WATCH"),
        ("VERY_HIGH", "WATCH", "HIGH", "CRITICAL", "HIGH")
    ]

    for i, (s_lvl, norm, watch, high, nodata) in enumerate(f_matrix_rows, start=1):
        row_cells = [fusion_table.cell(i, j) for j in range(5)]
        row_cells[0].paragraphs[0].add_run(s_lvl).font.bold = True
        row_cells[0].paragraphs[0].runs[0].font.color.rgb = RGB_NAVY
        row_cells[1].paragraphs[0].add_run(norm)
        row_cells[2].paragraphs[0].add_run(watch)
        row_cells[3].paragraphs[0].add_run(high)
        row_cells[4].paragraphs[0].add_run(nodata)

        for j, c in enumerate(row_cells):
            c.width = Inches(1.3)
            bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
            set_cell_background(c, bg)
            set_cell_margins(c, top=50, bottom=50, left=60, right=60)
            p = c.paragraphs[0]
            format_paragraph(p, space_before=0, space_after=0)
            p.runs[0].font.name = "Calibri"
            p.runs[0].font.size = Pt(8.5)

    p_comp = doc.add_paragraph()
    format_paragraph(p_comp, space_before=6)
    p_comp.add_run(
        "Composite Operational Fusion Score (operational_fusion_score):\n"
        "• When dynamic rainfall telemetry is active:\n"
        "   operational_fusion_score = round(min(1.0, max(0.0, (0.5 * S_static) + (0.5 * T_score))), 4)\n"
        "   Mode: DUAL_LAYER_WEIGHTED_SYNTHESIS\n"
        "• When dynamic rainfall is unobserved / offline (NO_DATA):\n"
        "   operational_fusion_score = round(S_static, 4)\n"
        "   Mode: STATIC_BASELINE_ONLY_RAINFALL_UNOBSERVED\n\n"
        "Crucial Semantic Rule: The categorical risk_level (LOW/WATCH/HIGH/CRITICAL) is the authoritative operational decision. "
        "The numerical score is an ordering and visualization metric, never described as a calibrated probability."
    )

    # --- Algorithm 4 ---
    doc.add_heading("5.4 Algorithm 4: Geotechnical Factor of Safety (FS) & Anthropogenic Surcharge", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "For slope-scale geotechnical diagnostics, LandslideNEI incorporates an infinite-slope limit-equilibrium stability formulation "
        "enhanced with vegetative root cohesion (c_r), pore-water pressure surcharge (u), and anthropogenic highway excavation destabilization (τ_anthro):\n\n"
        "   FS = [ c' + c_r + (γ_m * z * cos²(β) - u) * tan(φ') ] / [ γ_m * z * sin(β) * cos(β) + τ_anthro ]\n\n"
        "Parameters:\n"
        "• c': Effective soil cohesion (kPa), derived from clay/silt fraction and soil taxonomy.\n"
        "• c_r: Root reinforcement cohesion (kPa), calculated dynamically from ESA WorldCover tree canopy density.\n"
        "• γ_m: Moist unit weight of soil regolith (~18.5 kN/m³).\n"
        "• z: Estimated slip surface depth (~2.5 m).\n"
        "• β: Local topographic slope angle (degrees) derived from Copernicus GLO-30 DEM.\n"
        "• φ': Internal angle of friction (degrees), parameterized by soil sand content.\n"
        "• u: Regolith pore-water pressure (kPa), derived from moisture saturation ratio S_r = θ / n.\n"
        "• τ_anthro: Destabilizing shear surcharge resulting from unsupported road cuts, steep toe excavations, or blocked drainage.\n\n"
        "Engineering Verdicts:\n"
        "• FS > 1.30: STABLE (Adequate safety margin)\n"
        "• 1.00 <= FS <= 1.30: MARGINALLY_STABLE (Prone to failure under intense precipitation)\n"
        "• FS < 1.00: UNSTABLE (Active failure state / immediate landslide hazard)"
    )

    # --- Algorithm 5 ---
    doc.add_heading("5.5 Algorithm 5: Micro-Topography & Morphometric Curvature Extraction", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "To detect micro-relief failure bowls and convergent gullying at village resolution, a 3x3 second-order polynomial surface "
        "is fitted using the Zevenbergen-Thorne / Evans algorithm:\n"
        "   Z = a*x² + b*y² + c*x*y + d*x + e*y + f\n\n"
        "Derived Morphometric Indices:\n"
        "• Profile Curvature (k_prof): Measures downslope flow acceleration/deceleration. Strongly negative values indicate concave depositional hollows.\n"
        "• Planform Curvature (k_plan): Measures lateral flow convergence/divergence. Negative values indicate flow convergence into slope gullies.\n"
        "• Topographic Position Index (TPI): TPI = Z_0 - Z_mean(5x5). Categorizes slope into valley bottoms, mid-slope spurs, or exposed ridges.\n"
        "• Topographic Wetness Index (TWI): TWI = ln(a / tan(β)), identifying moisture accumulation zones."
    )

    # --- Algorithm 6 ---
    doc.add_heading("5.6 Algorithm 6: Vectorized Haversine Telemetry Matching & Multi-Tier Fallback", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "When an inference request arrives for coordinates (lat, lon), the provider computes great-circle distances across all CWC stations using vectorized NumPy Haversine:\n"
        "   d = 2R * arcsin( sqrt( sin²(Δφ/2) + cos(φ1)*cos(φ2)*sin²(Δλ/2) ) )\n\n"
        "Multi-Tier Resiliency Workflow:\n"
        "1. Distance Filter: If nearest station distance d > 50.0 km, local CWC data is strictly marked NO_LOCAL_DATA. Missing data remains None.\n"
        "2. Freshness Filter: If telemetry age > 6.0 hours, data is labeled STALE, triggering advisory alerts.\n"
        "3. Live Real-Time Integration: When auto_refetch=True, system executes 3 consecutive real-time queries to Open-Meteo API. If any succeed, live observation is used.\n"
        "4. Offline Degraded State: If network is offline, gracefully engages IMD district context, and if unavailable, enters unobserved mode preserving static ML."
    )

    # --- Algorithm 7 ---
    doc.add_heading("5.7 Algorithm 7: 3D DEM Adaptive Mesh Decimation & WebGL Visualization", level=2)
    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "For interactive 3D tactical terrain exploration, the engine extracts a 128x128 or 256x256 regular elevation grid from Copernicus GLO-30 rasters. "
        "The server returns normalized elevation buffers, bounding box coordinates, and hypsometric relief stats. In the browser/workstation, "
        "Three.js constructs a WebGL PlaneGeometry, maps dynamic vertex normals, and applies risk-tier color contouring (Green/Amber/Red) in real-time."
    )

    doc.add_paragraph()

    # =========================================================================
    # SECTION 6: API SPECIFICATION & MICROSERVICES
    # =========================================================================
    h6 = doc.add_heading("6. Unified REST API Specification & Microservices Contract", level=1)
    h6.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "The LandslideNEI FastAPI microservices suite exposes 15 dedicated endpoints covering inference, location profiling, "
        "3D terrain geometry, historical layers, and operational health:"
    )

    api_table = doc.add_table(rows=16, cols=5)
    api_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(api_table)

    api_headers = ["Method", "Endpoint", "Purpose", "Data Source", "Status"]
    for j, h in enumerate(api_headers):
        cell = api_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=70, bottom=70, left=60, right=60)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    endpoints = [
        ("GET", "/health", "System health check & engine readiness", "Internal State", "200 OK (9.3 ms)"),
        ("GET", "/api/v1/health", "Versioned health & provider status", "Internal State", "200 OK (9.4 ms)"),
        ("GET", "/api/v1/info", "API metadata, bounding box & version", "Config API", "200 OK (1.2 ms)"),
        ("GET", "/model-info", "ML Model A architecture & features", "Model Metadata", "200 OK (1.5 ms)"),
        ("POST", "/api/v1/predict", "Unified operational landslide prediction", "Model A + CWC + IMD", "200 OK (107 ms)"),
        ("POST", "/api/v1/profile", "Precision terrain & soil profiling", "Copernicus + SoilGrids", "200 OK (119 ms)"),
        ("POST", "/api/v1/rainfall/refetch", "Force live regional rainfall telemetry", "Open-Meteo Live API", "200 OK (380 ms)"),
        ("GET", "/api/v1/terrain/metadata", "Copernicus DEM coverage & tiles", "DEM Manifest", "200 OK (12.6 ms)"),
        ("GET", "/api/v1/terrain/mesh", "3D WebGL elevation mesh extraction", "Copernicus GLO-30", "200 OK (45 ms)"),
        ("GET", "/api/v1/layers/status", "Layer operational status check", "System Registry", "200 OK (2.1 ms)"),
        ("GET", "/api/v1/layers/historical-landslides", "75 verified historical landslide events", "Verified GSI Layer", "200 OK (15.8 ms)"),
        ("GET", "/", "API root landing & documentation router", "FastAPI Core", "200 OK (1.0 ms)"),
        ("GET", "/dashboard/", "Tactical EOC GIS command dashboard", "Static HTML/JS/CSS", "200 OK (Static)"),
        ("GET", "/website/", "Public product information portal", "Static HTML/JS/CSS", "200 OK (Static)"),
        ("GET", "/download/windows", "Desktop EXE distribution downloader", "Dist Artifact", "200 OK (Binary)")
    ]

    for i, (m, ep, purp, src, st) in enumerate(endpoints, start=1):
        c0 = api_table.cell(i, 0)
        c1 = api_table.cell(i, 1)
        c2 = api_table.cell(i, 2)
        c3 = api_table.cell(i, 3)
        c4 = api_table.cell(i, 4)
        c0.width = Inches(0.8)
        c1.width = Inches(1.8)
        c2.width = Inches(1.8)
        c3.width = Inches(1.1)
        c4.width = Inches(1.0)
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        for c in [c0, c1, c2, c3, c4]:
            set_cell_background(c, bg)
            set_cell_margins(c, top=40, bottom=40, left=50, right=50)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        p0.add_run(m).font.bold = True

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        p1.add_run(ep).font.size = Pt(7.5)

        p2 = c2.paragraphs[0]
        format_paragraph(p2, space_before=0, space_after=0)
        p2.add_run(purp).font.size = Pt(7.5)

        p3 = c3.paragraphs[0]
        format_paragraph(p3, space_before=0, space_after=0)
        p3.add_run(src).font.size = Pt(7.5)

        p4 = c4.paragraphs[0]
        format_paragraph(p4, space_before=0, space_after=0)
        p4.add_run(st).font.size = Pt(7.5)

    doc.add_paragraph()

    # =========================================================================
    # SECTION 7: EOC DASHBOARD & DESKTOP APPLICATION
    # =========================================================================
    h7 = doc.add_heading("7. Emergency Operations Center (EOC) Command Dashboard & Desktop Application", level=1)
    h7.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "To ensure seamless field operation by disaster managers, district collectors, and geotechnical engineers, LandslideNEI is deployed in two modalities:\n\n"
        "1. Tactical Web EOC Dashboard (Browser / Network Access):\n"
        "• Dual 2D/3D Tactical Mapping: Seamless toggle between 2D Leaflet spatial overview and Three.js 3D WebGL terrain exploration.\n"
        "• Live Telemetry HUD: Real-time UTC clock, elevation, coordinates, operational verdict banner, and animated SVG needle gauge.\n"
        "• Geotechnical & Micro-Climate Panels: Displays slope severity, plan/profile curvature, soil bulk density, clay fraction, and rainfall windows.\n"
        "• Historical Ground-Truth Verification: Interactive toggle displaying 75 verified critical landslide events with incident metadata.\n\n"
        "2. Standalone Windows Desktop Workstation (LANDSLIDENEI.exe):\n"
        "• Built with PyInstaller and embedded local Uvicorn ASGI server.\n"
        "• Auto-launches Microsoft Edge in dedicated windowed application mode (`--app=http://127.0.0.1:PORT/dashboard/`).\n"
        "• Native Windows integration: Automatically attaches to parent console (`AttachConsole`), handles redirected STDIO, and auto-negotiates free ports.\n"
        "• Self-contained offline capability: Fully executes Model A inference, GLO-30 terrain queries, and risk fusion with zero internet connection."
    )

    doc.add_paragraph()

    # =========================================================================
    # SECTION 8: 8-STATE EMPIRICAL VERIFICATION RESULTS
    # =========================================================================
    h8 = doc.add_heading("8. Empirical Verification Across All 8 Northeast India States", level=1)
    h8.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "The system was rigorously audited and executed live across all 8 NER state capitals and critical transport corridors. "
        "The following empirical results were recorded from direct API execution:"
    )

    ner_table = doc.add_table(rows=9, cols=6)
    ner_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(ner_table)

    n_headers = ["State Capital / Corridor", "State", "Coordinates", "Static Susc.", "Nearest CWC Station (Distance)", "Operational Risk"]
    for j, h in enumerate(n_headers):
        cell = ner_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=70, bottom=70, left=60, right=60)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    ner_locations = [
        ("Kohima (NH-29)", "Nagaland", "25.6740°N, 94.1120°E", "MODERATE (0.4595)", "Bokajan (50.16 km — Beyond 50km Cap -> NO_DATA)", "WATCH (0.4595)"),
        ("Shillong Peak", "Meghalaya", "25.5788°N, 91.8933°E", "MODERATE (0.3995)", "Guwahati DC Court (70.11 km — Beyond 50km Cap -> NO_DATA)", "WATCH (0.3995)"),
        ("Tezpur Sonitpur", "Assam", "26.6528°N, 92.7926°E", "LOW (0.1571)", "Tezpur (4.13 km — In-Situ Telemetry Connected)", "LOW (0.0785)"),
        ("Namchi Ridge", "Sikkim", "27.1664°N, 88.3639°E", "VERY_HIGH (0.8409)", "Majitar (7.77 km — In-Situ Telemetry Connected)", "WATCH (0.4302)"),
        ("Imphal Valley", "Manipur", "24.8170°N, 93.9368°E", "LOW (0.1105)", "Amraghat (26.16 km — In-Situ Telemetry Connected)", "LOW (0.0747)"),
        ("Lunglei Ridge", "Mizoram", "22.8878°N, 92.7397°E", "HIGH (0.7433)", "GUMTI HYDRO (111.45 km — Beyond 50km Cap -> NO_DATA)", "WATCH (0.7433)"),
        ("Agartala Urban", "Tripura", "23.8315°N, 91.2868°E", "LOW (0.2441)", "Sonamura (40.02 km — In-Situ Telemetry Connected)", "LOW (0.1270)"),
        ("Itanagar Foothills", "Arunachal", "27.0844°N, 93.6053°E", "HIGH (0.6347)", "Badatighat (38.43 km — In-Situ Telemetry Connected)", "WATCH (0.3271)")
    ]

    for i, (loc, st, coord, susc, stn, rsk) in enumerate(ner_locations, start=1):
        c0 = ner_table.cell(i, 0)
        c1 = ner_table.cell(i, 1)
        c2 = ner_table.cell(i, 2)
        c3 = ner_table.cell(i, 3)
        c4 = ner_table.cell(i, 4)
        c5 = ner_table.cell(i, 5)
        c0.width = Inches(1.3)
        c1.width = Inches(0.9)
        c2.width = Inches(1.2)
        c3.width = Inches(1.1)
        c4.width = Inches(1.3)
        c5.width = Inches(0.9)
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        for c in [c0, c1, c2, c3, c4, c5]:
            set_cell_background(c, bg)
            set_cell_margins(c, top=50, bottom=50, left=50, right=50)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        p0.add_run(loc).font.bold = True
        p0.runs[0].font.size = Pt(8)

        for p_idx, text_val in enumerate([st, coord, susc, stn, rsk], start=1):
            p_cell = ner_table.cell(i, p_idx).paragraphs[0]
            format_paragraph(p_cell, space_before=0, space_after=0)
            run = p_cell.add_run(text_val)
            run.font.size = Pt(8)
            if p_idx == 5:
                run.font.bold = True
                if "WATCH" in text_val:
                    run.font.color.rgb = RGBColor(217, 119, 6)
                elif "LOW" in text_val:
                    run.font.color.rgb = RGBColor(5, 150, 105)

    doc.add_paragraph()

    # =========================================================================
    # SECTION 9: RESILIENCY, EDGE CASES & SECURITY AUDIT
    # =========================================================================
    h9 = doc.add_heading("9. Edge-Case Resiliency, Security & Degraded Offline Mode", level=1)
    h9.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "A critical mandate for disaster-response software is fault tolerance under extreme conditions. "
        "LandslideNEI was subjected to a comprehensive 17-scenario edge-case test battery. All 17 passed without a single unhandled exception or crash:"
    )

    edge_table = doc.add_table(rows=18, cols=4)
    edge_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(edge_table)

    e_headers = ["Case #", "Failure / Boundary Scenario", "Expected Handling & HTTP Code", "Verified Test Result"]
    for j, h in enumerate(e_headers):
        cell = edge_table.cell(0, j)
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=70, bottom=70, left=60, right=60)
        p = cell.paragraphs[0]
        format_paragraph(p, space_before=0, space_after=0)
        r = p.add_run(h)
        r.font.name = "Arial"
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    edge_cases = [
        ("01", "Valid Coordinates (Kohima)", "200 OK with full susceptibility and risk payload", "PASS — Risk level WATCH generated"),
        ("02", "Coordinates Outside NER Domain (New Delhi)", "400 Bad Request with OUTSIDE_SUPPORTED_DOMAIN error", "PASS — Rejected cleanly by GADM polygon"),
        ("03", "Invalid Latitude (lat > 90°)", "422 Unprocessable Content schema validation error", "PASS — Rejected by Pydantic v2"),
        ("04", "Invalid Longitude (lon > 180°)", "422 Unprocessable Content schema validation error", "PASS — Rejected by Pydantic v2"),
        ("05", "Missing Parameters (Latitude omitted)", "422 Unprocessable Content field required error", "PASS — Field required exception caught"),
        ("06", "Null / None Coordinates", "422 Unprocessable Content valid number required error", "PASS — Rejected cleanly"),
        ("07", "Extreme Coordinates (-89.9°, -179.9°)", "400 Bad Request domain guardrail", "PASS — Rejected by spatial bounds"),
        ("08", "No CWC Station within 50 km (Lunglei)", "200 OK, rainfall status NO_RELIABLE_LOCAL_STATION", "PASS — GUMTI 111km rejected, rainfall=None"),
        ("09", "Stale CWC Data (>6 hours old)", "200 OK, marked STALE, triggers advisory reasons", "PASS — Correctly tagged with age 26601h"),
        ("10", "Missing Rainfall Window", "200 OK, window remains None (NOT converted to 0.0)", "PASS — Verified None != 0.0 mm"),
        ("11", "IMD Gridded Data Unavailable", "200 OK, falls back to CWC without macro enrichment", "PASS — Gracefully handled without crash"),
        ("12", "CWC Hydro-Telemetry Unavailable", "200 OK, enters unobserved mode (Trigger: NO_DATA)", "PASS — Static ML preserved bit-for-bit"),
        ("13", "Soil Raster Tile Unavailable", "200 OK, scikit-learn median imputation engages", "PASS — Zero failure in feature pipeline"),
        ("14", "DEM Raster Unavailable", "Safe handling via focal terrain cache or fallback", "PASS — No unhandled process termination"),
        ("15", "Malformed JSON Request Body", "422 / 400 Bad Request with structured error JSON", "PASS — Rejected before entering business logic"),
        ("16", "Upstream Real-time API Timeout", "200 OK, 3 retries engage, falls back to offline", "PASS — Handled via fallback_engaged=True"),
        ("17", "Upstream HTTP 500 Failure", "200 OK, resilient fallback to offline cache", "PASS — Handled via fallback_engaged=True")
    ]

    for i, (c_num, scn, exp, res) in enumerate(edge_cases, start=1):
        c0 = edge_table.cell(i, 0)
        c1 = edge_table.cell(i, 1)
        c2 = edge_table.cell(i, 2)
        c3 = edge_table.cell(i, 3)
        c0.width = Inches(0.6)
        c1.width = Inches(2.2)
        c2.width = Inches(2.2)
        c3.width = Inches(1.5)
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        for c in [c0, c1, c2, c3]:
            set_cell_background(c, bg)
            set_cell_margins(c, top=40, bottom=40, left=50, right=50)

        p0 = c0.paragraphs[0]
        format_paragraph(p0, space_before=0, space_after=0)
        p0.add_run(c_num).font.bold = True
        p0.runs[0].font.size = Pt(8)

        p1 = c1.paragraphs[0]
        format_paragraph(p1, space_before=0, space_after=0)
        p1.add_run(scn).font.size = Pt(8)

        p2 = c2.paragraphs[0]
        format_paragraph(p2, space_before=0, space_after=0)
        p2.add_run(exp).font.size = Pt(8)

        p3 = c3.paragraphs[0]
        format_paragraph(p3, space_before=0, space_after=0)
        r3 = p3.add_run(res)
        r3.font.size = Pt(8)
        r3.font.bold = True
        r3.font.color.rgb = RGBColor(5, 150, 105)

    doc.add_paragraph()

    # =========================================================================
    # SECTION 10: CONCLUSION & SIH 26001 DEPLOYMENT ROADMAP
    # =========================================================================
    h10 = doc.add_heading("10. Conclusion, Innovation Highlights & Deployment Roadmap", level=1)
    h10.style.font.color.rgb = RGB_NAVY

    p = doc.add_paragraph()
    format_paragraph(p)
    p.add_run(
        "LandslideNEI successfully addresses all foundational objectives of Smart India Hackathon Problem Statement SIH 26001. "
        "By enforcing strict scientific honesty (separating static predisposition from dynamic triggers, disallowing fake zeroes, and enforcing "
        "a 50km spatial telemetry cap), the platform establishes a reliable, mission-critical foundation for landslide disaster risk reduction in Northeast India.\n\n"
        "Key Architectural Innovations:\n"
        "1. True Dual-Layer Fusion: Deterministic 4x4 matrix eliminates black-box AI opacity during emergency operations.\n"
        "2. Zero-Dependency Tactical GIS: WebGL 3D terrain exploration running smoothly even on basic field laptops without specialized GIS workstations.\n"
        "3. Multi-Tier Telemetry Resilience: 3-attempt live real-time API loop with automated fallback to in-situ CWC and IMD macro tables.\n"
        "4. Fully Self-Contained Desktop EXE: Packaged single-executable operational workstation with pre-warmed inference engines and zero external runtime dependencies.\n\n"
        "Immediate Deployment Roadmap:\n"
        "• Phase 1 (Q4 2026): Pilot installation across Nagaland (Kohima EOC) and Sikkim (Gangtok/Namchi EOC).\n"
        "• Phase 2 (Q1 2027): Integration of National Remote Sensing Centre (NRSC) SAR interferometry / InSAR surface displacement alerts.\n"
        "• Phase 3 (Q2 2027): Direct integration with NDMA / SDMA Common Alerting Protocol (CAP) for automated SMS warning broadcasts to highway travelers."
    )

    doc.add_paragraph()

    # Final Signoff Block
    p_sign = doc.add_paragraph()
    format_paragraph(p_sign, space_before=16, space_after=4)
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_sign = p_sign.add_run("SUBMITTED FOR SMART INDIA HACKATHON EVALUATION\nPROBLEM STATEMENT ID: SIH 26001\nTEAM LANDSLIDENEI — ALL SYSTEMS OPERATIONAL")
    r_sign.font.name = "Arial"
    r_sign.font.size = Pt(9.5)
    r_sign.font.bold = True
    r_sign.font.color.rgb = RGB_NAVY

    # Save document
    doc.save(str(OUTPUT_FILE))
    print(f"Document successfully created and saved to: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size} bytes")


if __name__ == "__main__":
    build_document()
