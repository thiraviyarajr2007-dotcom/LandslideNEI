# Historical Landslide Rainfall Distribution & Threshold Audit

**Project:** LANDSLIDENEI  
**Evaluation Scope:** 75 Verified Historical Landslide Events (NESAC/NERDRR SLI 2021)  
**Status:** SCIENTIFIC AUDIT COMPLETED  
**Document Classification:** Operational Intelligence & Geotechnical Verification  

---

## 1. Executive Summary

This audit evaluates the statistical distribution of antecedent rainfall across all 75 verified landslide events from the **Seasonal Landslide Inventory for the North Eastern Indian Region (NER) – 2021** (`NESAC-SR-277-2022`).

In accordance with scientific integrity guidelines:
- **No model retraining was conducted.**
- **No missing rainfall values were replaced with zeros.**
- **Sub-daily windows are preserved as NULL.**
- **Candidate control periods are maintained as `CANDIDATE_CONTROL_ONLY` rather than assumed true negatives.**

The primary finding is that **74 of the 75 events rely on NASA GPM IMERG Late Run 24-hour antecedent rainfall**, while only **1 event (`NEI-2021-AR-008` at Bhalukpong) had verified local CWC hourly telemetry** ($\le 50\text{ km}$, $\ge 18$ valid hourly readings).

---

## 2. Multi-Window Temporal Availability Audit

| Rainfall Window | Valid Count | Missing / NULL Count | Availability (%) | Primary Data Source |
| :--- | :---: | :---: | :---: | :--- |
| **1-Hour (1h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **3-Hour (3h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **6-Hour (6h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **12-Hour (12h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **24-Hour (24h)** | **75** | **0** | **100.0%** | **GPM IMERG Late Run (74) + CWC (1)** |
| **48-Hour (48h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **72-Hour (72h)** | 1 | 74 | 1.33% | CWC Telemetry (`Bhalukpong`) |
| **7-Day (7d)** | 0 | 75 | 0.0% | CWC Telemetry (`Bhalukpong`) |

> **Key Finding:** Sub-daily precipitation records cannot be assumed or interpolated across the region without severe sensor hallucination. Sub-daily intensity-duration (I-D) thresholds must remain tied solely to verified real-time CWC stations when within the 50 km distance cap.

---

## 3. 24-Hour Antecedent Rainfall Distribution

Analysis across all $N = 75$ events ($mm$):

| Statistic | Value (mm) | Description |
| :--- | :---: | :--- |
| **Sample Size (N)** | **75** | Complete coordinate-ready verified inventory |
| **Minimum** | **0.0 mm** | `NEI-2021-AR-017` (Arunachal Pradesh, high crest rock fall) |
| **25th Percentile (Q1)** | **6.76 mm** | Lower quartile |
| **Median (Q2)** | **33.11 mm** | Median event precipitation across Northeast India |
| **Mean** | **46.55 mm** | Arithmetic mean (standard deviation: $\pm48.9$ mm) |
| **75th Percentile (Q3)** | **67.03 mm** | Upper quartile |
| **90th Percentile** | **103.64 mm** | Severe precipitation envelope |
| **Maximum** | **203.52 mm** | `NEI-2021-MZ-003` (Aizawl, Mizoram, extreme monsoon deluge) |

### State-Level Breakdown

| State | Event Count | Mean 24h (mm) | Median 24h (mm) | Min 24h (mm) | Max 24h (mm) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Arunachal Pradesh** | 17 | 42.89 | 42.0 | 0.0 | 150.77 |
| **Assam** | 4 | 45.13 | 29.66 | 0.01 | 121.19 |
| **Manipur** | 11 | 25.26 | 10.34 | 0.0 | 101.29 |
| **Meghalaya** | 4 | 99.52 | 98.82 | 0.28 | 200.13 |
| **Mizoram** | 4 | 60.68 | 15.97 | 7.24 | 203.52 |
| **Nagaland** | 15 | 32.23 | 37.74 | 0.0 | 65.4 |
| **Sikkim** | 18 | 56.81 | 41.81 | 3.3 | 198.11 |
| **Tripura** | 2 | 78.38 | 78.38 | 78.38 | 78.38 |

---

## 4. Evaluation of Existing Operational Thresholds

Current operational thresholds in `config/risk_thresholds.json`:
- **24-Hour WATCH Threshold:** $\ge 50.0\text{ mm}$
- **24-Hour HIGH Threshold:** $\ge 100.0\text{ mm}$

### Trigger Rate Analysis

| Operational Status | Criteria | Count | Percentage |
| :--- | :--- | :---: | :---: |
| **HIGH Triggered** | $R_{24h} \ge 100.0\text{ mm}$ | **9** | **12.0%** |
| **WATCH Triggered** | $50.0\text{ mm} \le R_{24h} < 100.0\text{ mm}$ | **21** | **28.0%** |
| **Total Dynamic Triggers** | $R_{24h} \ge 50.0\text{ mm}$ | **30** | **40.0%** |
| **Below Operational Threshold** | $R_{24h} < 50.0\text{ mm}$ | **45** | **60.0%** |

### Scientific Interpretation & Calibration Assessment

1. **High Trigger Sensitivity:**
   - **40.0%** of all documented 2021 landslide events occurred under rainfall that actively breaches either the WATCH or HIGH threshold.
   - This validates that the existing baseline thresholds ($50\text{ mm}$ and $100\text{ mm}$) are in the realistic physical operating range for monsoon slope triggering in Northeast India.

2. **Observation of Events Below Threshold (60.0%):**
   - The dataset indicates that 45 events (60.0%) were accompanied by $< 50\text{ mm}$ of GPM 24-hour rainfall.
   - The distribution indicates that many documented events were not accompanied by $\ge 50\text{ mm}$ of GPM 24-hour rainfall. Further investigation is required to distinguish antecedent rainfall, terrain/anthropogenic factors, and satellite rainfall uncertainty.
   - In particular, satellite-derived GPM IMERG 0.1° spatial aggregations may smooth out localized orographic precipitation, and slope stability may be influenced by localized toe cuts or multi-week antecedent moisture saturation. Event-specific geotechnical and high-resolution ground telemetry records are required before asserting causal failure mechanisms.

3. **Recommendation on Threshold Calibration:**
   - **Do NOT globally lower the 24h threshold below 50 mm.** Lowering the regional threshold would drastically increase false alarms across low-slope and urban areas during ordinary monsoon days.
   - **Preserve the Multi-Factor Operational Risk Fusion Architecture:** The static susceptibility model (Model A) correctly assigns HIGH susceptibility to steep cut slopes even when current rainfall is low, allowing the operational synthesis to output WATCH or MODERATE rather than falsely declaring the slope safe.
   - Future calibration should incorporate state-specific orographic multipliers rather than perturbing the core regional thresholds.

---

## 5. Architectural Compliance

- **Dataset Provenance:** Preserved in `historical_landslide_events.csv` (SHA-256 verified).
- **Zero Hallucination:** No synthetic hourly readings generated for the 74 GPM events.
- **Model Integrity:** Static Susceptibility Model A untouched.
- **Dashboard Synchronization:** Historical event markers connected to 3D EOC viewer via `/api/v1/layers/historical-landslides`.
