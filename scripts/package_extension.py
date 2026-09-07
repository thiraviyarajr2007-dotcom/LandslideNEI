"""
Package LandslideNEI Chrome/Edge Browser Extension into Distributable Zip Archive
=================================================================================
Validates Manifest V3 specifications and bundles extension/ into dist/
"""
import json
from pathlib import Path
import zipfile


def package_extension() -> Path:
    root = Path(__file__).resolve().parents[1]
    ext_dir = root / "extension"
    dist_dir = root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = ext_dir / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Missing extension manifest: {manifest_file}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Basic validations
    if manifest.get("manifest_version") != 3:
        raise ValueError("Extension must be Manifest V3")

    version = manifest.get("version", "1.0.0")
    name = manifest.get("name", "LandslideNEI")
    zip_name = f"LandslideNEI_Chrome_Extension_v{version}.zip"
    zip_path = dist_dir / zip_name

    # Validate essential files
    required_files = [
        "manifest.json",
        "background.js",
        "icons/icon16.png",
        "icons/icon32.png",
        "icons/icon48.png",
        "icons/icon128.png",
        "popup/popup.html",
        "popup/popup.css",
        "popup/popup.js",
        "sidepanel/sidepanel.html",
        "sidepanel/sidepanel.js",
    ]

    for rel_path in required_files:
        fpath = ext_dir / rel_path
        if not fpath.exists():
            raise FileNotFoundError(f"Missing required extension asset: {fpath}")

    # Build ZIP archive
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in ext_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".zip"):
                arcname = file_path.relative_to(ext_dir)
                zipf.write(file_path, arcname)
                file_count += 1

    size_kb = zip_path.stat().st_size / 1024
    print(f"[LandslideNEI] Successfully packaged extension '{name}' v{version}")
    print(f"               Target: {zip_path}")
    print(f"               Files: {file_count} | Size: {size_kb:.1f} KB")

    return zip_path


if __name__ == "__main__":
    package_extension()
