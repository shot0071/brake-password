# HackLock

An educational keypad lock built on an ESP32, used to teach **side-channel security** in a hands-on way. The firmware ships in two versions — a deliberately weak one and a hardened one — so students can see, measure, and then close a real timing leak on physical hardware.

Course project for **Systémové myslenie v IT a digitálna fabrikácia (STHDF)**, STU FIIT Bratislava, 2026/2027.

---

## What it is

HackLock is a small box with a keypad. You type a PIN; if it is correct, a servo opens the lid and an LED turns green. The interesting part is *how* the firmware checks the PIN:

- The **learning (weak) firmware** compares the entered PIN against the secret one character by character and reacts as soon as the first wrong character appears. This makes the device's response time depend on how many leading characters were correct — a classic **timing side channel**.
- The **hardened firmware** checks the whole PIN in constant time, so the response time no longer leaks information.

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
| **Total** | **~€12–20** |

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

## Team

| Role | Person |
|------|--------|
| Firmware & security | Nazar Bohach (ST-003) — [devNazarBohach](https://github.com/devNazarBohach) |
| Fabrication / enclosure | *(to be filled in)* |
| Documentation & 7Ds | *(to be filled in)* |

---

## Status

Active — course project, autumn semester 2026/2027. See the commit history and `docs/` for weekly progress.

## License

Educational project. Code under MIT, documentation under CC-BY 4.0 (see course template), unless noted otherwise.
