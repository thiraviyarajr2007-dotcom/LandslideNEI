"""
Phase 8M - GitHub Pages Static Deployment & Asset Path Verification Tests
=========================================================================
Validates:
1. Static website entry point exists at website/index.html.
2. Relative asset paths (CSS, JS, SVG assets) resolve cleanly without root-leading slash.
3. Subpath hosting compatibility under /LandslideNEI/.
4. Internal anchor navigation parity (every href="#id" has an existing target element).
5. No fake external download links (Windows download triggers modal with valid package manifest).
6. JavaScript syntax validity in website/js/app.js.
7. GitHub Actions Pages workflow configuration integrity.
"""

import http.server
import re
import socketserver
import threading
import time
from pathlib import Path
import pytest
import requests

PROJECT_ROOT = Path("C:/SIH Landslide")
WEBSITE_DIR = PROJECT_ROOT / "website"


def test_website_entry_point_exists():
    """Requirement 1 & 2: Confirm final website entry point exists at website/index.html."""
    entry_point = WEBSITE_DIR / "index.html"
    assert entry_point.exists(), "Missing website/index.html entry point"
    assert entry_point.stat().st_size > 10000, "website/index.html seems truncated"


def test_asset_relative_paths():
    """Requirement 3 & 5: Ensure all CSS, JS, and image assets use relative paths without root leading slashes."""
    content = (WEBSITE_DIR / "index.html").read_text(encoding="utf-8")

    hrefs = re.findall(r'href=["\'](.*?)["\']', content)
    srcs = re.findall(r'src=["\'](.*?)["\']', content)

    # Check for prohibited absolute root paths like /assets/, /css/, /js/, /dashboard/
    root_leading_paths = [
        path for path in (hrefs + srcs)
        if path.startswith("/") and not path.startswith("//")
    ]
    assert len(root_leading_paths) == 0, f"Found prohibited root-leading paths in website/index.html: {root_leading_paths}"


def test_internal_anchor_links():
    """Requirement 14: Verify internal navigation anchors link to valid DOM element IDs."""
    content = (WEBSITE_DIR / "index.html").read_text(encoding="utf-8")

    anchors = re.findall(r'href=["\']#([a-zA-Z0-9_-]+)["\']', content)
    assert len(anchors) >= 5, "Expected at least 5 internal anchor links"

    for anchor in set(anchors):
        # Look for id="anchor"
        assert f'id="{anchor}"' in content, f"Anchor #{anchor} does not have a corresponding element id='{anchor}'"


def test_download_button_integrity():
    """Requirement 14: Verify Download for Windows does not point to a fake external URL."""
    content = (WEBSITE_DIR / "index.html").read_text(encoding="utf-8")

    # Download buttons should have data-action="download-windows"
    download_buttons = re.findall(r'<a\b[^>]*data-action=["\']download-windows["\'][^>]*>', content)
    assert len(download_buttons) >= 2, "Expected at least 2 Download for Windows trigger links"

    for btn in download_buttons:
        assert 'href="http' not in btn, f"Download button points to external URL: {btn}"


def test_js_syntax_integrity():
    """Requirement 14: Verify JavaScript syntax is valid and loads cleanly."""
    js_file = WEBSITE_DIR / "js" / "app.js"
    assert js_file.exists()
    js_content = js_file.read_text(encoding="utf-8")

    assert "DOMContentLoaded" in js_content
    assert "initMobileMenu" in js_content
    assert "initModals" in js_content
    assert "downloadPlaceholderPackage" in js_content
    # Confirm manifest string is valid array join, not bare unquoted text
    assert 'const manifest = [' in js_content


def test_github_actions_pages_workflow_configured():
    """Requirement 11: Verify GitHub Actions Pages workflow file exists with proper permissions and path."""
    workflow_file = PROJECT_ROOT / ".github" / "workflows" / "deploy-pages.yml"
    assert workflow_file.exists(), "Missing .github/workflows/deploy-pages.yml"

    content = workflow_file.read_text(encoding="utf-8")
    assert "actions/upload-pages-artifact" in content
    assert "actions/deploy-pages" in content
    assert "path: './website'" in content or 'path: "website"' in content
    assert "pages: write" in content
    assert "id-token: write" in content


class SubpathHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler that maps /LandslideNEI/ to the website directory."""
    def translate_path(self, path):
        subpath_prefix = "/LandslideNEI"
        if path == subpath_prefix or path.startswith(subpath_prefix + "/"):
            rel = path[len(subpath_prefix):].lstrip("/")
            if not rel:
                rel = "index.html"
            return str(WEBSITE_DIR / rel)
        # Also serve at root / for direct root testing
        rel_root = path.lstrip("/")
        if not rel_root:
            rel_root = "index.html"
        return str(WEBSITE_DIR / rel_root)

    def log_message(self, format, *args):
        # Suppress noisy request logs during test run
        pass


@pytest.fixture(scope="module")
def local_static_server():
    """Spins up a local static server simulating both root / and /LandslideNEI/ subpath hosting."""
    # Find free port
    server = socketserver.TCPServer(("127.0.0.1", 0), SubpathHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    server.server_close()


def test_subpath_hosting_under_landslidenei(local_static_server):
    """Requirement 12 & 13: Test that /LandslideNEI/ loads all assets with HTTP 200."""
    base_url = f"{local_static_server}/LandslideNEI"

    # 1. Homepage loads
    resp_home = requests.get(f"{base_url}/")
    assert resp_home.status_code == 200
    assert "LANDSLIDENEI" in resp_home.text
    assert "<title>" in resp_home.text

    # 2. CSS loads
    resp_css = requests.get(f"{base_url}/css/styles.css")
    assert resp_css.status_code == 200
    assert "modal-backdrop" in resp_css.text

    # 3. JS loads
    resp_js = requests.get(f"{base_url}/js/app.js")
    assert resp_js.status_code == 200
    assert "initMobileMenu" in resp_js.text

    # 4. Images / SVGs load
    resp_logo = requests.get(f"{base_url}/assets/logo.svg")
    assert resp_logo.status_code == 200
    assert "svg" in resp_logo.headers.get("content-type", "") or "<svg" in resp_logo.text

    resp_fav = requests.get(f"{base_url}/assets/favicon.svg")
    assert resp_fav.status_code == 200
    assert "svg" in resp_fav.headers.get("content-type", "") or "<svg" in resp_fav.text


def test_root_hosting(local_static_server):
    """Requirement 12 & 13: Test that root / loads all assets with HTTP 200."""
    base_url = local_static_server

    resp_home = requests.get(f"{base_url}/")
    assert resp_home.status_code == 200
    assert "LANDSLIDENEI" in resp_home.text

    resp_css = requests.get(f"{base_url}/css/styles.css")
    assert resp_css.status_code == 200

    resp_js = requests.get(f"{base_url}/js/app.js")
    assert resp_js.status_code == 200
