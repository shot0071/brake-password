#!/usr/bin/env python3
# ============================================================
#  HackLock - live timing demo
#
#  A tiny interactive front-end for the lock. You type a PIN, press
#  Enter, and immediately see three things:
#    - the answer            (OK = correct, NO = wrong)
#    - how long it took      (round-trip time in milliseconds)
#    - a proportional bar    (one '#' per fixed slice of time)
#
#  The bar makes the timing leak visible WITHOUT a graph: on the leaky
#  firmware a guess with more correct leading digits comes back slower,
#  so its bar is longer. On the hardened firmware every bar is the same
#  length, whatever you type.
#
#  It speaks the same protocol as attack.py and REUSES that file's
#  transport code (open_target), so it takes the SAME --target option
#  and works against the emulator or a real board:
#
#    python live.py --target tcp:127.0.0.1:5555     (emulator)
#    python live.py --target serial:COM3:115200     (real board)
#
#  Nice sequence to try on the leaky firmware (secret 1379):
#    0000  ->  wrong, fastest, shortest bar   (0 correct leading digits)
#    1000  ->  slightly slower                (1 correct)
#    1370  ->  slower still                   (3 correct)
#    1379  ->  OK, slowest                    (all correct)
# ============================================================

import argparse

# Reuse attack.py's transports instead of duplicating them. Running this
# script puts its own folder (tools/attack) on the import path, so the
# plain "import" works from anywhere you launch it.
from attack import open_target

# One '#' in the bar stands for this many milliseconds. It is only a rough
# visual scale: lower it if the bars are too short to tell apart, raise it
# if they run off the edge of your terminal.
MS_PER_HASH = 0.2
MAX_BAR = 80            # never draw a bar longer than this many characters


def bar(ms):
    """Build a simple proportional '#' bar for a time in milliseconds."""
    n = min(int(ms / MS_PER_HASH), MAX_BAR)
    return "#" * n


def main():
    ap = argparse.ArgumentParser(description="HackLock live timing demo")
    ap.add_argument("--target", required=True,
                    help="tcp:host:port  or  serial:port:baud  (same as attack.py)")
    args = ap.parse_args()

    dev = open_target(args.target)
    print("HackLock live demo - type a PIN and press Enter.")
    print("Empty line or Ctrl+C to quit.\n")
    try:
        while True:
            pin = input("PIN> ").strip()
            if not pin:
                break
            answer, dt = dev.try_pin(pin)     # send TRY <pin>, time the reply
            ms = dt * 1000.0
            print(f"  {answer:<3} {ms:8.2f} ms  {bar(ms)}")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        dev.close()


if __name__ == "__main__":
    main()
