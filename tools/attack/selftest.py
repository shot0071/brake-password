#!/usr/bin/env python3
# ============================================================
#  HackLock - self-test of the whole experiment (emulator only)
#
#  Runs the full experiment against the desktop emulator and checks
#  that the result is "crisp":
#    - vulnerable firmware: the attack recovers the PIN, and response
#      time rises strictly with each correct digit (a clean staircase);
#    - hardened firmware: the attack FAILS, and response time is flat.
#  Then it regenerates the comparison plot.
#
#  Exit code 0 = all checks passed, 1 = something is off.
#  No hardware needed. Run it any time to confirm the experiment
#  still behaves:  python selftest.py
# ============================================================

import csv
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import attack  # noqa: E402

EMULATOR = os.path.join(HERE, "..", "emulator", "emulator.py")
MEAS_DIR = os.path.join(HERE, "..", "..", "measurements")
SECRET = "1379"


def start_emulator(mode, port):
    p = subprocess.Popen(
        [sys.executable, EMULATOR, "--mode", mode, "--port", str(port), "--secret", SECRET],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.0)
    return p


def medians_by_prefix(csv_path):
    groups = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            groups.setdefault(int(row["correct_prefix"]), []).append(float(row["elapsed_us"]))
    return {k: statistics.median(v) for k, v in sorted(groups.items())}


def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    return ok


def run():
    os.makedirs(MEAS_DIR, exist_ok=True)
    passed = True

    # --- vulnerable: attack must work, staircase must rise ---
    print("vulnerable firmware:")
    emu = start_emulator("vulnerable", 5700)
    try:
        dev = attack.open_target("tcp:127.0.0.1:5700")
        recovered = attack.recover(dev, len(SECRET), "0123456789", 15, "0")
        dev.close()
        passed &= check("attack recovers the PIN", recovered == SECRET,
                        f"got {recovered}, expected {SECRET}")

        vuln_csv = os.path.join(MEAS_DIR, "vulnerable.csv")
        dev = attack.open_target("tcp:127.0.0.1:5700")
        attack.measure(dev, len(SECRET), 25, vuln_csv, "0")
        dev.close()
    finally:
        emu.terminate(); emu.wait()

    med = medians_by_prefix(vuln_csv)
    steps = [med[k + 1] - med[k] for k in range(len(med) - 1)]
    passed &= check("response time rises every step", all(s > 500 for s in steps),
                    "steps(us)=" + ", ".join(f"{s:.0f}" for s in steps))

    # --- hardened: attack must fail, timing must be flat ---
    print("hardened firmware:")
    emu = start_emulator("hardened", 5701)
    try:
        dev = attack.open_target("tcp:127.0.0.1:5701")
        recovered_h = attack.recover(dev, len(SECRET), "0123456789", 15, "0")
        dev.close()
        passed &= check("attack FAILS (as it should)", recovered_h != SECRET,
                        f"recovered {recovered_h}")

        hard_csv = os.path.join(MEAS_DIR, "hardened.csv")
        dev = attack.open_target("tcp:127.0.0.1:5701")
        attack.measure(dev, len(SECRET), 25, hard_csv, "0", SECRET)
        dev.close()
    finally:
        emu.terminate(); emu.wait()

    med_h = medians_by_prefix(hard_csv)
    spread = max(med_h.values()) - min(med_h.values())
    passed &= check("response time stays flat", spread < 1500, f"spread(us)={spread:.0f}")

    # --- regenerate the plot ---
    plot = os.path.join(MEAS_DIR, "leak.png")
    r = subprocess.run([sys.executable, os.path.join(HERE, "plot.py"),
                        vuln_csv, hard_csv, "--labels", "vulnerable", "hardened",
                        "--out", plot], capture_output=True, text=True)
    passed &= check("plot regenerated", r.returncode == 0 and os.path.exists(plot))

    print("\n" + ("ALL GOOD - the experiment is crisp." if passed
                  else "SOMETHING IS OFF - see the FAIL lines above."))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
