"""Automated High-Resolution Screenshot Capture using Playwright.
Captures genuine screenshots of SentinelVault running on http://localhost:5173
with backend running on http://127.0.0.1:8000.
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = REPO_ROOT / "screenshots" / "hackbridge"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1/9] Loading Login Page...")
        page.goto("http://localhost:5173", wait_until="networkidle")
        time.sleep(1)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_login_view.png"))

        # Log in with analyst credentials
        print("[2/9] Authenticating as analyst_user...")
        sign_in_btn = page.locator("button:has-text('Sign In to Gateway')").first
        if sign_in_btn.is_visible():
            sign_in_btn.click()
            page.wait_for_selector("text=Welcome back", timeout=10000)
            time.sleep(1.5)

        print("[3/9] Capturing Dashboard (homepage.png)...")
        page.screenshot(path=str(SCREENSHOTS_DIR / "homepage.png"))

        print("[4/9] Navigating to Dataset Selection (dataset_selection.png)...")
        page.locator("button:has-text('Select Dataset')").first.click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "dataset_selection.png"))

        print("[5/9] Navigating to Query Builder (feature_1.png / query_builder.png)...")
        page.locator("button:has-text('Query Builder')").first.click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "query_builder.png"))
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature_1.png"))

        print("[6/9] Running Query to capture Results...")
        run_btn = page.locator("button:has-text('Run Query')").first
        if run_btn.is_visible():
            run_btn.click()
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOTS_DIR / "query_results.png"))

        print("[7/9] Navigating to Privacy Budget (feature_2.png / privacy_budget.png)...")
        page.locator("button:has-text('Privacy Budget')").first.click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "privacy_budget.png"))
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature_2.png"))

        print("[8/9] Navigating to Privacy Receipts (privacy_receipt.png)...")
        page.locator("button:has-text('Privacy Receipts')").first.click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "privacy_receipt.png"))

        print("[9/9] Navigating to Audit Logs & Security Events...")
        page.locator("button:has-text('Audit Logs')").first.click()
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "audit_logs.png"))

        sec_btn = page.locator("button:has-text('Security Events')").first
        if sec_btn.is_visible():
            sec_btn.click()
            time.sleep(1.5)
            page.screenshot(path=str(SCREENSHOTS_DIR / "security_events.png"))

        browser.close()
        print(f"\n[SUCCESS] All screenshots successfully saved to {SCREENSHOTS_DIR}")

if __name__ == "__main__":
    capture_all()
