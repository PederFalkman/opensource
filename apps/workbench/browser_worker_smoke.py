#!/usr/bin/env python3
"""WEB-09 optional real Chromium test: staged, checked wheel -> Worker -> Python.

Synthetic-only, ephemeral loopback static server. No deployment, customer files,
or persistent candidate-assets directory. Requires playwright, Chromium and
local energydata-kit installed from the repository source. This does NOT
validate signed release provenance or cross-browser compatibility.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

APP = Path(__file__).resolve().parent
PAGES = (
    "web09_worker_pilot.html",
    "web09_engine_worker.mjs",
    "web09_candidate_loader.mjs",
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


def load_helper(filename: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, APP / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(wheel: Path, *, timeout_ms: int = 180_000) -> int:
    if not wheel.is_file() or not wheel.name.startswith("energydata_kit-") or wheel.suffix != ".whl":
        raise ValueError("A locally built EnergyData Kit wheel is required")
    if wheel.stat().st_size > 10*1024*1024:
        raise ValueError("Wheel exceeds 10 MiB")
    adapter = load_helper("python_report.py", "web09_python_adapter")
    parity = load_helper("compare_parity.py", "web09_parity")
    inventory = load_helper("build_asset_manifest.py", "web09_manifest")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install playwright and its Chromium browser") from exc

    with tempfile.TemporaryDirectory(prefix="web09-synthetic-") as temporary:
        root = Path(temporary)
        for filename in PAGES:
            shutil.copyfile(APP / filename, root / filename)
        assets = root / "candidate-assets"
        assets.mkdir()
        shutil.copyfile(wheel, assets / wheel.name)
        result_manifest = inventory.build_manifest(assets)
        (assets / "manifest.json").write_text(
            json.dumps(result_manifest,sort_keys=True), encoding="utf-8"
        )
        server = ThreadingHTTPServer(
            ("127.0.0.1",0),partial(QuietHandler,directory=str(root))
        )
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page()
                    exceptions: list[str] = []
                    hosts: set[str] = set()
                    page.on("pageerror",lambda err: exceptions.append(str(err)))
                    from urllib.parse import urlsplit
                    page.on("request",lambda req: hosts.add(urlsplit(req.url).hostname or "unknown"))
                    page.goto(
                        f"http://127.0.0.1:{server.server_address[1]}/web09_worker_pilot.html"
                    )
                    # Verify real-browser cancel and immediate retry before parity.
                    # The first request is intentionally cancelled; it must leave
                    # no report and must not allow late worker messages to win.
                    page.locator("#scenario").select_option("baseline")
                    page.locator("#run").click()
                    page.locator("#cancel").click()
                    if "Cancelled" not in page.locator("#status").inner_text():
                        raise RuntimeError("Cancel did not enter cancelled state")
                    if page.locator("#result").inner_text() != "No report.":
                        raise RuntimeError("Cancelled run left a stale report")
                    if page.locator("#run").is_disabled():
                        raise RuntimeError("Run did not recover after cancellation")
                    page.wait_for_timeout(150)
                    if "Cancelled" not in page.locator("#status").inner_text():
                        raise RuntimeError("Late message overwrote cancelled state")
                    # The normal scenario matrix below verifies that a fresh
                    # worker and a new asset fetch can recover after cancellation.
                    # Build independent Python reference fixtures; none are user-provided.
                    grid=[["timestamp","power_kw"]]
                    import math
                    from datetime import datetime, timedelta, timezone
                    start=datetime(2026,10,19,tzinfo=timezone.utc)
                    for i in range(96):
                        if i in (28,29):
                            continue
                        value="" if i==62 else f"{440+75*math.sin(i/8)+20*math.cos(i/3):.2f}"
                        row=[(start+timedelta(minutes=i*15)).isoformat(timespec="milliseconds").replace("+00:00","Z"),value]
                        grid.append(row)
                        if i==54:
                            grid.append(list(row))
                    fixtures = {
                        "baseline": grid,
                        "dst_fall": [["timestamp","power_kw"],
                            ["2026-10-25T01:30:00+02:00","1"],
                            ["2026-10-25T02:00:00+02:00","2"],
                            ["2026-10-25T02:30:00+02:00","3"],
                            ["2026-10-25T02:00:00+01:00","4"],
                            ["2026-10-25T02:30:00+01:00","5"]],
                        "dst_spring": [["timestamp","power_kw"],
                            ["2026-03-29T01:30:00+01:00","1"],
                            ["2026-03-29T01:45:00+01:00","2"],
                            ["2026-03-29T03:00:00+02:00","3"],
                            ["2026-03-29T03:15:00+02:00","4"]],
                        "mixed_offsets": [["timestamp","power_kw"],
                            ["2026-01-01T00:00:00Z","1"],
                            ["2026-01-01T01:15:00+01:00","2"],
                            ["2026-01-01T00:30:00Z",""],
                            ["2026-01-01T01:45:00+01:00","4"]]
                    }
                    comparisons=[]
                    for scenario, rows in fixtures.items():
                        page.locator("#scenario").select_option(scenario)
                        page.locator("#run").click()
                        page.wait_for_function(
                            "() => !document.querySelector('#run').disabled && "
                            "(document.querySelector('#status').textContent.includes('canonical v2 report') || "
                            "document.querySelector('#status').textContent.includes('failed') || "
                            "document.querySelector('#status').textContent.includes('Unexpected report'))",
                            timeout=timeout_ms,
                        )
                        status=page.locator("#status").inner_text()
                        if "canonical v2 report" not in status:
                            raise RuntimeError(
                                f"Worker pipeline failed for {scenario}: {status}; JS errors={exceptions}"
                            )
                        actual=json.loads(page.locator("#result").inner_text())
                        csv_path=root/"synthetic.csv"
                        with csv_path.open("w",newline="",encoding="utf-8") as stream:
                            csv.writer(stream).writerows(rows)
                        reference=adapter.analyze_csv(
                            csv_path,timestamp="timestamp",value="power_kw"
                        )
                        differences=parity.changes(
                            parity.canonical(reference),parity.canonical(actual)
                        )
                        comparisons.append({
                            "scenario":scenario,"rows":len(rows)-1,
                            "canonical_parity":"PASS" if not differences else "FAIL",
                            "differences":differences[:30],
                        })
                    print(json.dumps({
                        "worker_status":"Python executed in isolated worker",
                        "scenarios":comparisons,
                        "page_errors":exceptions,
                        "observed_hosts":sorted(hosts),
                        "candidate_sha256":hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    },indent=2,sort_keys=True))
                    return 1 if exceptions or any(
                        case["canonical_parity"]!="PASS" for case in comparisons
                    ) else 0
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel",type=Path,required=True)
    parser.add_argument("--timeout-ms",type=int,default=180000)
    args=parser.parse_args(argv)
    if not 1000 <= args.timeout_ms <= 300000:
        parser.error("Timeout must be within 1000–300000 ms")
    try:
        return run(args.wheel,timeout_ms=args.timeout_ms)
    except (RuntimeError,ValueError,OSError) as exc:
        print(f"WEB-09 SMOKE FAILED: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
