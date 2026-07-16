"""Capture real screenshots of the ReEntry web app against the seeded demo.

Run from the repo root:
    python3 scripts/screenshots.py
or via:
    make screenshots

Prerequisites:
    pip install -e . playwright
    python3 -m playwright install chromium
    npm --prefix web install && NEXT_PUBLIC_DEMO_MODE=true npm --prefix web run build
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
ASSETS = REPO / "docs" / "assets"
WEB_PORT = 3001  # separate port so it does not collide with a running dev server


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def start_web() -> subprocess.Popen:
    log(f"starting Next.js on :{WEB_PORT}...")
    return subprocess.Popen(
        ["npm", "--prefix", "web", "run", "start", "--", "--port", str(WEB_PORT)],
        env={
            **os.environ,
            "NEXT_TELEMETRY_DISABLED": "1",
            # The build is already compiled with NEXT_PUBLIC_DEMO_MODE=true.
            # This var is here for documentation; Next.js reads it at build time.
            "NEXT_PUBLIC_DEMO_MODE": "true",
        },
        cwd=REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_port(port: int, timeout_s: float = 30.0) -> bool:
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
    app_url = f"http://localhost:{WEB_PORT}/app"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2,
        )
        page = ctx.new_page()

        log("loading /app (demo mode)...")
        page.goto(app_url, wait_until="networkidle")
        # Wait for the capsule panel to be rendered.
        page.wait_for_selector(".panel", timeout=20_000)
        # Give animations time to settle.
        page.wait_for_timeout(1_500)

        # 1. Full capsule view.
        path = ASSETS / "capsule-view.png"
        page.screenshot(path=str(path), full_page=False)
        log(f"saved {path.name}")

        # 2. Entropy breakdown (first .panel element contains the gauge).
        page.locator(".panel").first.screenshot(path=str(ASSETS / "entropy-gauge.png"))
        log("saved entropy-gauge.png")

        # 3. Evidence chip modal: try chips in order until one shows real data.
        chips = page.locator("button.ev-chip").all()
        modal_saved = False
        for chip in chips:
            chip.click()
            try:
                # Wait briefly for the slide panel to appear.
                page.wait_for_selector(".slide-panel", timeout=3_000)
                # Check we have actual content (not an error message).
                slide = page.locator(".slide-panel")
                body_text = slide.locator(".slide-body").inner_text(timeout=3_000)
                if "not found" not in body_text.lower() and len(body_text.strip()) > 10:
                    page.screenshot(path=str(ASSETS / "evidence-modal.png"))
                    log("saved evidence-modal.png")
                    modal_saved = True
                    # Close the panel.
                    close = page.locator(".close-btn").first
                    if close.count():
                        close.click()
                    else:
                        page.keyboard.press("Escape")
                    page.wait_for_timeout(400)
                    break
                # Not the right chip; close and try next.
                close = page.locator(".close-btn").first
                if close.count():
                    close.click()
                else:
                    page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            except Exception:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

        if not modal_saved:
            log("WARNING: could not capture evidence-modal.png (no chip had live data)")

        # 4. Action panel (scroll to Approve button, capture full viewport).
        approve_text = page.locator("text=Approve and run").first
        if approve_text.count():
            approve_text.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            page.screenshot(path=str(ASSETS / "action-panel.png"))
            log("saved action-panel.png")

        # 5. After-approve: click Approve, wait for running/done state.
        approve_btn = page.locator(".btn-cyan").filter(has_text="Approve").first
        if approve_btn.count():
            log("clicking Approve to capture post-approval state...")
            try:
                approve_btn.click()
                page.wait_for_timeout(1_200)
                page.screenshot(path=str(ASSETS / "after-approve.png"))
                log("saved after-approve.png")
            except Exception as exc:
                log(f"after-approve screenshot skipped: {exc}")

        browser.close()


def cleanup(web: subprocess.Popen) -> None:
    try:
        web.terminate()
        web.wait(timeout=5)
    except Exception:
        try:
            web.kill()
        except Exception:
            pass


def main() -> int:
    web = start_web()
    try:
        if not wait_for_port(WEB_PORT, timeout_s=30):
            print("ERROR: Next.js server did not start in time.", file=sys.stderr)
            print(
                "  Make sure the build is current: "
                "NEXT_PUBLIC_DEMO_MODE=true npm --prefix web run build",
                file=sys.stderr,
            )
            return 1
        log("web server is up")
        time.sleep(1)
        run_screenshots()
        log("all screenshots saved to docs/assets/")
        return 0
    finally:
        cleanup(web)


if __name__ == "__main__":
    sys.exit(main())
