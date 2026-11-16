#!/usr/bin/env python3
# ============================================================
#  HackLock - physical keypad monitor
#
#  A READ-ONLY serial viewer for the board. It never sends anything;
#  it just opens the port and prints what the firmware says. When a
#  line is the firmware's "RESULT <OK|NO> <microseconds>" summary, it
#  shows the answer and a proportional '#' bar, so someone watching the
#  terminal sees instantly whether the last physical keypad entry was
#  fast (wrong) or slow (more correct leading digits) on the leaky
#  firmware. Every other line (the "*" key echo, "cleared", the
#  "HackLock ready." banner, ...) is printed as-is.
#
#  Flash the board, then:
#    python monitor.py --target serial:COM3:115200
#  Now type PINs on the physical keypad and press '#'.
# ============================================================

import argparse
import re
import time

# The firmware prints exactly:  RESULT OK 6000   /   RESULT NO 2921
RESULT_RE = re.compile(r"^RESULT (OK|NO) (\d+)$")
US_PER_HASH = 200          # one '#' in the bar per 200 microseconds of compare time


def open_serial(spec):
    """Open the port named by a 'serial:port:baud' target for reading only."""
    import serial  # pip install pyserial
    parts = spec.split(":")
    if parts[0].lower() != "serial" or len(parts) < 2:
        raise ValueError(f"bad --target: {spec!r} (use serial:port:baud)")
    port = parts[1]
    baud = int(parts[2]) if len(parts) > 2 else 115200
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2.0)            # wait out the ESP32 auto-reset that opening triggers
    ser.reset_input_buffer()
    return ser


def main():
    ap = argparse.ArgumentParser(description="HackLock read-only keypad monitor")
    ap.add_argument("--target", required=True, help="serial:port:baud")
    args = ap.parse_args()

    ser = open_serial(args.target)
    print(f"Monitoring {args.target}  (read-only - nothing is sent; Ctrl+C to stop)")
    print("Type a PIN on the keypad and press '#'.\n")
    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue                         # read timeout, nothing arrived
            line = raw.decode(errors="replace").rstrip("\r\n")
            if not line:
                continue
            m = RESULT_RE.match(line)
            if m:
                answer, us = m.group(1), int(m.group(2))
                bar = "#" * (us // US_PER_HASH)
                print(f"  {answer:<3} {us:6d} us  {bar}")
            else:
                print(line)                      # pass normal firmware output through
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
