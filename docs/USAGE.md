# HackLock - how to use it

Two ways to run everything: **without hardware** (the emulator on your PC) and
**with hardware** (the ESP32 board). The attack tool is the same in both cases.

---

## A. Without hardware (emulator)

You only need Python 3. Open two terminals.

**Terminal 1 - start the lock (leaky version):**
```bash
cd tools/emulator
python emulator.py --mode vulnerable
```

**Terminal 2 - run the attack:**
```bash
cd tools/attack
python attack.py --target tcp:127.0.0.1:5555 recover --length 4
```
You should see it recover the PIN digit by digit and end with `-> OK`.

**Now prove the fix.** Stop the emulator (Ctrl+C) and restart it hardened:
```bash
python emulator.py --mode hardened
```
Run the same attack again - this time the recovered PIN is wrong, because the
timing no longer leaks. That contrast is the whole point of the project.

**Make the plot (the main picture):**
```bash
cd tools/attack
pip install -r requirements.txt          # first time only

# with the emulator running in --mode vulnerable:
python attack.py --target tcp:127.0.0.1:5555 measure --out ../../measurements/vulnerable.csv
# restart emulator in --mode hardened, then:
python attack.py --target tcp:127.0.0.1:5555 measure --out ../../measurements/hardened.csv

python plot.py ../../measurements/vulnerable.csv ../../measurements/hardened.csv \
       --labels vulnerable hardened --out ../../measurements/leak.png
```
`leak.png` shows a rising "staircase" for the vulnerable firmware (more correct
digits = more time) and a flat line for the hardened one.

---

## B. With hardware (ESP32 board)

### 1. Install the Arduino tools (once)
- Arduino IDE -> **Boards Manager** -> install **esp32** (by Espressif).
- **Library Manager** -> install **Keypad** and **ESP32Servo**.

### 2. Flash the firmware
- Open `firmware/hacklock/hacklock.ino`.
- At the top, choose the version:
  - `#define VULNERABLE 1` -> leaky (for the attack demo)
  - `#define VULNERABLE 0` -> hardened (for the fix demo)
- Select your board (e.g. "ESP32 Dev Module") and the right COM port, then Upload.

### 3. Try it by hand
- Open **Serial Monitor** at **115200** baud. You should see `HackLock ready.`
- On the keypad type `1379` then `#`. The green LED lights and the servo opens.
- A wrong PIN lights the red LED.

### 4. Run the attack over Serial
Close the Serial Monitor first (only one program can use the port).
```bash
cd tools/attack
pip install -r requirements.txt           # first time only

# Windows:
python attack.py --target serial:COM5:115200 recover --length 4
# Linux/macOS:
python attack.py --target serial:/dev/ttyUSB0:115200 recover --length 4
```
Replace `COM5` / `/dev/ttyUSB0` with your actual port (shown in the Arduino IDE).

Then re-flash with `#define VULNERABLE 0` and run the attack again to show it
fails against the hardened firmware. Use `measure` + `plot.py` exactly as in
section A to get the before/after plot from the real board.

---

## Protocol (what the tools and firmware say to each other)
```
PC -> lock:   TRY 1379\n
lock -> PC:   OK      (correct)   or   NO   (wrong)
```
On the keypad: 4 digits then `#` to confirm, `*` to clear.

## Tuning the demo
In the firmware (and matching flags on the emulator):
- `SECRET` - the PIN (default `1379`).
- `LEAK_US` - extra microseconds per correct digit on the vulnerable version.
  Bigger = easier to measure (default 1500). On a real board, raise it if the
  attack is unreliable; lower it to make the demo more realistic.
- `RESP_US` - fixed answer time on the hardened version. Keep it larger than the
  slowest possible check.
- `attack.py ... --samples N` - more samples = more reliable, but slower.
