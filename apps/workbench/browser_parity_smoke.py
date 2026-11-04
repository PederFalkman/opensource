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


def transfer_snapshot(events: list[dict[str, Any]]) -> dict[str, int]:
    """CDP encoded transfer bytes (not unpacked dependency, memory or disk sizes)."""
    remote = [event for event in events if event["host"] not in {"localhost", "127.0.0.1"}]
    local = [event for event in events if event["host"] in {"localhost", "127.0.0.1"}]
    return {
        "external_encoded_bytes": sum(int(item["encoded_bytes"]) for item in remote),
        "local_encoded_bytes": sum(int(item["encoded_bytes"]) for item in local),
        "completed_requests": len(events),
        "external_completed_requests": len(remote),
    }


def v8_heap_snapshot(session: Any) -> dict[str, int | None]:
    """V8 heap only; does not cover WebAssembly linear or native browser memory."""
    values = {m["name"]: m["value"] for m in session.send("Performance.getMetrics")["metrics"]}
    return {
        "js_heap_used_bytes": int(values["JSHeapUsedSize"]) if "JSHeapUsedSize" in values else None,
        "js_heap_total_bytes": int(values["JSHeapTotalSize"]) if "JSHeapTotalSize" in values else None,
    }



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
                    # Chromium-specific diagnostics, not full process/network accounting.
                    session = page.context.new_cdp_session(page)
                    session.send("Network.enable")
                    session.send("Performance.enable")
                    request_hosts: dict[str, str] = {}
                    completed_transfers: list[dict[str, Any]] = []

                    def on_request(event: dict[str, Any]) -> None:
                        request_hosts[event["requestId"]] = (
                            urlsplit(event["request"]["url"]).hostname or "<unknown>"
                        )

                    def on_finished(event: dict[str, Any]) -> None:
                        completed_transfers.append({
                            "host": request_hosts.get(event["requestId"], "<unknown>"),
                            "encoded_bytes": max(0, int(event.get("encodedDataLength", 0))),
                        })

                    session.on("Network.requestWillBeSent", on_request)
                    session.on("Network.loadingFinished", on_finished)
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
                    if page.evaluate("globalThis.__edkSyntheticFixtureForTest?.() ?? null") != grid:
                        raise RuntimeError("Browser baseline fixture diverges from Workbench")
                    if page.locator('input[type="file"]').count() != 1:
                        raise RuntimeError("Experiment must not accept customer CSV uploads")
                    page.locator("#wheel").set_input_files(str(wheel))
                    page.locator("#wheelHash").fill(digest)
                    scenarios = ("baseline", "dst_fall", "dst_spring", "mixed_offsets")
                    checks: list[dict[str, Any]] = []
                    transfer_before = len(completed_transfers)
                    for scenario in scenarios:
                        page.locator("#scenario").select_option(scenario)
                        fixture = page.evaluate(
                            "(name) => globalThis.__edkSyntheticScenarioForTest(name)", scenario
                        )
                        if not fixture or fixture[0] != ["timestamp", "power_kw"]:
                            raise RuntimeError(f"Invalid hard-coded synthetic fixture: {scenario}")
                        with csv_file.open("w", encoding="utf-8", newline="") as stream:
                            csv.writer(stream).writerows(fixture)
                        local = adapter.analyze_csv(
                            csv_file, timestamp="timestamp", value="power_kw"
                        )
                        start_case = time.perf_counter()
                        page.locator("#run").click()
                        try:
                            page.wait_for_function(
                                "() => !document.querySelector('#run').disabled && "
                                "(document.querySelector('#status').textContent.includes('Python returned') || "
                                "document.querySelector('#status').textContent.includes('Experiment failed'))",
                                timeout=timeout_ms,
                            )
                        except Exception as exc:
                            raise RuntimeError(
                                f"Pyodide did not finish scenario {scenario} within {timeout_ms} ms"
                            ) from exc
                        seconds = round(time.perf_counter() - start_case, 2)
                        status = page.locator("#status").inner_text()
                        if not status.startswith("Python returned"):
                            raise RuntimeError(f"{scenario}: {status}")
                        raw_report = page.locator("#result").inner_text()
                        try:
                            browser_report = json.loads(raw_report)
                        except json.JSONDecodeError as exc:
                            raise RuntimeError(
                                f"{scenario}: browser returned invalid JSON; status={status!r}; "
                                f"first_chars={raw_report[:120]!r}"
                            ) from exc
                        differences = parity.changes(
                            parity.canonical(local), parity.canonical(browser_report)
                        )
                        case_transfers = transfer_snapshot(completed_transfers[transfer_before:])
                        transfer_before = len(completed_transfers)
                        checks.append({
                            "network": case_transfers,
                            "v8_heap_after_run": v8_heap_snapshot(session),
                            "scenario": scenario,
                            "rows": len(fixture) - 1,
                            "elapsed_seconds": seconds,
                            "canonical_parity": "PASS" if not differences else "FAIL",
                            "field_differences": differences[:50],
                        })
                    print(json.dumps({
                        "runtime_status": "Python executed in Chromium/Pyodide",
                        "wheel_sha256": digest,
                        "wheel_file_bytes": wheel.stat().st_size,
                        "measurement_limits": "CDP bytes exclude incomplete/cached transfers; V8 heap excludes WASM and native memory.",
                        "scenario_results": checks,
                        "external_hosts": sorted(external_hosts),
                        "page_errors": errors,
                        "suspected_outbound_dataset_payload_requests": network_payload_alerts,
                    }, indent=2, sort_keys=True))
                    if errors or network_payload_alerts or any(
                        case["canonical_parity"] != "PASS" for case in checks
                    ):
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
