"""
LANDSLIDENEI - Desktop Application Build Script (Phase 8N)
=========================================================
Builds a standalone, offline Windows desktop application executable using PyInstaller.
Packages Python runtime, FastAPI risk inference engine, GIS dashboard, ML pipeline,
and regional boundary/rainfall datasets into dist/LANDSLIDENEI/.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def clean_build_artifacts():
    """Remove previous build and dist directories."""
    print("[1/5] Cleaning previous build artifacts...")
    for folder in ["build", "dist/LANDSLIDENEI"]:
        p = PROJECT_ROOT / folder
        if p.exists():
            print(f"  Removing {p}...")
            shutil.rmtree(p, ignore_errors=True)

def verify_source_assets():
    """Verify all critical runtime dependencies and model files exist."""
    print("[2/5] Verifying source assets...")
    
    # Auto-seed CWC features if full dataset is missing (e.g. CI or fresh git clone)
    cwc_target = PROJECT_ROOT / "data" / "processed" / "cwc_rainfall_features.csv"
    cwc_seed = PROJECT_ROOT / "data" / "processed" / "cwc_rainfall_stations_seed.csv"
    if not cwc_target.exists() and cwc_seed.exists():
        cwc_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cwc_seed, cwc_target)
        print(f"  [Auto-seeded] {cwc_target.name} from {cwc_seed.name}")

    required = [
        PROJECT_ROOT / "desktop_app.py",
        PROJECT_ROOT / "model" / "static_lsm_pipeline.joblib",
        PROJECT_ROOT / "model" / "static_lsm_metadata.json",
        PROJECT_ROOT / "config" / "risk_thresholds.json",
        PROJECT_ROOT / "config" / "api.json",
        PROJECT_ROOT / "data" / "inspection" / "landslide_validation" / "gadm41_IND_1.json",
        PROJECT_ROOT / "data" / "processed" / "cwc_rainfall_features.csv",
        PROJECT_ROOT / "dashboard" / "index.html",
        PROJECT_ROOT / "website" / "index.html",
        PROJECT_ROOT / "assets" / "icon.ico",
    ]
    for p in required:
        if not p.exists():
            raise FileNotFoundError(f"Missing required asset for packaging: {p}")
        print(f"  [OK] {p.relative_to(PROJECT_ROOT)}")

def run_pyinstaller():
    """Execute PyInstaller to compile desktop_app.py."""
    print("[3/5] Running PyInstaller compilation...")
    
    icon_path = str(PROJECT_ROOT / "assets" / "icon.ico")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "LANDSLIDENEI",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}",
        # Data bundles
        f"--add-data={PROJECT_ROOT / 'dashboard'};dashboard",
        f"--add-data={PROJECT_ROOT / 'website'};website",
        f"--add-data={PROJECT_ROOT / 'config'};config",
        f"--add-data={PROJECT_ROOT / 'model'};model",
        f"--add-data={PROJECT_ROOT / 'data' / 'inspection' / 'landslide_validation'};data/inspection/landslide_validation",
        f"--add-data={PROJECT_ROOT / 'data' / 'processed'};data/processed",
        f"--add-data={PROJECT_ROOT / 'assets'};assets",
        # Source code
        f"--add-data={PROJECT_ROOT / 'api'};api",
        f"--add-data={PROJECT_ROOT / 'src'};src",
        # Hidden imports
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "fastapi",
        "--hidden-import", "fastapi.staticfiles",
        "--hidden-import", "starlette",
        "--hidden-import", "starlette.staticfiles",
        "--hidden-import", "starlette.responses",
        "--hidden-import", "starlette.routing",
        "--hidden-import", "pydantic",
        "--collect-all", "rasterio",
        "--collect-all", "pyproj",
        "--collect-all", "shapely",
        "--collect-submodules", "sklearn.ensemble",
        "--collect-submodules", "sklearn.impute",
        "--collect-submodules", "sklearn.compose",
        "--collect-submodules", "sklearn.preprocessing",
        "--collect-submodules", "sklearn.pipeline",
        "--collect-submodules", "sklearn.tree",
        "--collect-submodules", "sklearn.utils",
        "--hidden-import", "sklearn",
        "--hidden-import", "joblib",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",
        "--hidden-import", "api.main",
        "--hidden-import", "api.schemas",
        "--hidden-import", "src.inference.location_profiler",
        "--hidden-import", "src.inference.rainfall_provider",
        "--hidden-import", "src.inference.risk_fusion",
        "--hidden-import", "src.inference.rainfall_trigger",
        # Excluded unnecessary modules to minimize footprint
        "--exclude-module", "pytest",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "torchaudio",
        "--exclude-module", "tensorboard",
        "--exclude-module", "sympy",
        "--exclude-module", "PIL.ImageTk",
        "--exclude-module", "shapely.tests",
        "--exclude-module", "rasterio.tests",
        "--exclude-module", "scipy.tests",
        "--exclude-module", "numpy.tests",
        "--exclude-module", "pandas.tests",
        "--exclude-module", "sklearn.tests",
        str(PROJECT_ROOT / "desktop_app.py"),
    ]
    
    print(f"Executing command: {' '.join(cmd[:6])} ...")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller failed with exit code {res.returncode}")

def ensure_bundle_mirror():
    """
    Mirror key asset directories directly into dist/LANDSLIDENEI root
    to guarantee both exe-relative and internal-relative path discovery.
    """
    print("[4/5] Mirroring asset bundles into distribution directory...")
    dist_dir = PROJECT_ROOT / "dist" / "LANDSLIDENEI"
    if not dist_dir.exists():
        raise FileNotFoundError(f"Dist directory not found: {dist_dir}")

    # Folders to guarantee at root
    folders_to_copy = [
        ("dashboard", dist_dir / "dashboard"),
        ("website", dist_dir / "website"),
        ("config", dist_dir / "config"),
        ("model", dist_dir / "model"),
        ("assets", dist_dir / "assets"),
    ]
    for src_name, target_dir in folders_to_copy:
        src_path = PROJECT_ROOT / src_name
        if not target_dir.exists():
            print(f"  Copying {src_name} -> {target_dir.relative_to(PROJECT_ROOT)}...")
            shutil.copytree(src_path, target_dir, dirs_exist_ok=True)

    # Specific data subsets
    data_val = dist_dir / "data" / "inspection" / "landslide_validation"
    data_val.mkdir(parents=True, exist_ok=True)
    gadm_src = PROJECT_ROOT / "data" / "inspection" / "landslide_validation" / "gadm41_IND_1.json"
    gadm_dest = data_val / "gadm41_IND_1.json"
    if not gadm_dest.exists() and gadm_src.exists():
        shutil.copy2(gadm_src, gadm_dest)

    data_proc = dist_dir / "data" / "processed"
    data_proc.mkdir(parents=True, exist_ok=True)
    src_proc = PROJECT_ROOT / "data" / "processed"
    for item in ["cwc_rainfall_features.csv", "rainfall", "imd"]:
        s = src_proc / item
        d = data_proc / item
        if s.exists() and not d.exists():
            if s.is_dir():
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

def verify_build_output():
    """Verify built executable and assets."""
    print("[5/5] Verifying distribution package...")
    exe_path = PROJECT_ROOT / "dist" / "LANDSLIDENEI" / "LANDSLIDENEI.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Target executable not found: {exe_path}")

    exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
    dist_dir = PROJECT_ROOT / "dist" / "LANDSLIDENEI"
    total_size_mb = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()) / (1024 * 1024)

    print(f"\n========================================================")
    print(f" BUILD SUCCESSFUL!")
    print(f" Executable: {exe_path}")
    print(f" Executable Size: {exe_size_mb:.2f} MB")
    print(f" Total Distribution Bundle Size: {total_size_mb:.2f} MB")
    print(f"========================================================\n")

if __name__ == "__main__":
    clean_build_artifacts()
    verify_source_assets()
    run_pyinstaller()
    ensure_bundle_mirror()
    verify_build_output()
