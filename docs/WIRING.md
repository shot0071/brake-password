# HackLock - hardware wiring guide

Everything plugs into a breadboard with jumper (Dupont) wires. No soldering is
needed if your ESP32 comes with its pin headers already attached and your
keypad has the usual 8-pin connector.

## Parts

| Part | Notes | Approx. price |
|---|---|---|
| ESP32 dev board (DevKit, 30/38-pin) | the brain | EUR 5-8 |
| 4x4 membrane keypad | PIN entry | EUR 1-2 |
| SG90 micro servo | opens the lid | EUR 2-3 |
| Red LED | "denied" | ~ EUR 0.1 |
| Green LED *(optional)* | "granted" | ~ EUR 0.1 |
| 2x 220 ohm resistor | one per LED | ~ EUR 0.1 |
| Active buzzer *(optional)* | beeps | ~ EUR 1 |
| Breadboard + jumper wires | — | EUR 3-5 |

## Pinout (this is the single source of truth - code and wiring match it)

### Keypad 4x4 -> ESP32
The keypad has 8 pins in a row. Looking at the connector, pins 1-4 are the
**rows**, pins 5-8 are the **columns** (left to right on most modules).

| Keypad pin | Function | ESP32 GPIO |
|---|---|---|
| 1 | Row 1 (R1) | GPIO 13 |
| 2 | Row 2 (R2) | GPIO 14 |
| 3 | Row 3 (R3) | GPIO 27 |
| 4 | Row 4 (R4) | GPIO 26 |
| 5 | Col 1 (C1) | GPIO 25 |
| 6 | Col 2 (C2) | GPIO 33 |
| 7 | Col 3 (C3) | GPIO 32 |
| 8 | Col 4 (C4) | GPIO 23 |

No resistors and no power needed for the keypad - the ESP32 uses its internal
pull-ups. If your keys land in the wrong place, your module's row/column order
is reversed: swap the two groups of four wires, or edit `rowPins`/`colPins` in
the sketch.

### Servo SG90 -> ESP32
The servo has three wires.

| Servo wire | Connect to |
|---|---|
| Orange (signal) | GPIO 18 |
| Red (V+) | 5V / VIN |
| Brown (GND) | GND |

Power it from **5V (VIN)**, not 3V3 - the servo is weak on 3.3 V. For the demo,
USB power is fine. If the board browns out or resets when the servo moves, give
the servo its own 5 V supply and join the grounds (GND of ESP32 and of the
supply must be connected together).

### Red LED "denied" -> ESP32
LED has a long leg (anode, +) and a short leg (cathode, -).

```
GPIO 21  ->  220 ohm resistor  ->  LED long leg (anode)
LED short leg (cathode)  ->  GND
```

### Green LED "granted" (optional) -> ESP32
```
GPIO 19  ->  220 ohm resistor  ->  LED long leg (anode)
LED short leg (cathode)  ->  GND
```

### Buzzer (optional) -> ESP32
Active buzzer, so no resistor needed.
```
Buzzer +  ->  GPIO 5
Buzzer -  ->  GND
```

## Turning the optional parts off
If you do not wire the green LED or the buzzer, open
`firmware/hacklock/hacklock.ino` and set the pin to `-1`:

```cpp
const int LED_GREEN = -1;   // green LED not connected
const int BUZZER    = -1;   // buzzer not connected
```

The red LED and the servo are required; the rest are optional.

## Quick wiring map

```
                     ESP32 DevKit
  keypad R1..R4 ---> 13 14 27 26
  keypad C1..C4 ---> 25 33 32 23
  servo signal  ---> 18         servo V+ -> 5V,  servo GND -> GND
  red LED       ---> 21 -[220]-|>|- GND
  green LED     ---> 19 -[220]-|>|- GND   (optional)
  buzzer        ---> 5  --------[#]- GND  (optional)
```

## Safety / scope
HackLock attacks only **our own** firmware on **our own** board. It is a
teaching aid, not a real lock.
