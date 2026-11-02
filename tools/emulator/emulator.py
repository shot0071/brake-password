#!/usr/bin/env python3
# ============================================================
#  HackLock - desktop emulator (no hardware needed)
#
#  Reproduces the lock's PIN-check timing on a PC so the whole
#  attack can be developed and demonstrated before the parts
#  arrive. It speaks the SAME protocol as the firmware over a
#  TCP socket:
#
#       client sends:  TRY 1234\n
#       emulator answers:  OK\n   or   NO\n
#
#  The two modes match the firmware exactly:
#    --mode vulnerable : early exit + extra time per correct digit
#    --mode hardened   : constant-time compare, fixed answer time
#
#  Run it, then point the attack tool at it:
#       python emulator.py --mode vulnerable
#       python attack.py --target tcp:127.0.0.1:5555 recover
# ============================================================

import argparse
import socket
import time

# Defaults mirror firmware/hacklock/hacklock.ino
SECRET  = "1379"
PIN_LEN = 4
LEAK_US = 1500      # extra time per correct digit (vulnerable)
RESP_US = 8000      # fixed total answer time (hardened)


def busy_wait_us(microseconds: float) -> None:
    """Spin for the given time. A real delay, so it shows up in measurements."""
    end = time.perf_counter_ns() + int(microseconds * 1000)
    while time.perf_counter_ns() < end:
        pass


def check_vulnerable(candidate: str) -> bool:
    """Leaky check: stop at the first wrong digit, pay LEAK_US per correct one."""
    for i in range(PIN_LEN):
        if i >= len(candidate) or candidate[i] != SECRET[i]:
            return False               # early exit -> time depends on correct prefix
        busy_wait_us(LEAK_US)          # each correct digit costs extra time
    return True


def check_hardened(candidate: str) -> bool:
    """Constant-time check: look at all digits, no early exit."""
    cand = (candidate + "\x00" * PIN_LEN)[:PIN_LEN]
    diff = 0
    for i in range(PIN_LEN):
        diff |= ord(cand[i]) ^ ord(SECRET[i])
    return diff == 0


def handle_attempt(candidate: str, mode: str) -> bool:
    # The input must be exactly PIN_LEN long, or "1379" and "137999" would both
    # pass (the check only looks at the first PIN_LEN digits). The length is
    # attacker-chosen, not secret, so this guard leaks nothing. Mirrors firmware.
    len_ok = (len(candidate) == PIN_LEN)
    if mode == "hardened":
        start = time.perf_counter_ns()
        ok = len_ok and check_hardened(candidate)
        # pad the whole attempt to a fixed duration
        while (time.perf_counter_ns() - start) < RESP_US * 1000:
            pass
        return ok
    return len_ok and check_vulnerable(candidate)


def serve(host: str, port: int, mode: str) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    print(f"HackLock emulator ready.  mode={mode}  secret={SECRET}")
    print(f"Listening on tcp://{host}:{port}   (Ctrl+C to stop)")
    try:
        while True:
            conn, addr = srv.accept()
            with conn, conn.makefile("rwb", buffering=0) as f:
                for raw in f:
                    line = raw.decode(errors="replace").strip()
                    if not line:
                        continue
                    if line.upper().startswith("TRY "):
                        candidate = line[4:].strip()
                        ok = handle_attempt(candidate, mode)
                        f.write(b"OK\n" if ok else b"NO\n")
                    elif line.upper() in ("QUIT", "EXIT"):
                        break
                    else:
                        f.write(b"NO\n")
    except KeyboardInterrupt:
        print("\nemulator stopped")
    finally:
        srv.close()


def main() -> None:
    global SECRET, PIN_LEN, LEAK_US, RESP_US
    ap = argparse.ArgumentParser(description="HackLock desktop emulator")
    ap.add_argument("--mode", choices=["vulnerable", "hardened"], default="vulnerable")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--secret", default=SECRET)
    ap.add_argument("--leak-us", type=int, default=LEAK_US)
    ap.add_argument("--resp-us", type=int, default=RESP_US)
    args = ap.parse_args()

    SECRET  = args.secret
    PIN_LEN = len(SECRET)
    LEAK_US = args.leak_us
    RESP_US = args.resp_us
    serve(args.host, args.port, args.mode)


if __name__ == "__main__":
    main()
