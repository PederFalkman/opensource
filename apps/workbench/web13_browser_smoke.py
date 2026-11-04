#!/usr/bin/env python3
"""WEB-13 manually invoked synthetic-only browser smoke; never scheduled.

Requires a locally built candidate wheel, installed energydata-kit and Playwright.
No customer files or remote deployment. Validates the *new* review UI, not WEB-09.
"""
from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent
ASSETS = (
    "web13_synthetic_review.html",
    "web13_pilot_state.mjs",
    "web14_evidence.mjs",
    "web09_candidate_loader.mjs",
    "web09_engine_worker.mjs",
)
SCENARIOS = ("baseline", "dst_fall", "dst_spring", "mixed_offsets")


def reference_rows(scenario: str) -> list[list[str]]:
    """Independent local reference input for the fixed Worker fixtures."""
    if scenario not in SCENARIOS:
        raise ValueError("Unsupported synthetic scenario")
    if scenario == "baseline":
        start = datetime(2026, 10, 19, tzinfo=timezone.utc)
        rows = [["timestamp", "power_kw"]]
        for i in range(96):
            if i in (28, 29):
                continue
            value = "" if i == 62 else f"{440 + 75*math.sin(i/8) + 20*math.cos(i/3):.2f}"
            instant = (start + timedelta(minutes=15*i)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            row = [instant, value]
            rows.append(row)
            if i == 54:
                rows.append(list(row))
        return rows
    fixtures = {
        "dst_fall": [
            ["2026-10-25T01:30:00+02:00", "1"],
            ["2026-10-25T02:00:00+02:00", "2"],
            ["2026-10-25T02:30:00+02:00", "3"],
            ["2026-10-25T02:00:00+01:00", "4"],
            ["2026-10-25T02:30:00+01:00", "5"],
        ],
        "dst_spring": [
            ["2026-03-29T01:30:00+01:00", "1"],
            ["2026-03-29T01:45:00+01:00", "2"],
            ["2026-03-29T03:00:00+02:00", "3"],
            ["2026-03-29T03:15:00+02:00", "4"],
        ],
        "mixed_offsets": [
            ["2026-01-01T00:00:00Z", "1"],
            ["2026-01-01T01:15:00+01:00", "2"],
            ["2026-01-01T00:30:00Z", ""],
            ["2026-01-01T01:45:00+01:00", "4"],
        ],
    }
    return [["timestamp", "power_kw"], *fixtures[scenario]]


def load_local_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, APP / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load local reference helper: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass


def manifest_for(wheel: Path) -> dict[str, object]:
    data = wheel.read_bytes()
    asset = {"path": wheel.name, "bytes": len(data),
             "sha256": hashlib.sha256(data).hexdigest()}
    return {"schema_version": "1", "status": "candidate-not-approved",
            "purpose": "review-only-static-asset-inventory",
            "total_bytes": len(data), "assets": [asset]}


def run(wheel: Path, browser_name: str, timeout_ms: int) -> int:
    if browser_name not in ("chromium", "firefox", "webkit"):
        raise ValueError("Unsupported browser")
    if not wheel.is_file() or not wheel.name.startswith("energydata_kit-") or wheel.suffix != ".whl":
        raise ValueError("Locally built EnergyData Kit wheel required")
    if not 0 < wheel.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError("Wheel must be within 10 MiB")
    from playwright.sync_api import sync_playwright
    adapter = load_local_module("python_report.py", "web13_local_adapter")
    parity = load_local_module("compare_parity.py", "web13_parity")

    with tempfile.TemporaryDirectory(prefix="web13-review-") as temporary:
        root = Path(temporary)
        for asset in ASSETS:
            shutil.copyfile(APP / asset, root / asset)
        candidate = root / "candidate-assets"
        candidate.mkdir()
        shutil.copyfile(wheel, candidate / wheel.name)
        manifest_bytes = json.dumps(manifest_for(wheel), sort_keys=True).encode("utf-8")
        (candidate / "manifest.json").write_bytes(manifest_bytes)
        # This is a synthetic test receipt only, not independently authorized provenance.
        reviewed_pin = hashlib.sha256(manifest_bytes).hexdigest()
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        outcomes: list[dict[str, object]] = []
        errors: list[str] = []
        try:
            with sync_playwright() as playwright:
                browser = getattr(playwright, browser_name).launch()
                try:
                    context = browser.new_context(accept_downloads=True)
                    page = context.new_page()
                    page.on("pageerror", lambda exc: errors.append(str(exc)))
                    page.goto(
                        f"http://127.0.0.1:{server.server_address[1]}/web13_synthetic_review.html")
                    if page.locator("input[type=file]").count() != 0:
                        raise RuntimeError("Review pilot unexpectedly accepts local files")
                    # No candidate fetch may occur without a separately supplied pin.
                    manifest_requests = []
                    page.on("request", lambda req: manifest_requests.append(req.url)
                            if req.url.endswith("/candidate-assets/manifest.json") else None)
                    page.locator("#run").click()
                    if "reviewed manifest SHA-256 is required" not in page.locator("#status").inner_text():
                        raise RuntimeError("Missing manifest pin did not fail closed")
                    if manifest_requests:
                        raise RuntimeError("Manifest fetched before independent pin supplied")
                    page.locator("#reviewPin").fill("0" * 64)
                    page.locator("#run").click()
                    page.wait_for_function(
                        "() => !document.querySelector('#run').disabled", timeout=10000)
                    if "SHA-256 mismatch" not in page.locator("#status").inner_text():
                        raise RuntimeError("Incorrect review pin was not rejected")
                    if page.locator("#export").is_enabled():
                        raise RuntimeError("Export must remain disabled after invalid review pin")
                    page.locator("#reviewPin").fill(reviewed_pin)
                    # Cancel a pending package request and ensure stale responses do not win.
                    page.route("**/candidate-assets/manifest.json", lambda route: None)
                    with page.expect_request("**/candidate-assets/manifest.json", timeout=10000):
                        page.locator("#run").click()
                    page.locator("#cancel").click()
                    if "Cancelled" not in page.locator("#status").inner_text():
                        raise RuntimeError("Cancellation not reflected in UI")
                    if page.locator("#export").is_enabled():
                        raise RuntimeError("Export must be disabled after cancel")
                    page.unroute("**/candidate-assets/manifest.json")

                    for scenario in SCENARIOS:
                        page.locator("#scenario").select_option(scenario)
                        page.locator("#run").click()
                        page.wait_for_function(
                            """() => !document.querySelector('#run').disabled &&
                             (document.querySelector('#status').textContent.includes('not independently attested') ||
                              document.querySelector('#status').textContent.includes('Failed'))""",
                            timeout=timeout_ms)
                        status = page.locator("#status").inner_text()
                        if "Failed" in status:
                            raise RuntimeError(f"{scenario}: {status}")
                        result = json.loads(page.locator("#result").inner_text())
                        if result.get("status") != "internal-unattested-synthetic-only":
                            raise RuntimeError("Missing synthetic-only evidence classification")
                        if result.get("scenario") != scenario:
                            raise RuntimeError("Wrong scenario in evidence")
                        if result.get("result", {}).get("report", {}).get("schema_version") != "2":
                            raise RuntimeError("Canonical report schema mismatch")
                        if result.get("wheel_sha256") != hashlib.sha256(wheel.read_bytes()).hexdigest():
                            raise RuntimeError("Wheel fingerprint mismatch in evidence")
                        # Compare every canonical field to an independent local Python
                        # assessment, not just success/schema/selected headline metrics.
                        csv_path = root / f"{scenario}-reference.csv"
                        with csv_path.open("w", newline="", encoding="utf-8") as stream:
                            csv.writer(stream).writerows(reference_rows(scenario))
                        reference = adapter.analyze_csv(
                            csv_path, timestamp="timestamp", value="power_kw"
                        )
                        differences = parity.changes(
                            parity.canonical(reference),
                            parity.canonical(result["result"]),
                        )
                        if differences:
                            raise RuntimeError(
                                f"{scenario}: canonical parity failed with {len(differences)} differences: "
                                + "; ".join(differences[:8])
                            )
                        with page.expect_download() as downloaded:
                            page.locator("#export").click()
                        export = downloaded.value
                        if export.suggested_filename != "energydata-synthetic-review-evidence.json":
                            raise RuntimeError("Unexpected evidence filename")
                        export_path = root / f"{scenario}-export.json"
                        export.save_as(str(export_path))
                        if json.loads(export_path.read_text(encoding="utf-8")) != result:
                            raise RuntimeError("Export does not match displayed evidence")
                        outcomes.append({"scenario": scenario, "status": "PASS",
                                         "canonical_schema": "2", "parity": "PASS", "field_differences": 0, "export": "PASS"})
                    context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        print(json.dumps({"browser": browser_name, "cases": outcomes,
                          "page_errors": errors, "synthetic_only": True}, indent=2))
        return 0 if len(outcomes) == 4 and not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--timeout-ms", type=int, default=300000)
    args = parser.parse_args()
    if not 1000 <= args.timeout_ms <= 300000:
        parser.error("Timeout must be within 1000–300000 ms")
    try:
        return run(args.wheel, args.browser, args.timeout_ms)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f"WEB-13 SMOKE FAILED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
