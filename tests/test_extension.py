"""
Unit Tests for LandslideNEI Chrome/Edge Browser Extension (Manifest V3)
========================================================================
Tests:
1. Manifest V3 Schema & Metadata Compliance
2. Extension Icons Resolution & Integrity
3. Popup HTML, CSS & JavaScript Structure
4. Background Service Worker & Side Panel Assets
5. Extension Distribution Packager & ZIP Verification
"""

import json
from pathlib import Path
import zipfile
import pytest
from PIL import Image

from scripts.package_extension import package_extension


@pytest.fixture
def extension_dir():
    return Path(__file__).resolve().parents[1] / "extension"


def test_manifest_schema_compliance(extension_dir):
    """Verify that manifest.json conforms to Chromium Manifest V3 specifications."""
    manifest_path = extension_dir / "manifest.json"
    assert manifest_path.exists(), "manifest.json must exist in extension/"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("manifest_version") == 3, "Must be Manifest V3"
    assert "LandslideNEI" in manifest.get("name", "")
    assert manifest.get("version") == "1.0.0"
    assert "action" in manifest
    assert manifest["action"].get("default_popup") == "popup/popup.html"
    assert manifest.get("background", {}).get("service_worker") == "background.js"
    assert "sidePanel" in manifest.get("permissions", [])
    assert "storage" in manifest.get("permissions", [])
    assert manifest.get("side_panel", {}).get("default_path") == "sidepanel/sidepanel.html"


def test_extension_icons_integrity(extension_dir):
    """Verify that all required icon resolutions exist and have valid PNG dimensions."""
    icons_dir = extension_dir / "icons"
    assert icons_dir.exists()

    expected_sizes = [16, 32, 48, 128]
    for size in expected_sizes:
        icon_path = icons_dir / f"icon{size}.png"
        assert icon_path.exists(), f"Missing icon: {icon_path.name}"

        with Image.open(icon_path) as img:
            assert img.format == "PNG"
            assert img.size == (size, size)


def test_popup_ui_assets(extension_dir):
    """Verify that popup HTML, CSS, and JS exist and contain critical interface components."""
    popup_html = extension_dir / "popup" / "popup.html"
    popup_css = extension_dir / "popup" / "popup.css"
    popup_js = extension_dir / "popup" / "popup.js"

    assert popup_html.exists()
    assert popup_css.exists()
    assert popup_js.exists()

    html_content = popup_html.read_text(encoding="utf-8")
    assert "sector-select" in html_content
    assert "verdict-pill" in html_content
    assert "rain-24h" in html_content
    assert "fos-val" in html_content
    assert "slope-val" in html_content
    assert "road-cut-val" in html_content
    assert "btn-open-workstation" in html_content

    js_content = popup_js.read_text(encoding="utf-8")
    assert "evaluatePoint" in js_content
    assert "checkApiHealth" in js_content
    assert "updateBadge" in js_content


def test_background_service_worker_and_sidepanel(extension_dir):
    """Verify background.js and sidepanel assets exist and have valid logic."""
    bg_js = extension_dir / "background.js"
    sidepanel_html = extension_dir / "sidepanel" / "sidepanel.html"
    sidepanel_js = extension_dir / "sidepanel" / "sidepanel.js"

    assert bg_js.exists()
    assert sidepanel_html.exists()
    assert sidepanel_js.exists()

    bg_content = bg_js.read_text(encoding="utf-8")
    assert "chrome.runtime.onInstalled" in bg_content
    assert "chrome.action.setBadgeText" in bg_content
    assert "chrome.alarms.onAlarm" in bg_content


def test_package_extension_zip_verification(extension_dir):
    """Verify that the packaging script creates a valid zip archive containing all required assets."""
    zip_path = package_extension()
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    assert zip_path.stat().st_size > 5000  # At least 5 KB

    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "background.js" in names
        assert "icons/icon16.png" in names
        assert "icons/icon128.png" in names
        assert "popup/popup.html" in names
        assert "popup/popup.js" in names
        assert "sidepanel/sidepanel.html" in names
