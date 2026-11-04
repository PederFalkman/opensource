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
                    page.locator("#run").click()
                    page.wait_for_function(
                        "() => document.querySelector('#status').textContent.includes('canonical v2 report') || "
                        "document.querySelector('#status').textContent.includes('failed') || "
                        "document.querySelector('#status').textContent.includes('Unexpected report')",
                        timeout=timeout_ms,
                    )
                    status=page.locator("#status").inner_text()
                    if "canonical v2 report" not in status:
                        raise RuntimeError(f"Worker pipeline failed: {status}; JS errors={exceptions}")
                    actual=json.loads(page.locator("#result").inner_text())
                    # Independently compute the actual Workbench fixture without
                    # reading any user-supplied CSV.
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
                    csv_path=root/"synthetic.csv"
                    with csv_path.open("w",newline="",encoding="utf-8") as stream:
                        csv.writer(stream).writerows(grid)
                    reference=adapter.analyze_csv(csv_path,timestamp="timestamp",value="power_kw")
                    differences=parity.changes(parity.canonical(reference),parity.canonical(actual))
                    print(json.dumps({
                        "worker_status":status,
                        "canonical_parity":"PASS" if not differences else "FAIL",
                        "differences":differences[:30],
                        "page_errors":exceptions,
                        "observed_hosts":sorted(hosts),
                        "candidate_sha256":hashlib.sha256(wheel.read_bytes()).hexdigest(),
                    },indent=2,sort_keys=True))
                    return 1 if differences or exceptions else 0
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
