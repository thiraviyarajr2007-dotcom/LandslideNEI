"""
Unit and Integration Tests for Desktop Application Packaging (Phase 8N)
Verifies build configuration, website download links, installer assets,
and standalone executable health check.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def test_packaging_prerequisites_exist():
    """Verify build scripts, icon, entrypoints, and CI workflows exist."""
    assert (PROJECT_ROOT / "desktop_app.py").exists(), "desktop_app.py runtime missing"
    assert (PROJECT_ROOT / "scripts" / "build_desktop_app.py").exists(), "build_desktop_app.py missing"
    assert (PROJECT_ROOT / "scripts" / "build_windows_installer.ps1").exists(), "build_windows_installer.ps1 missing"
    assert (PROJECT_ROOT / "assets" / "icon.ico").exists(), "assets/icon.ico missing"
    assert (PROJECT_ROOT / ".github" / "workflows" / "windows-build.yml").exists(), "windows-build.yml missing"

def test_website_download_integration():
    """Verify website download buttons point to official release installer URL."""
    html_path = PROJECT_ROOT / "website" / "index.html"
    js_path = PROJECT_ROOT / "website" / "js" / "app.js"
    
    html_content = html_path.read_text(encoding="utf-8")
    js_content = js_path.read_text(encoding="utf-8")
    
    assert "LANDSLIDENEI_Setup_x64.exe" in html_content, "Missing installer name in website HTML"
    assert "v1.0.0" in html_content, "Missing release version in website HTML"
    assert "downloadReleasePackage" in js_content, "Missing downloadReleasePackage in app.js"
    
    expected_url = "https://github.com/thiraviyarajr2007-dotcom/LandslideNEI/releases/download/v1.0.0/LANDSLIDENEI_Setup_x64.exe"
    assert expected_url in js_content, f"Expected release URL {expected_url} not found in app.js"

def test_gitignore_contains_packaging_artifacts():
    """Verify .gitignore prevents committing large build binaries."""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "installer/*.exe" in gitignore

def test_desktop_app_check_health_cli():
    """
    Test headless health check flag --check-health on python entrypoint directly.
    """
    python_exe = sys.executable
    cmd = [python_exe, str(PROJECT_ROOT / "desktop_app.py"), "--check-health"]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"desktop_app.py --check-health failed: {res.stderr}"
    assert "healthy" in res.stdout or "UP" in res.stdout or "OK" in res.stdout or "LANDSLIDENEI" in res.stdout

def test_distribution_bundle_if_built():
    """
    If dist/LANDSLIDENEI/LANDSLIDENEI.exe exists, verify directory structure and data mirroring.
    """
    exe_path = PROJECT_ROOT / "dist" / "LANDSLIDENEI" / "LANDSLIDENEI.exe"
    if not exe_path.exists():
        pytest.skip("Distribution bundle not yet built in local environment")

    dist_dir = PROJECT_ROOT / "dist" / "LANDSLIDENEI"
    assert (dist_dir / "dashboard" / "index.html").exists(), "dashboard bundle missing in dist"
    assert (dist_dir / "website" / "index.html").exists(), "website bundle missing in dist"
    assert (dist_dir / "config" / "risk_thresholds.json").exists(), "config bundle missing in dist"
    assert (dist_dir / "model" / "static_lsm_pipeline.joblib").exists(), "model bundle missing in dist"
    assert (dist_dir / "data" / "inspection" / "landslide_validation" / "gadm41_IND_1.json").exists(), "GADM geojson missing in dist"

def test_executable_headless_health_if_built():
    """
    If dist/LANDSLIDENEI/LANDSLIDENEI.exe exists, run it headlessly with --check-health.
    """
    exe_path = PROJECT_ROOT / "dist" / "LANDSLIDENEI" / "LANDSLIDENEI.exe"
    if not exe_path.exists():
        pytest.skip("Executable not yet built in local environment")

    res = subprocess.run([str(exe_path), "--check-health"], capture_output=True, text=True, timeout=60)
    combined = res.stdout + " " + res.stderr
    assert res.returncode == 0, f"LANDSLIDENEI.exe --check-health failed with code {res.returncode}: {combined}"
    assert "HEALTH_OK" in combined or "status" in combined
    assert "ok" in combined.lower()
