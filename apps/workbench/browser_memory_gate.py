#!/usr/bin/env python3
"""WEB-10 optional real-browser RSS envelope around WEB-09 synthetic smoke.

The command delegates exclusively to the existing synthetic-only smoke harness.
It measures descendants of the launched Python harness process, which normally
contain Playwright's driver and browser subprocesses. It does not isolate
per-Worker WASM memory or prove freed memory after Worker. Run manually only.

Example after installing playwright, browser, build, package, psutil:
  python apps/workbench/browser_memory_gate.py --wheel /tmp/edk-wheel/*.whl
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from browser_memory_probe import MemorySampler, load_psutil

APP = Path(__file__).resolve().parent
SMOKE = APP / "browser_worker_smoke.py"


def run(wheel: Path, *, sample_ms: int = 100, timeout_ms: int = 180_000) -> int:
    """Run the current WEB-09 smoke harness and sample its child process RSS."""
    if not wheel.is_file() or not wheel.name.startswith("energydata_kit-") or wheel.suffix != ".whl":
        raise ValueError("Provide a trusted, locally built EnergyData Kit wheel")
    if wheel.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Wheel exceeds 10 MiB")
    if not 20 <= sample_ms <= 5000:
        raise ValueError("Sample interval must be 20–5000 ms")
    if not 1000 <= timeout_ms <= 300_000:
        raise ValueError("Smoke timeout must be 1000–300000 ms")
    psutil = load_psutil()
    command = [
        sys.executable, str(SMOKE), "--wheel", str(wheel.resolve()),
        "--timeout-ms", str(timeout_ms),
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace",
    )
    sampler = MemorySampler(psutil, root_pid=process.pid, interval_ms=sample_ms)
    sampler.start()
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout_ms / 1000 + 120)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        output, _ = process.communicate()
    finally:
        result = sampler.stop()
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    print(json.dumps({
        "schema_version": "web10.memory-envelope.v1",
        "synthetic_only": True,
        "smoke_exit_code": process.returncode,
        "smoke_timed_out": timed_out,
        "measurement": result.to_dict(),
        "interpretation": (
            "Sampled Playwright/browser descendant-process RSS, including possible shared "
            "memory double counting. Do not interpret peak or final RSS as Python/WASM "
            "memory use or proof that terminating an individual Worker freed memory."
        ),
    }, indent=2, sort_keys=True))
    return 2 if timed_out else (0 if process.returncode == 0 else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sample-ms", type=int, default=100)
    parser.add_argument("--timeout-ms", type=int, default=180_000)
    args = parser.parse_args(argv)
    try:
        return run(args.wheel, sample_ms=args.sample_ms, timeout_ms=args.timeout_ms)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"WEB-10 MEMORY GATE FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
