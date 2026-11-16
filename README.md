# HackLock

An educational keypad lock built on an ESP32, used to teach **side-channel security** in a hands-on way. The firmware ships in two versions — a deliberately weak one and a hardened one — so students can see, measure, and then close a real timing leak on physical hardware.

Course project for **Systémové myslenie v IT a digitálna fabrikácia (STHDF)**, STU FIIT Bratislava, 2026/2027.

---

## What it is

HackLock is a small box with a keypad. You type a PIN; if it is correct, a servo opens the lid and an LED turns green. The interesting part is *how* the firmware checks the PIN:

- The **learning (weak) firmware** compares the entered PIN against the secret one character by character and reacts as soon as the first wrong character appears. This makes the device's response time depend on how many leading characters were correct — a classic **timing side channel**.
- The **hardened firmware** checks the whole PIN in constant time, so the response time no longer leaks information.

**Why does a better guess take longer?** The weak check loops over the PIN one digit at a time and, for every digit that *matches*, spends a tiny extra slice of time before moving to the next one; the moment it hits a *wrong* digit it returns immediately. So the more correct leading digits a guess has, the more of those slices it pays, and the **slower** the answer comes back. A completely wrong guess (first digit already wrong) is the **fastest** of all. This is the normal direction of a real early-exit string-comparison leak — slower means "more of your guess was right" — and the attack exploits it directly: for each position it tries all ten digits and keeps the one whose answer is consistently the **slowest** as the correct digit (`recover()` in `tools/attack/attack.py`).

A companion tool on a laptop measures the device's response time over the serial link, so the two firmware versions can be compared on the same hardware. The goal is to make an invisible class of bug (a few microseconds of difference) visible and measurable, and then to show the fix working.

> **Scope note:** HackLock is a teaching aid. It demonstrates a well-known vulnerability class against *our own* device and is meant for classroom and self-study use.

---

## Repository layout

```
.
├── firmware/
│   ├── learning/        # intentionally weak PIN check (teaching version)
│   └── hardened/        # constant-time PIN check (fixed version)
├── tools/
│   └── emulator/        # desktop emulator of the lock (no hardware needed)
├── hardware/            # wiring diagram, bill of materials, enclosure files
├── measurements/        # timing data + plots comparing the two versions
├── docs/                # photos, video links, slides, notes
└── README.md
```

*(Folders are added as each part lands — see the weekly log below.)*

---

## Hardware

| Part | Approx. price |
|------|---------------|
| ESP32 dev board | €5–8 |
| 4×4 membrane keypad | €1–2 |
| SG90 micro servo | €2–3 |
| LEDs, resistors, jumper wires, breadboard | €3–5 |
| Buzzer | ~€1 |
| **Total** | **~€25-30** |

Enclosure is 3D-printed or laser-cut in the faculty FabLab.

---

## Emulator (run it without hardware)

Before the parts arrive, the whole concept can be explored in software. The emulator reproduces the lock's PIN-check behaviour on a PC, so the timing difference can be studied and the measurement/analysis tooling can be developed in parallel with the hardware.

```bash
cd tools/emulator
python emulator.py
```

See `tools/emulator/README.md` for options.

---

## Quick start (for a new teammate)

The first three need no hardware. The last two need the board flashed from
`firmware/hacklock/hacklock.ino` (set `#define VULNERABLE 1` for the attack
demo). Full details are in [`docs/USAGE.md`](docs/USAGE.md).

```bash
cd tools/attack

# 1) Emulator demo: start the leaky lock (one terminal), recover its PIN (another)
python ../emulator/emulator.py --mode vulnerable
python attack.py --target tcp:127.0.0.1:5555 recover --length 4

# 2) Self-test: run the whole experiment on the emulator and check it is "crisp"
python selftest.py

# 3) Live demo by hand: type PINs and watch the response-time bar grow
python live.py --target tcp:127.0.0.1:5555

# 4) Real board (adjust the COM port): watch timing by hand, then recover the PIN
python live.py   --target serial:COM3:115200
python attack.py --target serial:COM3:115200 recover --length 4
```

The emulator and the board speak the same protocol and behave the same way, so
you can learn the whole flow on the emulator before touching hardware.

---

## Team

| Role | Person |
|------|--------|
| Firmware & security | Nazar Bohach (ST-003) — [devNazarBohach](https://github.com/devNazarBohach) |
| Fabrication / enclosure | Mykola Malesh (ST-028) [MykolaMalesh](https://github.com/shot0071) |
| Documentation & 7Ds | *(to be filled in)* |

---

## Status

Active — course project, autumn semester 2026/2027. See the commit history and `docs/` for weekly progress.

## License

Educational project. Code under MIT, documentation under CC-BY 4.0 (see course template), unless noted otherwise.
