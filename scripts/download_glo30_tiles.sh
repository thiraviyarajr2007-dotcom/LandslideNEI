#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
base="$repo_root/data/raw/dem/copernicus_glo30"
tile_file="$base/downloads/required_glo30_tiles.txt"
out_dir="$base/downloads"
mkdir -p "$out_dir"

while IFS= read -r tile; do
  [[ -z "$tile" ]] && continue
  stem="${tile#Copernicus_DSM_COG_10_}"
  key="$tile/Copernicus_DSM_COG_10_${stem}.tif"
  out="$out_dir/Copernicus_DSM_COG_10_${stem}_DEM.tif"
  echo "Downloading $tile"
  curl --fail --location --retry 5 --retry-delay 3 --continue-at - \
    "https://copernicus-dem-30m.s3.amazonaws.com/$key" -o "$out"
done < "$tile_file"

find "$out_dir" -maxdepth 1 -type f -name '*_DEM.tif' -printf '%f\t%s bytes\n' | sort
