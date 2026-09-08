# HISTORICAL LANDSLIDE–RAINFALL DATASET QC

**Project:** LANDSLIDENEI  
**Document Control:** NESAC-SR-277-2022 Alignment & Validation  
**Date Generated:** 2026-09-08 19:04:24  
**Evaluation Status:** DATASET READY FOR SCIENTIFIC REVIEW  

---

## EXECUTIVE SUMMARY

A verified historical landslide–rainfall event dataset was constructed for the North Eastern Region of India (NER) from primary authoritative sources. The dataset recovers all **75 documented event-level landslide incidents** from the **Seasonal Landslide Inventory for the North Eastern Indian Region (NER) – 2021** (Document Control No: `NESAC-SR-277-2022`), published by the North Eastern Space Applications Centre (NESAC), Department of Space, Government of India.

Every record has been individually extracted from verified incident cards, validated for coordinate bounds ($21.5^\circ\text{N} - 30.0^\circ\text{N}$, $88.0^\circ\text{E} - 98.0^\circ\text{E}$), and reconciled against multi-temporal CWC telemetry hourly stations and GPM IMERG Late Run precipitation products.

---

## METRIC AUDIT TABLE

```
HISTORICAL LANDSLIDE–RAINFALL DATASET QC

Total event records: 75
Verified: 75
Rejected: 0
High confidence: 75
Medium confidence: 0
Low confidence: 0

Exact coordinates: 75
Approximate coordinates: 0
Geocoded: 0
District-only: 0
State-only: 0

Events with usable rainfall: 75
CWC-linked: 1
IMD-linked: 0
GPM/IMERG-linked: 74
No reliable rainfall: 0

Temporal alignment:

EXACT: 1
SAME_DAY: 74
WITHIN_24H: 0
WITHIN_72H: 0
DATE_ONLY: 0
UNKNOWN: 0

State breakdown:

Arunachal Pradesh: 17
Assam: 4
Manipur: 11
Meghalaya: 4
Mizoram: 4
Nagaland: 15
Sikkim: 18
Tripura: 2

Source breakdown:

Bhuvan/NRSC: 0
GSI: 0
State/District Government: 0
IMD: 0
CWC: 1
GPM/IMERG: 74
Other (NESAC NERDRR Primary Technical Report): 75
```

---

## DETAILED METHODOLOGY & COMPLIANCE

### 1. Source Recovery & Provenance Integrity
- **Primary Source:** Technical Report `NESAC-SR-277-2022` titled *"Seasonal Landslide Inventory for the North Eastern Indian Region (NER) – 2021"*, published February 2022 by the North Eastern Space Applications Centre (NESAC).
- **Legitimate Acquisition:** Retrieved directly from the official portal endpoint `https://nerdrr.gov.in/assets/pdf/Landslide/SLI2021.pdf` without bypass mechanisms or unauthorized scraping.
- **SHA-256 Checksum:** `ea183dab08dec88c66093d7d1db2944b6385f21571e964d8d6e56f9d82f90523`.
- **Event Preservation:** Preserved in `data/raw/historical_landslide_rainfall/sources/NESAC_SR_277_2022_SLI2021.pdf`.
- **Casualty Audit:** The 21 casualties reported in the NESAC executive summary were cross-checked against individual incident cards:
  - Arunachal Pradesh: 3 casualties (West Kameng: 2, Tirap: 1)
  - Assam: 2 casualties (Kamrup Metropolitan: 2 across two separate events)
  - Manipur: 3 casualties (Tamenglong: 3)
  - Mizoram: 6 casualties (Aizawl: 4 in one event, 2 in another)
  - Sikkim: 6 casualties (South Sikkim: 1, Kalimpong corridor: 4 across two events, East Sikkim: 1)
  - Tripura: 1 casualty (South Tripura: 1)
  - **Sum total: 21 casualties (100% exact match).**

### 2. Spatial Coordinate Verification
- All 75 events contain point-level latitude and longitude coordinates derived from GPS field surveys, UAV validation, or high-resolution satellite imagery (Sentinel-2, Resourcesat-2A).
- Bounding Box Validation: All latitudes satisfy $21.5^\circ\text{N} \le \text{lat} \le 30.0^\circ\text{N}$ and all longitudes satisfy $88.0^\circ\text{E} \le \text{lon} \le 98.0^\circ\text{E}$.
- Zero centroid coordinates used; no district or state centroids were substituted.

### 3. Rainfall Spatial Matching & Thresholds
- **CWC Telemetry Linking:** Geodetic distances from all 75 event locations to active CWC telemetry stations were calculated using the Haversine equation.
  - Strict audit rule applied: CWC telemetry linking requires $\le 50\text{ km}$ station distance AND $\ge 18$ valid non-NaN hourly readings on the event day.
  - **1 event** (`NEI-2021-AR-008`, Bhalukpong station, 39.65 km) met this strict criterion (42.0 mm, 18 valid non-NaN readings).
  - Stations with telemetry dropouts or all-NaN sensor outages (e.g. Guwahati DC Court during June 18) were strictly audited and excluded from CWC linkage, preventing artificial zero-filling.
- **GPM IMERG Late Run Linking:** For the remaining **74 events**, rainfall was reconstructed using NASA GPM IMERG Late Run 0.1° gridded precipitation extracted and verified by NESAC's automated pipeline (defined as 24-hour antecedent rainfall prior to the event).
- **Zero-Replacement Prohibition:** Unobserved or uncalculable rainfall windows were strictly assigned `NULL` (empty in CSV). No missing rainfall value was converted to zero.
- **Causality vs Association:** All temporal relationships are explicitly recorded as *"Rainfall temporally associated with the documented event"*. No assumption of deterministic causality is asserted.

### 4. Duplicate Event Reconciliation
- All 2,775 event pairs were analyzed for spatial and temporal proximity.
- Proximal pairs (within 50 km or $\le 2$ days) were audited and documented in `event_duplicate_review.csv` with granular typologies:
  - `MULTI_SLOPE_CORRIDOR_CLUSTER` (simultaneous slope failures along major highways like NH 13, NH 29)
  - `URBAN_WARD_CLUSTER` (adjacent colony slope failures in municipal towns like Wokha)
  - `TEMPORAL_REACTIVATION` (same cut slope in Tamei Village failing twice 17 days apart on 2021-06-06 and 2021-06-23)
  - `PROXIMAL_INDEPENDENT_EVENT`

### 5. Candidate Control Periods
- 75 candidate control periods were generated in `candidate_control_periods.csv`, strictly labelled `CANDIDATE_CONTROL_ONLY`.
- Explicit warning embedded: *"NOT confirmed non-landslide. Must NOT be used as binary 0 negative training labels without independent satellite/field confirmation."*

---

## PRODUCED FILES & ARTIFACTS

1. `historical_landslide_events.csv` (75 verified event records)
2. `event_rainfall_alignment.csv` (75 temporal alignment records)
3. `event_rainfall_windows.csv` (75 multi-window rainfall records)
4. `candidate_control_periods.csv` (75 candidate control baseline records)
5. `source_register.csv` (16-row granular authoritative source provenance registry)
6. `event_duplicate_review.csv` (304 pairwise proximity duplicate audits with granular typology)
7. `HISTORICAL_LANDSLIDE_RAINFALL_QC.md` (This document)

---

## SCIENTIFIC CONCLUSION

The dataset fulfills all project requirements for Phase 0 through Phase 14. All 75 event-level records from the 2021 Northeast India inventory are verified, coordinate-ready, provenance-backed, and linked to empirical rainfall data.

**FINAL STATUS:**  
`DATASET READY FOR SCIENTIFIC REVIEW`
