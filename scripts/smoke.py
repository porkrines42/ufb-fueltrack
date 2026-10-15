"""Exercise the static app without modifying source or existing browser data."""
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("CHROMIUM_PATH"):
            options["executable_path"] = os.environ["CHROMIUM_PATH"]
        browser = p.chromium.launch(**options)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(f"http://127.0.0.1:{server.server_port}/")
        assert response.status == 200
        assert page.title() == "UFB FuelTrack — Demo"
        logo = page.get_by_alt_text("United Food Brands").first
        assert logo.evaluate("image => image.complete && image.naturalWidth > 0")
        page.get_by_role("button", name="Enter FuelTrack").click()
        assert page.get_by_text("My fuel dashboard", exact=True).is_visible()
        page.get_by_role("button", name="+ Add receipt").click()
        assert page.get_by_role("heading", name="Upload gas receipt").is_visible()
        assert page.locator("#receiptImage").count() == 1
        page.locator(".modal .x").click()
        page.get_by_text("Sign out", exact=False).click()
        admin = page.locator("#account option").evaluate_all(
            "options => options.find(o => o.textContent.includes('Administrator')).value"
        )
        page.select_option("#account", admin)
        page.get_by_role("button", name="Enter FuelTrack").click()
        assert page.get_by_role("heading", name="Company overview").is_visible()
        page.locator(".side").get_by_text("Receipts", exact=False).click()
        assert page.locator("table tbody tr").count() > 0
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("h1").is_visible()
        assert not errors, errors
        from mobile_ux import run_mobile_ux
        run_mobile_ux(browser, f"http://127.0.0.1:{server.server_port}/")
        browser.close()
        print("PASS: branding, employee/admin login, dashboards, upload form, receipts, mobile; no JS errors")
finally:
    server.shutdown()
    server.server_close()
