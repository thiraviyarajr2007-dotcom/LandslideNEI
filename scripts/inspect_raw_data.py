from pathlib import Path
import hashlib
import pandas as pd


ROOT = Path("data/raw")


def file_hash(path):
    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def inspect_csv(path):
    print("\n" + "=" * 90)
    print(f"FILE: {path}")
    print(f"SIZE: {path.stat().st_size:,} bytes")

    try:
        df = pd.read_csv(path)

        print(f"ROWS: {len(df):,}")
        print(f"COLUMNS: {len(df.columns)}")

        print("\nCOLUMN NAMES:")
        for column in df.columns:
            print(f"  - {column}")

        print("\nDATA TYPES:")
        print(df.dtypes.to_string())

        print("\nMISSING VALUES:")
        missing = df.isna().sum()
        print(missing[missing > 0].to_string() if missing.any() else "  None")

        print("\nDUPLICATE ROWS:")
        print(f"  {df.duplicated().sum():,}")

        print("\nFIRST 3 ROWS:")
        print(df.head(3).to_string(index=False))

        print("\nLAST 3 ROWS:")
        print(df.tail(3).to_string(index=False))

    except Exception as e:
        print(f"ERROR: {e}")


def main():
    csv_files = sorted(ROOT.rglob("*.csv"))

    print(f"Found {len(csv_files)} CSV files.")

    for path in csv_files:
        inspect_csv(path)

    print("\n" + "=" * 90)
    print("SHA256 HASHES")
    print("=" * 90)

    for path in csv_files:
        try:
            print(f"{file_hash(path)}  {path}")
        except Exception as e:
            print(f"ERROR: {path} -> {e}")


if __name__ == "__main__":
    main()
