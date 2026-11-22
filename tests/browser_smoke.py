"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.locator("#ranking tr").first.wait_for()
                assert page.locator("#province").input_value() == "NS"
                assert "$" in page.locator("#value").inner_text()
                page.locator("#softwood").click()
                page.wait_for_function("document.querySelector('#period-title').textContent.includes('British Columbia')")
                assert page.locator("#product").input_value() == "softwood"
                page.locator("#mode").select_option("month")
                page.locator("#month").select_option("202301")
                page.wait_for_function("document.querySelector('#comparison').textContent.includes('outside')")
                page.locator("#destination").select_option("US")
                assert page.locator("#series tr").count() == 1
                with page.expect_download() as download:
                    page.locator("#download").click()
                assert download.value.suggested_filename.endswith(".csv")
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: trade presets, date ranges, file export and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
