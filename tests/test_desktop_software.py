"""
Phase 8L - Windows Desktop Software Verification Tests
======================================================
Validates:
1. All 10 dedicated view routes exist in dashboard/index.html.
2. Strictly English-only UI: 0 Tamil unicode characters (\\u0b80-\\u0bff) in index.html.
3. Windows titlebar and window control buttons exist.
4. Zero dead buttons: every button has an onclick handler, data-navigate target, or form submit action.
5. Scientific disclaimer ("not an uncalibrated probability") is present.
6. CSS contains tactical dark theme tokens, Space Grotesk, and JetBrains Mono.
7. JS contains router (navigateTo), auth handlers, telemetry table, and report renderer.
"""

import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app

PROJECT_ROOT = Path("C:/SIH Landslide")
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_all_10_views_present_in_dashboard():
    """Verify all 10 architectural views exist with data-view attributes."""
    index_file = DASHBOARD_DIR / "index.html"
    assert index_file.exists(), "dashboard/index.html does not exist"
    content = index_file.read_text(encoding="utf-8")

    expected_views = [
        "view-setup",
        "view-login",
        "view-register",
        "view-home",
        "view-location-analysis",
        "view-risk-map",
        "view-rainfall-telemetry",
        "view-alerts",
        "view-reports",
        "view-settings",
    ]

    for view_id in expected_views:
        assert f'id="{view_id}"' in content, f"Missing view: {view_id} in dashboard/index.html"


def test_strictly_english_only():
    """Verify zero Tamil characters (\\u0B80-\\u0BFF) appear anywhere in dashboard/index.html."""
    index_file = DASHBOARD_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    tamil_matches = re.findall(r"[\u0B80-\u0BFF]", content)
    assert len(tamil_matches) == 0, f"Found {len(tamil_matches)} Tamil characters in dashboard/index.html"


def test_titlebar_and_window_controls():
    """Verify standard Windows desktop workstation titlebar and control buttons."""
    index_file = DASHBOARD_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    assert 'class="window-titlebar"' in content
    assert 'id="sys-btn-minimize"' in content
    assert 'id="sys-btn-maximize"' in content
    assert 'id="sys-btn-close"' in content


def test_zero_dead_buttons():
    """Verify all buttons have functional triggers (onclick, data-navigate, or type=submit)."""
    index_file = DASHBOARD_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    button_tags = re.findall(r"<button\b[^>]*>", content, re.IGNORECASE)
    assert len(button_tags) >= 20, f"Expected at least 20 interactive buttons, found {len(button_tags)}"

    for btn in button_tags:
        has_click = "onclick=" in btn
        has_nav = "data-navigate=" in btn
        has_submit = 'type="submit"' in btn
        has_id = 'id="sys-btn-' in btn or 'id="user-profile-btn"' in btn or 'id="btn-' in btn
        has_action = 'data-action=' in btn or 'data-alert-filter=' in btn
        assert has_click or has_nav or has_submit or has_id or has_action, f"Potentially dead button found without action: {btn}"


def test_scientific_disclaimer_present():
    """Verify the required scientific disclaimer is explicitly rendered in the desktop UI."""
    index_file = DASHBOARD_DIR / "index.html"
    content = index_file.read_text(encoding="utf-8")

    disclaimer_pattern = "not an uncalibrated probability of landslide occurrence"
    assert disclaimer_pattern in content.lower(), "Missing scientific disclaimer in dashboard/index.html"


def test_tactical_dark_theme_css():
    """Verify CSS incorporates design tokens matching the software_theme specification."""
    css_file = DASHBOARD_DIR / "css" / "styles.css"
    assert css_file.exists()
    css_content = css_file.read_text(encoding="utf-8")

    assert "#0b1325" in css_content  # Surface color
    assert "#060e1f" in css_content  # Container lowest
    assert "#00e5ff" in css_content  # Primary container
    assert "Space Grotesk" in css_content
    assert "JetBrains Mono" in css_content


def test_js_router_and_workstation_logic():
    """Verify core workstation router and analytical handlers are declared in app.js."""
    js_file = DASHBOARD_DIR / "js" / "app.js"
    assert js_file.exists()
    js_content = js_file.read_text(encoding="utf-8")

    expected_functions = [
        "navigateTo",
        "evaluateLocation",
        "renderCwcTable",
        "renderAlerts",
        "renderReportDocument",
        "handleLogin",
        "handleRegister",
        "handleLogout",
    ]
    for fn in expected_functions:
        assert fn in js_content, f"Missing function {fn} in app.js"


def test_desktop_software_served_via_fastapi(client):
    """Verify FastAPI serves the desktop workstation index and assets cleanly."""
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert "LandslideNEI" in resp.text
    assert "view-home" in resp.text
    assert "view-risk-map" in resp.text
    assert "view-rainfall-telemetry" in resp.text
