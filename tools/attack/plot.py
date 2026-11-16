#!/usr/bin/env python3
# ============================================================
#  HackLock - plot response time vs correct-prefix length
#
#  Turns the CSV from  attack.py measure  into the project's main
#  picture: the "staircase" that shows the timing leak.
#
#  Give it one CSV (vulnerable) or two (vulnerable + hardened) to
#  compare them side by side.
#
#    python plot.py vulnerable.csv
#    python plot.py vulnerable.csv hardened.csv --out leak.png
# ============================================================

import argparse
import csv
import statistics
from collections import defaultdict


def load(path):
    """Return {correct_prefix: [elapsed_us, ...]} from a measurement CSV."""
    groups = defaultdict(list)
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            groups[int(row["correct_prefix"])].append(float(row["elapsed_us"]))
    return groups


def summarise(path):
    groups = load(path)
    xs = sorted(groups)
    med = [statistics.median(groups[k]) for k in xs]
    err = [statistics.pstdev(groups[k]) if len(groups[k]) > 1 else 0 for k in xs]
    return xs, med, err


def main():
    ap = argparse.ArgumentParser(description="Plot HackLock timing measurements")
    ap.add_argument("csv", nargs="+", help="one or two measurement CSV files")
    ap.add_argument("--labels", nargs="+", help="legend labels (default: file names)")
    ap.add_argument("--out", default="timing.png")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = args.labels or [p.rsplit("/", 1)[-1] for p in args.csv]
    fig, ax = plt.subplots(figsize=(7, 4.5))

    for path, label in zip(args.csv, labels):
        xs, med, err = summarise(path)
        ax.errorbar(xs, med, yerr=err, marker="o", capsize=4, label=label)

    ax.set_xlabel("Number of correct leading digits")
    ax.set_ylabel("Median response time (microseconds)")
    ax.set_title("HackLock: response time leaks the correct prefix")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
