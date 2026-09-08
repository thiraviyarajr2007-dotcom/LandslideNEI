"""
LANDSLIDENEI - Windows Desktop Workstation Main Application Entry Point
======================================================================
Launches the embedded local FastAPI risk inference engine on localhost
and opens the dedicated native Windows desktop workstation interface.
"""

from __future__ import annotations

import ctypes
import io
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Ensure standard streams are not None in PyInstaller --windowed mode
ORIG_STDOUT = sys.__stdout__
ORIG_STDERR = sys.__stderr__

if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# 1. Resolve Application Runtime Directory
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
    if (exe_dir / "model" / "static_lsm_pipeline.joblib").exists():
        APP_ROOT = exe_dir
    elif (meipass / "model" / "static_lsm_pipeline.joblib").exists():
        APP_ROOT = meipass
    else:
        APP_ROOT = exe_dir
    INSTALL_DIR = exe_dir
else:
    APP_ROOT = Path(__file__).resolve().parent
    INSTALL_DIR = APP_ROOT

os.environ["LANDSLIDENEI_ROOT"] = str(APP_ROOT)
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# Configure GDAL and PROJ data paths if bundled
for candidate in [APP_ROOT / "rasterio" / "gdal_data", APP_ROOT / "_internal" / "rasterio" / "gdal_data"]:
    if candidate.exists():
        os.environ["GDAL_DATA"] = str(candidate)
        break

for candidate in [APP_ROOT / "pyproj" / "proj_dir" / "share" / "proj", APP_ROOT / "_internal" / "pyproj" / "proj_dir" / "share" / "proj"]:
    if candidate.exists():
        os.environ["PROJ_DATA"] = str(candidate)
        os.environ["PROJ_LIB"] = str(candidate)
        break

# User data & logs directory in %LOCALAPPDATA%\LandslideNEI
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
USER_DATA_DIR = Path(LOCAL_APPDATA) / "LandslideNEI"
LOGS_DIR = USER_DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
STARTUP_LOG = LOGS_DIR / "startup.log"


def log_startup(message: str) -> None:
    """Log startup message to persistent user logs."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(STARTUP_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def show_error_box(title: str, message: str) -> None:
    """Display native Windows alert box without raw stack traces."""
    log_startup(f"ERROR: {title} - {message}")
    if "--check-health" not in sys.argv and sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    else:
        print(f"[{title}] {message}", file=sys.stderr)


def find_free_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Find a free localhost port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def start_backend_server(port: int, stop_event: threading.Event) -> None:
    """Run uvicorn server in a dedicated worker thread with its own asyncio loop."""
    try:
        log_startup("BackendThread: Initializing asyncio event loop...")
        import asyncio
        import uvicorn
        log_startup("BackendThread: Importing FastAPI application...")
        from api.main import app
        log_startup("BackendThread: FastAPI application imported successfully.")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
            loop="asyncio",
        )
        server = uvicorn.Server(config)

        # Monitor stop_event to shut down server
        def monitor_stop():
            stop_event.wait()
            server.should_exit = True

        threading.Thread(target=monitor_stop, daemon=True).start()
        log_startup(f"BackendThread: Starting Uvicorn server on port {port}...")
        loop.run_until_complete(server.serve())
        log_startup("BackendThread: Uvicorn server stopped cleanly.")
    except BaseException as e:
        import traceback
        log_startup(f"Backend thread exception:\n{traceback.format_exc()}")


def wait_for_backend(port: int, timeout_sec: float = 60.0) -> bool:
    """Poll localhost health endpoint until HTTP 200 or timeout."""
    import urllib.request

    url = f"http://127.0.0.1:{port}/api/v1/health"
    start_t = time.time()
    deadline = start_t + timeout_sec
    last_log = start_t
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    elapsed = time.time() - start_t
                    log_startup(f"Backend responded HTTP 200 in {elapsed:.1f}s.")
                    return True
        except Exception:
            if time.time() - last_log >= 5.0:
                last_log = time.time()
                elapsed = last_log - start_t
                log_startup(f"Waiting for local inference engine readiness... ({elapsed:.0f}s / {timeout_sec:.0f}s)")
            time.sleep(0.5)
    return False


def launch_desktop_window(port: int) -> subprocess.Popen | None:
    """
    Launch Microsoft Edge in dedicated --app mode for a clean native desktop experience.
    Falls back to system default browser if Edge is not located.
    """
    target_url = f"http://127.0.0.1:{port}/dashboard/"

    edge_candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]

    edge_exe = next((p for p in edge_candidates if p.exists()), None)

    if edge_exe:
        log_startup(f"Launching desktop window via Edge: {edge_exe}")
        cmd = [
            str(edge_exe),
            f"--app={target_url}",
            "--window-size=1440,900",
            f"--user-data-dir={USER_DATA_DIR / 'webview_profile'}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        return subprocess.Popen(cmd)
    else:
        log_startup("Edge not found, falling back to default browser.")
        import webbrowser
        webbrowser.open(target_url)
        return None


def main() -> int:
    """Main execution lifecycle."""
    log_startup("LANDSLIDENEI Desktop Workstation starting...")

    # Check model existence
    model_path = APP_ROOT / "model" / "static_lsm_pipeline.joblib"
    if not model_path.exists():
        show_error_box(
            "LANDSLIDENEI - Missing Model Asset",
            f"Required static susceptibility model file was not found:\n{model_path}\n\n"
            f"Please ensure the application is properly installed."
        )
        return 1

    port = find_free_port(8000)
    log_startup(f"Bound local backend port: {port}")

    stop_event = threading.Event()
    server_thread = threading.Thread(
        target=start_backend_server,
        args=(port, stop_event),
        daemon=True,
        name="BackendThread"
    )
    server_thread.start()

    log_startup("Waiting for local inference engine readiness...")
    if not wait_for_backend(port, timeout_sec=60.0):
        show_error_box(
            "LANDSLIDENEI - Initialization Failure",
            "The local risk inference engine failed to respond on localhost.\n\n"
            f"Diagnostics have been saved to:\n{STARTUP_LOG}"
        )
        stop_event.set()
        return 1

    log_startup(f"Inference engine online at http://127.0.0.1:{port}/")

    if "--check-health" in sys.argv:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health") as resp:
            data = resp.read().decode("utf-8")
        msg = f"HEALTH_OK: {data}"
        log_startup(f"Health check succeeded: {data}")
        # Write directly to original file handles if attached, plus standard streams
        if ORIG_STDOUT is not None:
            try:
                ORIG_STDOUT.write(msg + "\n")
                ORIG_STDOUT.flush()
            except Exception:
                pass
        if ORIG_STDERR is not None:
            try:
                ORIG_STDERR.write(msg + "\n")
                ORIG_STDERR.flush()
            except Exception:
                pass
        print(msg)
        print(msg, file=sys.stderr)
        stop_event.set()
        time.sleep(0.5)
        return 0

    if "--test-terrain-offline" in sys.argv:
        import urllib.request
        import urllib.error
        import json
        test_locs = [
            ("1. Kohima (Nagaland)", 25.6740, 94.1120, "Authoritative NH-29 Corridor Cache"),
            ("2. Shillong (Meghalaya)", 25.5788, 91.8933, "Authoritative Capital Focal Cache"),
            ("3. Tezpur (Assam)", 26.6338, 92.7926, "Authoritative North-Bank Brahmaputra Focal Cache"),
            ("4. Imphal (Manipur)", 24.8170, 93.9368, "Authoritative Capital Intermontane Focal Cache"),
            ("5. Mokokchung (Nagaland)", 26.3256, 94.5165, "Authoritative Central Nagaland Focal Cache"),
            ("6. Lunglei (Mizoram)", 22.8872, 92.7388, "Authoritative Southern Mizoram Focal Cache"),
            ("7. Agartala (Tripura)", 23.8315, 91.2868, "Authoritative Capital Urban Focal Cache"),
            ("8. Nongstoin (Meghalaya)", 25.5200, 91.2700, "Genuine Resampled Window from Regional N25_E091 Cache"),
            ("9. Itanagar (Arunachal)", 27.0844, 93.6053, "Authoritative Foothills Focal Cache"),
            ("10. Namchi (Sikkim)", 27.1667, 88.3500, "Authoritative South Sikkim Focal Cache"),
        ]
        results = []
        all_passed = True
        total_time_ms = 0
        for name, lat, lon, desc in test_locs:
            t0 = time.perf_counter()
            url = f"http://127.0.0.1:{port}/api/v1/terrain/mesh?latitude={lat}&longitude={lon}&radius_km=10.0&grid_size=128"
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req) as resp:
                    t_load = (time.perf_counter() - t0) * 1000
                    total_time_ms += t_load
                    data = json.loads(resp.read().decode("utf-8"))
                    stats = data.get("elevation_stats", {})
                    ok = data.get("status") == "SUCCESS" and stats.get("min_m") is not None and len(data.get("elevations", [])) == 16384
                    if not ok:
                        all_passed = False
                    res_line = f"LOC: {name:28s} | Lat: {lat:.4f} Lon: {lon:.4f} | Src: {data.get('dem_source')[:25]} | Mode: {data.get('source_mode')} | Elev: {stats.get('min_m')}m - {stats.get('max_m')}m | Time: {t_load:.1f}ms | Result: {'PASS' if ok else 'FAIL'}"
                    results.append(res_line)
                    log_startup(res_line)
            except Exception as exc:
                all_passed = False
                res_line = f"LOC: {name} | ERROR: {exc}"
                results.append(res_line)
                log_startup(res_line)

        # Test out-of-domain coordinate
        bad_ok = False
        try:
            url_bad = f"http://127.0.0.1:{port}/api/v1/terrain/mesh?latitude=28.6139&longitude=77.2090"
            urllib.request.urlopen(url_bad)
        except urllib.error.HTTPError as e:
            bad_ok = (e.code == 404)

        avg_time = total_time_ms / len(test_locs)
        summary = (
            f"\n================================================================================\n"
            f"STEP 9 EXE OFFLINE TERRAIN VERIFICATION REPORT\n"
            f"================================================================================\n"
            + "\n".join(results)
            + f"\n--------------------------------------------------------------------------------\n"
            f"Out-of-Domain 404 Guardrail: {'PASS (404 Not Found)' if bad_ok else 'FAIL'}\n"
            f"Average Terrain Load Time:   {avg_time:.2f} ms\n"
            f"Final Offline Readiness:     {'FULL NER OFFLINE TERRAIN READY' if (all_passed and bad_ok) else 'FULL NER OFFLINE TERRAIN NOT READY'}\n"
            f"================================================================================\n"
        )
        if ORIG_STDOUT is not None:
            try:
                ORIG_STDOUT.write(summary)
                ORIG_STDOUT.flush()
            except Exception:
                pass
        print(summary)
        stop_event.set()
        time.sleep(0.5)
        return 0 if (all_passed and bad_ok) else 1

    # Launch desktop window
    win_proc = launch_desktop_window(port)

    if win_proc:
        # Wait for the user to close the desktop application window
        try:
            win_proc.wait()
        except KeyboardInterrupt:
            pass
    else:
        # If launched via default browser, wait for interrupt
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    log_startup("Application window closed by user. Stopping local backend...")
    stop_event.set()
    time.sleep(0.5)
    log_startup("LANDSLIDENEI terminated cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
