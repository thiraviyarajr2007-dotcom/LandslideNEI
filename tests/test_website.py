"""
Phase 8K - LANDSLIDENEI Public Product Website Integration Tests
================================================================
Validates:
1. Static files mounting and delivery via FastAPI for public website.
2. Root JSON overview includes website_url and download_url.
3. Root HTML redirect parameter handling for website view.
4. Delivery and integrity of CSS, JS, logo.svg, and favicon.svg.
5. All required navigation anchors (#product, #how-it-works, #technology, #dashboard, #about, #download).
6. English-only content integrity (0 Tamil characters or translation selectors).
7. Windows download endpoint (/download/windows) contract.
8. Interactive action elements (download-windows, view-brief) exist and have matching modals.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app

PROJECT_ROOT = Path("C:/SIH Landslide")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_website_index_served(client):
    """Verify /website/ serves index.html with 200 OK."""
    resp = client.get("/website/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "LANDSLIDENEI" in resp.text
    assert "Geospatial Operations Engine" in resp.text or "OPERATIONAL GIS PLATFORM" in resp.text


def test_root_json_includes_website(client):
    """Verify root JSON API includes website_url and download_url."""
    resp = client.get("/", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["website_url"] == "/website/"
    assert data["dashboard_url"] == "/dashboard/"
    assert data["download_url"] == "/download/windows"


def test_root_redirect_with_website_view(client):
    """Verify / with ?view=website redirects to /website/."""
    resp = client.get("/?view=website", headers={"Accept": "text/html"}, follow_redirects=False)
    assert resp.status_code in [302, 307]
    assert resp.headers["location"] == "/website/"


def test_static_website_assets(client):
    """Verify CSS, JS, logo.svg, and favicon.svg are served correctly."""
    assets = [
        ("/website/css/styles.css", "text/css", "Custom Tactical Scrollbar"),
        ("/website/js/app.js", "application/javascript", "initMobileMenu"),
        ("/website/assets/logo.svg", "image/svg+xml", "<svg"),
        ("/website/assets/favicon.svg", "image/svg+xml", "<svg"),
    ]
    for path, exp_type, exp_content in assets:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed to fetch {path}"
        assert exp_type in resp.headers.get("content-type", "") or "text" in resp.headers.get("content-type", "")
        assert exp_content in resp.text, f"Missing content in {path}"


def test_required_section_anchors(client):
    """Verify all required section anchors exist in website HTML."""
    resp = client.get("/website/")
    assert resp.status_code == 200
    text = resp.text
    required_ids = ["product", "how-it-works", "technology", "dashboard", "about", "download"]
    for sid in required_ids:
        assert f'id="{sid}"' in text, f"Missing required anchor id='{sid}' in website HTML"


def test_english_only_content(client):
    """Verify website is strictly English with 0 Tamil characters."""
    resp = client.get("/website/")
    assert resp.status_code == 200
    text = resp.text
    tamil_chars = [c for c in text if 0x0B80 <= ord(c) <= 0x0BFF]
    assert len(tamil_chars) == 0, f"Found {len(tamil_chars)} unexpected Tamil characters"
    assert "language-selector" not in text
    assert "language-switcher" not in text


def test_windows_download_distribution_route(client):
    """Verify /download/windows returns verified release package manifest."""
    resp = client.get("/download/windows")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"] == "LANDSLIDENEI Desktop Workstation"
    assert data["package_name"] == "LANDSLIDENEI_Setup_x64.exe"
    assert "sha256" in data
    assert "minimum_requirements" in data
    assert data["minimum_requirements"]["architecture"] == "x86_64"


def test_interactive_modals_and_actions(client):
    """Verify interactive modal triggers and containers are present."""
    resp = client.get("/website/")
    assert resp.status_code == 200
    text = resp.text
    assert 'id="download-modal"' in text
    assert 'id="brief-modal"' in text
    assert 'data-action="download-windows"' in text
    assert 'data-action="view-brief"' in text
    assert 'id="mobile-menu-btn"' in text
    assert 'id="mobile-drawer"' in text
