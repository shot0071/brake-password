# HackLock — Project Scope (Zámer)

## One-sentence scope
HackLock is an educational ESP32 keypad lock that we ship in two firmware versions — a teaching version with a timing side-channel weakness and a hardened constant-time version — together with a desktop emulator and measurement tooling, so that the security concept can be demonstrated, measured, and fixed on real hardware.

## In scope
- **Hardware stand:** ESP32 + 4×4 keypad + servo + LEDs/buzzer in a 3D-printed / laser-cut enclosure.
- **Two firmware builds:** a *learning* build (PIN checked character by character, reacting at the first mismatch) and a *hardened* build (whole-PIN constant-time check).
- **Emulator:** a PC program that reproduces the lock's PIN-check behaviour so the concept and the tooling can be developed before and alongside the hardware.
- **Measurement tooling:** a laptop-side script that records the device's response time over serial and produces plots comparing the two firmware versions.
- **Documentation:** full build instructions, wiring diagram, bill of materials, 7Ds project docs, and a short demo video — everything another team or a teacher needs to rebuild the kit.
- **Optional (stretch / grade A):** a small model that distinguishes normal human PIN entry from automated probing and reacts accordingly.

## Out of scope
- It is **not** a real security product and is not meant to protect anything valuable.
- No attack on any third-party or commercial device — only our own firmware on our own board.
- No complex mechanics (no motorised deadbolt); a single servo opens a lid. This is deliberate: moving mechanics were the main failure point in past course projects.
- No cloud service, mobile app, or networking beyond the local serial link (unless added later as a stretch goal).

## Success criteria
- [ ] On the learning firmware, the response-time difference between a correct and an incorrect leading character is measurable and repeatable.
- [ ] The measurement tool recovers a 4-digit PIN on the learning firmware far faster than brute force.
- [ ] On the hardened firmware, that timing difference is no longer measurable and the same tool fails.
- [ ] A person outside the team can rebuild the kit from the repository alone.

## Deliverables (by January)
- [ ] Working hardware stand
- [ ] Both firmware versions in the repo
- [ ] Emulator + measurement tool with sample data and plots
- [ ] Documentation (README, 7Ds, build guide) and demo video
- [ ] Pitch (5–7 min) and final presentation (10–12 min)

## Main risks
- Component delivery / budget (parts bought at our own expense, ~€15–20).
- Timing noise on the ESP32 making the effect hard to measure — mitigated by averaging many samples and by first proving the method in the emulator.
- Team coordination — mitigated by clear roles (firmware, fabrication, documentation) and weekly commits.
