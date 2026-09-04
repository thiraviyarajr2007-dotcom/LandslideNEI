import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
import hashlib
import json

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

IMD_ROOT = PROJECT_ROOT / "data" / "raw" / "imd"

STATE_FILE = IMD_ROOT / "rainfall_statewise_daily_imd.csv"
DISTRICT_FILE = IMD_ROOT / "rainfall_districtwise_daily_imd.csv"

REPORT_FILE = PROJECT_ROOT / "data" / "imd_rainfall_inspection.json"


# Canonical Northeast India states used by this project.
NER_STATES = {
    "ARUNACHAL PRADESH",
    "ASSAM",
    "MANIPUR",
    "MEGHALAYA",
    "MIZORAM",
    "NAGALAND",
    "SIKKIM",
    "TRIPURA",
}


# ============================================================
# HELPERS
# ============================================================

def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_state(value):
    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    # Normalize repeated whitespace.
    value = " ".join(value.split())

    return value


def inspect_basic(df, path):
    print("\n" + "=" * 80)
    print(f"FILE: {path.relative_to(PROJECT_ROOT)}")
    print("=" * 80)

    print(f"Rows    : {len(df):,}")
    print(f"Columns : {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nData types:")
    for column, dtype in df.dtypes.items():
        print(f"  {column}: {dtype}")

    print("\nMissing values:")
    missing = df.isna().sum()

    if missing.sum() == 0:
        print("  None")
    else:
        for column, count in missing.items():
            if count:
                print(f"  {column}: {count:,}")

    print("\nDuplicate complete rows:")
    print(f"  {df.duplicated().sum():,}")

    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))


# ============================================================
# STATEWISE INSPECTION
# ============================================================

def inspect_statewise():
    if not STATE_FILE.exists():
        raise FileNotFoundError(
            f"Statewise IMD file not found: {STATE_FILE}"
        )

    print("\nLoading statewise IMD data...")
    df = pd.read_csv(
        STATE_FILE,
        low_memory=False,
    )

    inspect_basic(df, STATE_FILE)

    result = {
        "file": str(
            STATE_FILE.relative_to(PROJECT_ROOT)
        ),
        "size_bytes": STATE_FILE.stat().st_size,
        "sha256": sha256(STATE_FILE),
        "rows": len(df),
        "columns": df.columns.tolist(),
    }

    # --------------------------------------------------------
    # State column
    # --------------------------------------------------------

    state_candidates = [
        column
        for column in df.columns
        if str(column).strip().lower() == "state"
    ]

    print("\nState column:")
    print(f"  Candidates: {state_candidates}")

    if not state_candidates:
        result["error"] = "No State column found."
        return result

    state_column = state_candidates[0]

    normalized_state = df[state_column].map(
        normalize_state
    )

    unique_states = sorted(
        normalized_state.dropna().unique().tolist()
    )

    ner_present = sorted(
        set(unique_states) & NER_STATES
    )

    ner_missing = sorted(
        NER_STATES - set(unique_states)
    )

    result["state_column"] = state_column
    result["unique_states"] = unique_states
    result["ner_states_present"] = ner_present
    result["ner_states_missing"] = ner_missing

    print("\nUnique states:")
    print(f"  {len(unique_states)}")

    for state in unique_states:
        print(f"  - {state}")

    print("\nNER states found:")
    for state in ner_present:
        print(f"  [+] {state}")

    print("\nNER states missing:")
    for state in ner_missing:
        print(f"  [-] {state}")

    # --------------------------------------------------------
    # NER-only inspection
    # --------------------------------------------------------

    ner_mask = normalized_state.isin(NER_STATES)

    ner_df = df.loc[ner_mask].copy()
    ner_df["_normalized_state"] = normalized_state.loc[ner_mask]

    result["ner_rows"] = len(ner_df)

    print("\nNER-only rows:")
    print(f"  {len(ner_df):,}")

    print("\nRows by NER state:")
    state_counts = (
        ner_df["_normalized_state"]
        .value_counts()
        .sort_index()
    )

    result["ner_rows_by_state"] = {
        state: int(count)
        for state, count in state_counts.items()
    }

    for state, count in state_counts.items():
        print(f"  {state}: {count:,}")

    # --------------------------------------------------------
    # Date candidates
    # --------------------------------------------------------

    date_candidates = [
        column
        for column in df.columns
        if "date" in str(column).lower()
        or "time" in str(column).lower()
    ]

    result["date_candidates"] = date_candidates

    print("\nDate/time candidates:")

    for column in date_candidates:
        parsed = pd.to_datetime(
            ner_df[column],
            errors="coerce",
            dayfirst=True,
        )

        valid = parsed.notna()

        print(f"  - {column}")
        print(
            f"      parseable: "
            f"{valid.sum():,}/{len(parsed):,}"
        )

        if valid.any():
            print(
                f"      range: "
                f"{parsed.min()} -> {parsed.max()}"
            )

    # --------------------------------------------------------
    # Rainfall candidates
    # --------------------------------------------------------

    rainfall_candidates = [
        column
        for column in df.columns
        if any(
            keyword in str(column).lower()
            for keyword in [
                "actual",
                "rainfall",
                "rain",
                "precip",
            ]
        )
    ]

    result["rainfall_candidates"] = rainfall_candidates

    print("\nRainfall-related candidates:")

    for column in rainfall_candidates:
        numeric = pd.to_numeric(
            ner_df[column],
            errors="coerce",
        )

        print(f"  - {column}")
        print(
            f"      numeric values: "
            f"{numeric.notna().sum():,}"
        )

        if numeric.notna().any():
            print(
                f"      min: {numeric.min()}"
            )
            print(
                f"      max: {numeric.max()}"
            )

    return result


# ============================================================
# DISTRICTWISE INSPECTION
# ============================================================

def inspect_districtwise():
    if not DISTRICT_FILE.exists():
        raise FileNotFoundError(
            f"Districtwise IMD file not found: {DISTRICT_FILE}"
        )

    print("\nLoading districtwise IMD data...")
    df = pd.read_csv(
        DISTRICT_FILE,
        low_memory=False,
    )

    inspect_basic(df, DISTRICT_FILE)

    result = {
        "file": str(
            DISTRICT_FILE.relative_to(PROJECT_ROOT)
        ),
        "size_bytes": DISTRICT_FILE.stat().st_size,
        "sha256": sha256(DISTRICT_FILE),
        "rows": len(df),
        "columns": df.columns.tolist(),
    }

    # --------------------------------------------------------
    # State column
    # --------------------------------------------------------

    state_candidates = [
        column
        for column in df.columns
        if str(column).strip().lower() == "state"
    ]

    print("\nState column:")
    print(f"  Candidates: {state_candidates}")

    if not state_candidates:
        result["error"] = "No State column found."
        return result

    state_column = state_candidates[0]

    normalized_state = df[state_column].map(
        normalize_state
    )

    unique_states = sorted(
        normalized_state.dropna().unique().tolist()
    )

    ner_present = sorted(
        set(unique_states) & NER_STATES
    )

    ner_missing = sorted(
        NER_STATES - set(unique_states)
    )

    result["state_column"] = state_column
    result["unique_states"] = unique_states
    result["ner_states_present"] = ner_present
    result["ner_states_missing"] = ner_missing

    print("\nUnique states:")
    print(f"  {len(unique_states)}")

    for state in unique_states:
        print(f"  - {state}")

    print("\nNER states found:")
    for state in ner_present:
        print(f"  [+] {state}")

    print("\nNER states missing:")
    for state in ner_missing:
        print(f"  [-] {state}")

    # --------------------------------------------------------
    # NER-only data
    # --------------------------------------------------------

    ner_mask = normalized_state.isin(NER_STATES)

    ner_df = df.loc[ner_mask].copy()
    ner_df["_normalized_state"] = normalized_state.loc[ner_mask]

    result["ner_rows"] = len(ner_df)

    print("\nNER-only rows:")
    print(f"  {len(ner_df):,}")

    print("\nRows by NER state:")
    state_counts = (
        ner_df["_normalized_state"]
        .value_counts()
        .sort_index()
    )

    result["ner_rows_by_state"] = {
        state: int(count)
        for state, count in state_counts.items()
    }

    for state, count in state_counts.items():
        print(f"  {state}: {count:,}")

    # --------------------------------------------------------
    # District column
    # --------------------------------------------------------

    district_candidates = [
        column
        for column in df.columns
        if str(column).strip().lower() == "district"
    ]

    print("\nDistrict column:")
    print(f"  Candidates: {district_candidates}")

    if district_candidates:
        district_column = district_candidates[0]

        district_counts = (
            ner_df.groupby("_normalized_state")[
                district_column
            ]
            .nunique(dropna=True)
            .sort_index()
        )

        result["district_column"] = district_column
        result["districts_by_state"] = {
            state: int(count)
            for state, count in district_counts.items()
        }

        print("\nUnique districts by NER state:")

        for state, count in district_counts.items():
            print(f"  {state}: {count:,}")

    # --------------------------------------------------------
    # Date candidates
    # --------------------------------------------------------

    date_candidates = [
        column
        for column in df.columns
        if "date" in str(column).lower()
        or "time" in str(column).lower()
    ]

    result["date_candidates"] = date_candidates

    print("\nDate/time candidates:")

    for column in date_candidates:
        parsed = pd.to_datetime(
            ner_df[column],
            errors="coerce",
            dayfirst=True,
        )

        valid = parsed.notna()

        print(f"  - {column}")
        print(
            f"      parseable: "
            f"{valid.sum():,}/{len(parsed):,}"
        )

        if valid.any():
            print(
                f"      range: "
                f"{parsed.min()} -> {parsed.max()}"
            )

    # --------------------------------------------------------
    # Rainfall candidates
    # --------------------------------------------------------

    rainfall_candidates = [
        column
        for column in df.columns
        if any(
            keyword in str(column).lower()
            for keyword in [
                "actual",
                "rainfall",
                "rain",
                "precip",
            ]
        )
    ]

    result["rainfall_candidates"] = rainfall_candidates

    print("\nRainfall-related candidates:")

    for column in rainfall_candidates:
        numeric = pd.to_numeric(
            ner_df[column],
            errors="coerce",
        )

        print(f"  - {column}")
        print(
            f"      numeric values: "
            f"{numeric.notna().sum():,}"
        )

        if numeric.notna().any():
            print(
                f"      min: {numeric.min()}"
            )
            print(
                f"      max: {numeric.max()}"
            )

    # --------------------------------------------------------
    # State + district + date duplicate audit
    # --------------------------------------------------------

    if (
        state_column
        and district_candidates
        and date_candidates
    ):
        district_column = district_candidates[0]

        date_column = date_candidates[0]

        duplicate_mask = ner_df.duplicated(
            subset=[
                "_normalized_state",
                district_column,
                date_column,
            ],
            keep=False,
        )

        duplicate_rows = ner_df.loc[
            duplicate_mask
        ]

        result["state_district_date_duplicate_rows"] = (
            len(duplicate_rows)
        )

        print(
            "\nDuplicate "
            "state + district + date rows:"
        )
        print(f"  {len(duplicate_rows):,}")

    return result


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("IMD RAINFALL -- NER INSPECTION")
    print("=" * 80)

    print("\nTarget NER states:")

    for state in sorted(NER_STATES):
        print(f"  - {state}")

    report = {
        "ner_states": sorted(NER_STATES),
        "statewise": None,
        "districtwise": None,
    }

    # Statewise.
    try:
        report["statewise"] = inspect_statewise()
    except Exception as exc:
        print(f"\nSTATEWISE ERROR: {exc}")
        report["statewise"] = {
            "error": str(exc)
        }

    # Districtwise.
    try:
        report["districtwise"] = inspect_districtwise()
    except Exception as exc:
        print(f"\nDISTRICTWISE ERROR: {exc}")
        report["districtwise"] = {
            "error": str(exc)
        }

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("IMD INSPECTION COMPLETE")
    print("=" * 80)
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
