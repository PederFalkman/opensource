#!/usr/bin/env python3
"""Optional, real-Chromium WEB-07 parity smoke test for synthetic data only.

Run from repository root:
    python -m pip install playwright
    python -m playwright install chromium
    python apps/workbench/browser_parity_smoke.py --wheel packages/energydata-kit/dist/energydata_kit-....whl

Also install the local energydata-kit package (`pip install -e packages/energydata-kit`).
This script uses localhost and CDN access, and does not use customer files.
NOT part of routine CI; run only after explicit environment/network approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


APP = Path(__file__).resolve().parent
MAX_WHEEL_BYTES = 10 * 1024 * 1024


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve static files only, bound to loopback."""

    def log_message(self, format: str, *args: Any) -> None:
        """Avoid writing request paths or content to logs."""


def load_python_file(filename: str, name: str) -> Any:
    """Import one local Python helper without depending on the current working directory."""
    spec = importlib.util.spec_from_file_location(name, APP / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(wheel: Path, *, timeout_ms: int = 180_000, headless: bool = True) -> int:
    """Compare genuine browser-runtime results with local canonical Python."""
    if not wheel.is_file() or not wheel.name.startswith("energydata_kit-") or wheel.suffix != ".whl":
        raise ValueError("Provide a trusted locally built energydata_kit-*.whl")
    if wheel.stat().st_size > MAX_WHEEL_BYTES:
        raise ValueError("Wheel exceeds 10 MiB limit")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    adapter = load_python_file("python_report.py", "workbench_python_report")
    parity = load_python_file("compare_parity.py", "workbench_parity")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install optional browser test dependency: python -m pip install playwright") from exc

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(APP)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    errors: list[str] = []
    external_hosts: set[str] = set()
    network_payload_alerts: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="edk-browser-parity-") as temp:
            csv_file = Path(temp) / "synthetic-example.csv"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=headless)
                try:
                    page = browser.new_page(accept_downloads=False)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    def monitor_request(req: Any) -> None:
                        parsed = urlsplit(req.url)
                        if parsed.hostname not in {"127.0.0.1", "localhost"}:
                            external_hosts.add(parsed.hostname or "<unknown>")
                        body = req.post_data or ""
                        if "2026-10-19T00:00:00" in body or "synthetic-example.csv" in body:
                            network_payload_alerts.append(req.url)
                    page.on("request", monitor_request)
                    page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
                    grid = page.evaluate("syntheticGrid()")
                    if len(grid) != 96:
                        raise RuntimeError("Unexpected browser fixture length")
                    with csv_file.open("w", encoding="utf-8", newline="") as stream:
                        csv.writer(stream).writerows(grid)
                    local = adapter.analyze_csv(csv_file, timestamp="timestamp", value="power_kw")
                    start = time.perf_counter()
                    page.goto(f"http://127.0.0.1:{port}/experimental_pyodide.html")
                    page.locator("#wheel").set_input_files(str(wheel))
                    page.locator("#wheelHash").fill(digest)
                    page.locator("#csv").set_input_files(str(csv_file))
                    page.locator("#run").click()
                    try:
                        page.wait_for_function(
                            "() => document.querySelector('#status').textContent.includes('Python returned') || "
                            "document.querySelector('#status').textContent.includes('Experiment failed')",
                            timeout=timeout_ms,
                        )
                    except Exception as exc:
                        raise RuntimeError(f"Runtime did not finish within {timeout_ms} ms") from exc
                    seconds = round(time.perf_counter() - start, 2)
                    status = page.locator("#status").inner_text()
                    if not status.startswith("Python returned"):
                        raise RuntimeError(status)
                    browser_report = json.loads(page.locator("#result").inner_text())
                    differences = parity.changes(
                        parity.canonical(local), parity.canonical(browser_report)
                    )
                    print(json.dumps({
                        "runtime_status": status,
                        "wheel_sha256": digest,
                        "elapsed_seconds": seconds,
                        "external_hosts": sorted(external_hosts),
                        "page_errors": errors,
                        "suspected_outbound_dataset_payload_requests": network_payload_alerts,
                        "canonical_parity": "PASS" if not differences else "FAIL",
                        "field_differences": differences[:50],
                    }, indent=2, sort_keys=True))
                    if errors or network_payload_alerts or differences:
                        return 1
                    return 0
                finally:
                    browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; synthetic-only smoke test is an optional manual gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path, help="Trusted local wheel to test")
    parser.add_argument("--timeout-ms", type=int, default=180_000)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    if not 1000 <= args.timeout_ms <= 600_000:
        parser.error("--timeout-ms must be 1000–600000")
    try:
        return run(args.wheel, timeout_ms=args.timeout_ms, headless=not args.headed)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"BROWSER TEST FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
