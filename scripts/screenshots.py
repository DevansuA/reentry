"""Capture real screenshots of the ReEntry web app against the seeded demo.

Run from the repo root:
    python3 scripts/screenshots.py
or via:
    make screenshots

Prerequisites:
    pip install -e . playwright fastapi uvicorn
    python3 -m playwright install chromium
    npm --prefix web install && npm --prefix web run build
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
ASSETS = REPO / "docs" / "assets"
DB = "/tmp/reentry-screenshot.db"
PROJ = "/tmp/reentry-screenshot-proj"
API_PORT = 8000
WEB_PORT = 3000


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def seed_demo() -> None:
    log("seeding demo...")
    subprocess.run(
        ["python3", "-m", "reentry.cli", "demo", "--dir", PROJ],
        env={**os.environ, "REENTRY_DB": DB},
        check=True, capture_output=True,
    )


def start_api() -> subprocess.Popen:
    log(f"starting FastAPI server on :{API_PORT}...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app",
         "--port", str(API_PORT), "--log-level", "error"],
        env={**os.environ, "REENTRY_DB": DB, "PYTHONPATH": str(REPO)},
        cwd=REPO,
    )


def start_web() -> subprocess.Popen:
    log(f"starting Next.js on :{WEB_PORT}...")
    return subprocess.Popen(
        ["npm", "--prefix", "web", "run", "start", "--", "--port", str(WEB_PORT)],
        env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"},
        cwd=REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_port(port: int, timeout_s: float = 20.0) -> bool:
    import socket
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def run_screenshots() -> None:
    from playwright.sync_api import sync_playwright

    ASSETS.mkdir(parents=True, exist_ok=True)
    base = f"http://localhost:{WEB_PORT}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2,  # 2x / high-DPI
        )
        page = ctx.new_page()

        log("navigating to capsule view...")
        page.goto(base, wait_until="networkidle")
        page.wait_for_selector(".panel", timeout=15_000)

        # 1. Full capsule view with contradiction flagged.
        path = ASSETS / "capsule-view.png"
        page.screenshot(path=str(path), full_page=False)
        log(f"saved {path.name}")

        # 2. Entropy breakdown close-up.
        # Scroll to the entropy panel and capture.
        entropy_el = page.locator(".tape").first
        entropy_el.scroll_into_view_if_needed()
        page.locator("section.panel").first.screenshot(path=str(ASSETS / "entropy-gauge.png"))
        log("saved entropy-gauge.png")

        # 3. Evidence chip modal: click the first chip.
        first_chip = page.locator("button.ev-chip").first
        if first_chip.count():
            first_chip.click()
            page.wait_for_selector(".modal", timeout=5_000)
            page.screenshot(path=str(ASSETS / "evidence-modal.png"))
            log("saved evidence-modal.png")
            # Close modal.
            page.keyboard.press("Escape")
            page.locator(".modal-close").first.click(timeout=2_000)

        # 4. Pending action panel.
        action_panel = page.locator("text=Approve and run").first
        if action_panel.count():
            action_panel.scroll_into_view_if_needed()
            page.screenshot(path=str(ASSETS / "action-panel.png"))
            log("saved action-panel.png")

        # 5. Approve and show post-approval state (best-effort).
        approve_btn = page.locator("button.btn-approve").first
        if approve_btn.count():
            log("approving pending action to capture post-approval state...")
            try:
                approve_btn.click()
                # Wait for the page to refresh after the action completes.
                page.wait_for_timeout(6_000)
                page.screenshot(path=str(ASSETS / "after-approve.png"))
                log("saved after-approve.png")
            except Exception as exc:
                log(f"after-approve screenshot skipped: {exc}")

        browser.close()


def cleanup(api: subprocess.Popen, web: subprocess.Popen) -> None:
    for proc in (api, web):
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def main() -> int:
    # Clean up any previous run.
    subprocess.run(["rm", "-f", DB], check=False)
    subprocess.run(["rm", "-rf", PROJ], check=False)

    seed_demo()
    api = start_api()
    web = start_web()

    try:
        if not wait_for_port(API_PORT, timeout_s=15):
            print("ERROR: FastAPI server did not start.", file=sys.stderr)
            return 1
        log("API server is up")

        if not wait_for_port(WEB_PORT, timeout_s=30):
            print("ERROR: Next.js server did not start in time.", file=sys.stderr)
            print("  Make sure the build is current: npm --prefix web run build", file=sys.stderr)
            return 1
        log("web server is up")

        # Give Next.js a little extra time to warm up.
        time.sleep(2)

        run_screenshots()
        log("all screenshots saved to docs/assets/")
        return 0
    finally:
        cleanup(api, web)


if __name__ == "__main__":
    sys.exit(main())
