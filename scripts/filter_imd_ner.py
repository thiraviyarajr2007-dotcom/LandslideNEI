import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pathlib import Path
import hashlib
import json
from datetime import datetime

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

IMD_ROOT = PROJECT_ROOT / "data" / "raw" / "imd"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "imd"

STATE_FILE = IMD_ROOT / "rainfall_statewise_daily_imd.csv"
DISTRICT_FILE = IMD_ROOT / "rainfall_districtwise_daily_imd.csv"

STATE_OUTPUT = OUTPUT_ROOT / "imd_statewise_ner.csv"
DISTRICT_OUTPUT = OUTPUT_ROOT / "imd_districtwise_ner.csv"

REPORT_FILE = OUTPUT_ROOT / "imd_ner_filter_report.json"


# ============================================================
# CANONICAL NER STATES
# ============================================================

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
    """
    Convert state names into a canonical comparison form.

    This function does NOT alter the original State column.
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    # Collapse repeated whitespace.
    value = " ".join(value.split())

    # Remove common trailing carriage-return artifacts.
    value = value.replace("\r", "").replace("\n", "")

    return value


def validate_state_column(df, source_name):
    if "State" not in df.columns:
        raise ValueError(
            f"{source_name}: required 'State' column not found."
        )


def validate_no_non_ner_rows(df, source_name):
    invalid = df.loc[
        ~df["State_Normalized"].isin(NER_STATES)
    ]

    if not invalid.empty:
        states = sorted(
            invalid["State_Normalized"]
            .dropna()
            .unique()
            .tolist()
        )

        raise RuntimeError(
            f"{source_name}: non-NER states found after filtering: "
            + ", ".join(states)
        )


# ============================================================
# FILTER ONE DATASET
# ============================================================

def filter_dataset(
    input_path: Path,
    output_path: Path,
    dataset_name: str,
):
    print()
    print("=" * 80)
    print(f"PROCESSING: {dataset_name}")
    print("=" * 80)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    # --------------------------------------------------------
    # Read raw dataset
    # --------------------------------------------------------

    df = pd.read_csv(
        input_path,
        low_memory=False,
    )

    validate_state_column(
        df,
        dataset_name,
    )

    original_rows = len(df)

    print(f"Input rows: {original_rows:,}")

    # --------------------------------------------------------
    # Create canonical comparison column.
    #
    # Original State values remain untouched.
    # --------------------------------------------------------

    df["State_Normalized"] = df["State"].map(
        normalize_state
    )

    # --------------------------------------------------------
    # Identify rows belonging to NER
    # --------------------------------------------------------

    ner_mask = df["State_Normalized"].isin(
        NER_STATES
    )

    filtered = df.loc[ner_mask].copy()

    print(
        f"NER rows: {len(filtered):,}"
    )

    # --------------------------------------------------------
    # Safety validation
    # --------------------------------------------------------

    validate_no_non_ner_rows(
        filtered,
        dataset_name,
    )

    # Missing state values should never silently enter
    # the filtered dataset.
    missing_state_rows = int(
        df["State_Normalized"].isna().sum()
    )

    if filtered["State_Normalized"].isna().any():
        raise RuntimeError(
            f"{dataset_name}: missing State values "
            "entered filtered dataset."
        )

    # --------------------------------------------------------
    # State distribution
    # --------------------------------------------------------

    rows_by_state = (
        filtered["State_Normalized"]
        .value_counts()
        .sort_index()
    )

    rows_by_state_dict = {
        state: int(count)
        for state, count in rows_by_state.items()
    }

    print("\nRows by NER state:")

    for state in sorted(NER_STATES):
        count = rows_by_state_dict.get(state, 0)

        print(
            f"  {state}: {count:,}"
        )

    # --------------------------------------------------------
    # Date inspection
    # --------------------------------------------------------

    date_columns = [
        column
        for column in filtered.columns
        if str(column).strip().lower() == "date"
    ]

    date_report = {}

    if date_columns:
        date_column = date_columns[0]

        parsed = pd.to_datetime(
            filtered[date_column],
            errors="coerce",
        )

        date_report = {
            "column": date_column,
            "parseable_rows": int(parsed.notna().sum()),
            "invalid_rows": int(parsed.isna().sum()),
            "min": (
                parsed.min().isoformat()
                if parsed.notna().any()
                else None
            ),
            "max": (
                parsed.max().isoformat()
                if parsed.notna().any()
                else None
            ),
        }

        print("\nDate coverage:")
        print(
            f"  Parseable: "
            f"{date_report['parseable_rows']:,}"
        )
        print(
            f"  Invalid  : "
            f"{date_report['invalid_rows']:,}"
        )
        print(
            f"  Range    : "
            f"{date_report['min']} -> "
            f"{date_report['max']}"
        )

    # --------------------------------------------------------
    # Duplicate validation
    # --------------------------------------------------------

    complete_duplicates = int(
        filtered.duplicated().sum()
    )

    key_columns = ["State_Normalized"]

    if "District" in filtered.columns:
        key_columns.append("District")

    if "Date" in filtered.columns:
        key_columns.append("Date")

    key_duplicates = int(
        filtered.duplicated(
            subset=key_columns,
            keep=False,
        ).sum()
    )

    print("\nDuplicate checks:")
    print(
        f"  Complete-row duplicates: "
        f"{complete_duplicates:,}"
    )
    print(
        f"  Key duplicates "
        f"({', '.join(key_columns)}): "
        f"{key_duplicates:,}"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    filtered.to_csv(
        output_path,
        index=False,
    )

    print()
    print(f"Output: {output_path}")

    return {
        "dataset": dataset_name,
        "input_file": str(
            input_path.relative_to(PROJECT_ROOT)
        ),
        "input_sha256": sha256(input_path),
        "output_file": str(
            output_path.relative_to(PROJECT_ROOT)
        ),
        "output_sha256": sha256(output_path),
        "input_rows": original_rows,
        "output_rows": len(filtered),
        "rows_removed": (
            original_rows - len(filtered)
        ),
        "missing_state_rows_in_input": missing_state_rows,
        "rows_by_state": rows_by_state_dict,
        "date": date_report,
        "complete_row_duplicates": complete_duplicates,
        "key_columns": key_columns,
        "key_duplicate_rows": key_duplicates,
        "states_present_after_filter": sorted(
            filtered["State_Normalized"]
            .dropna()
            .unique()
            .tolist()
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("IMD RAINFALL — NER FILTERING PIPELINE")
    print("=" * 80)

    print("\nTarget states:")

    for state in sorted(NER_STATES):
        print(f"  - {state}")

    state_report = filter_dataset(
        STATE_FILE,
        STATE_OUTPUT,
        "Statewise IMD",
    )

    district_report = filter_dataset(
        DISTRICT_FILE,
        DISTRICT_OUTPUT,
        "Districtwise IMD",
    )

    # --------------------------------------------------------
    # Final cross-dataset validation
    # --------------------------------------------------------

    state_states = set(
        state_report["states_present_after_filter"]
    )

    district_states = set(
        district_report["states_present_after_filter"]
    )

    if state_states != NER_STATES:
        raise RuntimeError(
            "Statewise output does not contain exactly "
            "the expected NER states."
        )

    if district_states != NER_STATES:
        raise RuntimeError(
            "Districtwise output does not contain exactly "
            "the expected NER states."
        )

    report = {
        "generated_at_utc": (
            datetime.utcnow().isoformat() + "Z"
        ),
        "ner_states": sorted(NER_STATES),
        "statewise": state_report,
        "districtwise": district_report,
        "raw_files_modified": False,
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

    print()
    print("=" * 80)
    print("NER FILTERING COMPLETE")
    print("=" * 80)

    print(
        f"Statewise output  : {STATE_OUTPUT}"
    )

    print(
        f"Districtwise output: {DISTRICT_OUTPUT}"
    )

    print(
        f"Report             : {REPORT_FILE}"
    )

    print()
    print("Raw India-wide files were NOT modified.")
    print("=" * 80)


if __name__ == "__main__":
    main()
