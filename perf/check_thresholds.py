"""Fail (exit 1) if a load-test run breaks the agreed limits. Reads Locust's *_stats.csv.

Usage: python perf/check_thresholds.py perf/results_stats.csv [--p95-ms 500] [--max-fail-pct 1]
"""
import argparse
import csv
import sys

ap = argparse.ArgumentParser()
ap.add_argument("csv_file")
ap.add_argument("--p95-ms", type=float, default=500, help="max allowed 95th percentile response time (ms)")
ap.add_argument("--max-fail-pct", type=float, default=1.0, help="max allowed failed requests in percent")
args = ap.parse_args()

problems = []
with open(args.csv_file, newline="") as f:
    for row in csv.DictReader(f):
        name = row["Name"]
        total = int(row["Request Count"])
        fails = int(row["Failure Count"])
        p95 = float(row["95%"])
        fail_pct = 100 * fails / total if total else 0
        status = "OK"
        if p95 > args.p95_ms:
            problems.append(f"{name}: p95 {p95:.0f} ms > {args.p95_ms:.0f} ms"); status = "SLOW"
        if fail_pct > args.max_fail_pct:
            problems.append(f"{name}: {fail_pct:.1f}% failed > {args.max_fail_pct}%"); status = "FAIL"
        print(f"{status:5} {name:28} requests={total:5} fail%={fail_pct:5.1f} p95={p95:6.0f}ms")

if problems:
    print("\nTHRESHOLDS BROKEN:\n  " + "\n  ".join(problems))
    sys.exit(1)
print("\nAll thresholds met.")
