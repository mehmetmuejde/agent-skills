#!/usr/bin/env python3
"""Evaluate a `footprint --sample … -j <file>` recording of one macOS process.

Reads `samples[].processes[].footprint` (bytes) and `samples[].start_time.wall_time_s`,
drops the warm-up samples, fits a least-squares line and reports the growth rate in
MB per hour, the peak and the first/last footprint.

Exit codes: 0 = within budget, 1 = slope above --max-mb-per-hour, 2 = unusable input.
Standard library only; run with `python3 -I analyze_soak.py soak.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MB = 1024 * 1024


def load_series(path: Path, process: str | None) -> list[tuple[float, int]]:
    data = json.loads(path.read_text())
    bytes_per_unit = int(data.get("bytes per unit", 1))
    series: list[tuple[float, int]] = []
    for sample in data.get("samples", []):
        t = sample.get("start_time", {}).get("wall_time_s")
        procs = sample.get("processes", [])
        if process is not None:
            procs = [p for p in procs if p.get("name") == process or str(p.get("pid")) == process]
        if t is None or not procs:
            continue
        # Several matching processes (e.g. helpers with the same name): sum them.
        total = sum(int(p.get("footprint", 0)) for p in procs) * bytes_per_unit
        series.append((float(t), total))
    return series


def slope_per_hour(series: list[tuple[float, int]]) -> float:
    """Least-squares slope in bytes per hour."""
    n = len(series)
    t0 = series[0][0]
    xs = [t - t0 for t, _ in series]
    ys = [float(v) for _, v in series]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        return 0.0
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return cov / var_x * 3600.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("json_file", type=Path, help="footprint JSON written with -j")
    parser.add_argument("--max-mb-per-hour", type=float, default=5.0,
                        help="fail when the fitted growth exceeds this (default 5)")
    parser.add_argument("--warmup-samples", type=int, default=0,
                        help="number of leading samples to ignore (default 0)")
    parser.add_argument("--process", help="process name or pid to select (default: all)")
    args = parser.parse_args()

    try:
        series = load_series(args.json_file, args.process)
    except (OSError, ValueError) as error:
        print(f"error: cannot read {args.json_file}: {error}", file=sys.stderr)
        return 2

    series = series[args.warmup_samples:]
    if len(series) < 2:
        print("error: need at least two samples after warm-up", file=sys.stderr)
        return 2

    duration_min = (series[-1][0] - series[0][0]) / 60
    slope_mb = slope_per_hour(series) / MB
    peak_mb = max(v for _, v in series) / MB
    first_mb = series[0][1] / MB
    last_mb = series[-1][1] / MB

    print(f"samples:   {len(series)} over {duration_min:.1f} min")
    print(f"footprint: first {first_mb:.1f} MB, last {last_mb:.1f} MB, peak {peak_mb:.1f} MB")
    print(f"slope:     {slope_mb:+.2f} MB/hour (budget {args.max_mb_per_hour:.2f})")

    if slope_mb > args.max_mb_per_hour:
        print("result:    FAIL - footprint keeps growing")
        return 1
    print("result:    ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
