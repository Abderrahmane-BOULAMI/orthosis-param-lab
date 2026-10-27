"""Screenshots of each dashboard tab (needs a running app: streamlit run app/dashboard.py)."""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
TABS = [("Design an orthosis", "design"), ("Why made-to-measure", "sizing"),
        ("Measurement assistant", "assistant"), ("Population checks", "population")]


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 1250}, device_scale_factor=1)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("text=Orthosis Param Lab", timeout=120_000)
        time.sleep(8)
        for tab, name in TABS:
            page.get_by_role("tab", name=tab).click()
            time.sleep(6)
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
        b.close()
    print("screenshots in", SHOTS)


if __name__ == "__main__":
    main()
