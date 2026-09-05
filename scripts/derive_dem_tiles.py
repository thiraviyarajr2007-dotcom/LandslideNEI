from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd


def tile_name(lat: float, lon: float) -> str:
    ns = f"N{math.floor(lat):02d}_00" if lat >= 0 else f"S{abs(math.ceil(lat)):02d}_00"
    ew = f"E{math.floor(lon):03d}_00" if lon >= 0 else f"W{abs(math.ceil(lon)):03d}_00"
    return f"Copernicus_DSM_COG_10_{ns}_{ew}_DEM"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--output", type=Path, default=Path("required_glo30_tiles.txt"))
    args = ap.parse_args()
    df = pd.read_csv(args.csv)
    required = sorted({tile_name(float(lat), float(lon)) for lat, lon in zip(df["latitude"], df["longitude"])})
    args.output.write_text("\n".join(required) + "\n", encoding="utf-8")
    print(f"samples={len(df)}")
    print(f"tiles={len(required)}")
    print("\n".join(required))


if __name__ == "__main__":
    main()

