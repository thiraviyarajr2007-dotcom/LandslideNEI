"""
LANDSLIDENEI - GitHub Release Asset Publisher
============================================
Publishes the standalone Windows desktop installer (LANDSLIDENEI_Setup_x64.exe)
to GitHub Releases under tag v1.0.0 so that users can download it directly without 404.
"""

import hashlib
import mimetypes
import os
import sys
from pathlib import Path
import requests

import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_PATH = PROJECT_ROOT / "installer" / "LANDSLIDENEI_Setup_x64.exe"
REPO = "thiraviyarajr2007-dotcom/LandslideNEI"
TAG_NAME = "v1.0.0"
RELEASE_NAME = "LANDSLIDENEI v1.0.0 - Official Windows Desktop GA Release"


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            check=True
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("password=", 1)[1].strip()
    except Exception:
        pass
    return ""


TOKEN = get_github_token()

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "LandslideNEI-Release-Publisher",
}

RELEASE_BODY = """## LANDSLIDENEI Operational Landslide Early Warning Workstation
### Official Windows Desktop GA Release (v1.0.0)

This is the official, standalone 64-bit Windows installation package for the **LANDSLIDENEI Desktop Workstation**.

### Package Details:
- **Filename:** `LANDSLIDENEI_Setup_x64.exe`
- **Platform:** Windows 10 & Windows 11 (64-bit)
- **Architecture:** x86_64
- **Size:** ~70.4 MB (73,851,100 bytes)
- **SHA-256 Checksum:** `bc7a6adceb87bbd2674c98e76f2e834f02ae848125fc9319b3f75c992970aaaf`

### Integrated Capabilities:
1. **Model A Static Susceptibility:** Random Forest inference trained on 14 landslide conditioning factors across 8 Northeast Indian states.
2. **Dynamic Trigger Fusion:** Real-time IMD Doppler rainfall and CWC river stage telemetry fusion.
3. **Pore-Water Pressure Engine:** Infinite-slope transient hydrological factor-of-safety modeling.
4. **Micro-Topography & Anthropogenic Engine:** High-resolution DEM slope profiling and toe-cutting hazard detection.
5. **Fully Self-Contained:** Runs completely offline with built-in runtime and dark tactical EOC workstation UI.

### Installation Instructions:
1. Download **`LANDSLIDENEI_Setup_x64.exe`** from the Assets below.
2. Run the installer and specify destination directory (default: `C:\\Program Files\\LANDSLIDENEI` or user directory).
3. Execute `Create_Shortcuts.bat` or launch **`LANDSLIDENEI.exe`**.
"""


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def get_or_create_release():
    print(f"[*] Checking existing releases for {REPO}...")
    url = f"https://api.github.com/repos/{REPO}/releases"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    releases = resp.json()

    for rel in releases:
        if rel.get("tag_name") == TAG_NAME:
            print(f"[+] Release {TAG_NAME} already exists (id: {rel['id']}).")
            return rel

    # Create release
    print(f"[*] Creating new release for tag {TAG_NAME}...")
    payload = {
        "tag_name": TAG_NAME,
        "target_commitish": "main",
        "name": RELEASE_NAME,
        "body": RELEASE_BODY,
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False,
    }
    create_resp = requests.post(url, headers=HEADERS, json=payload)
    if create_resp.status_code not in (200, 201):
        print(f"[-] Failed to create release: {create_resp.status_code} {create_resp.text}")
        sys.exit(1)

    rel = create_resp.json()
    print(f"[+] Successfully created release {TAG_NAME} (id: {rel['id']}) at {rel.get('html_url')}")
    return rel


def upload_asset(release: dict):
    if not INSTALLER_PATH.exists():
        print(f"[-] Installer not found at {INSTALLER_PATH}")
        sys.exit(1)

    file_size = INSTALLER_PATH.stat().st_size
    file_sha = compute_sha256(INSTALLER_PATH)
    print(f"[*] Installer verified: {file_size} bytes, SHA256: {file_sha}")

    # Check if asset already exists in release
    assets = release.get("assets", [])
    for asset in assets:
        if asset.get("name") == INSTALLER_PATH.name:
            print(f"[!] Asset {INSTALLER_PATH.name} already exists in release (id: {asset['id']}).")
            if asset.get("size") == file_size:
                print("[+] Asset size matches. Skipping upload.")
                return asset
            else:
                print("[*] Asset size differs. Deleting old asset...")
                del_resp = requests.delete(asset["url"], headers=HEADERS)
                del_resp.raise_for_status()
                print("[+] Old asset deleted.")
                break

    # Upload asset to upload_url
    upload_url_template = release.get("upload_url", "")
    upload_url = upload_url_template.split("{")[0] + f"?name={INSTALLER_PATH.name}"
    print(f"[*] Uploading {INSTALLER_PATH.name} ({file_size / (1024*1024):.2f} MB) to GitHub Releases...")

    upload_headers = {
        "Authorization": f"token {TOKEN}",
        "Content-Type": "application/vnd.microsoft.portable-executable",
        "User-Agent": "LandslideNEI-Release-Publisher",
    }

    with open(INSTALLER_PATH, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers=upload_headers,
            data=f,
            timeout=300
        )

    if upload_resp.status_code not in (200, 201):
        print(f"[-] Asset upload failed: {upload_resp.status_code} {upload_resp.text}")
        sys.exit(1)

    asset = upload_resp.json()
    print(f"[+] Asset successfully uploaded! Download URL: {asset.get('browser_download_url')}")
    return asset


def verify_download_url():
    download_url = f"https://github.com/{REPO}/releases/download/{TAG_NAME}/{INSTALLER_PATH.name}"
    print(f"[*] Verifying public download URL: {download_url}")
    # Perform a HEAD request following redirects up to 5 times
    resp = requests.head(download_url, allow_redirects=True, timeout=30)
    print(f"[*] Response Status Code: {resp.status_code}")
    print(f"[*] Content-Length: {resp.headers.get('Content-Length')}")
    print(f"[*] Content-Type: {resp.headers.get('Content-Type')}")

    if resp.status_code == 200:
        print("[SUCCESS] GitHub Release download URL is LIVE, VERIFIED, and serving bytes directly!")
        return True
    else:
        print(f"[FAIL] Download URL returned unexpected status {resp.status_code}")
        return False


if __name__ == "__main__":
    release = get_or_create_release()
    upload_asset(release)
    if verify_download_url():
        print("\nAll Release steps completed successfully!")
    else:
        sys.exit(1)
