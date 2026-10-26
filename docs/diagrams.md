# HackLock diagrams

UML views of the HackLock design, derived from the firmware sketch (`tools/emulator`) and the project description. GitHub renders the diagrams below directly from the Mermaid source. They are a working version; a full Enterprise Architect model will replace or extend them.

| # | Diagram |
|---|---------|
| 1 | [Use cases](#use-cases) |
| 2 | [Components](#components) |
| 3 | [Deployment and wiring](#deployment-and-wiring) |
| 4 | [Sequence: timing attack on the learning (vulnerable) firmware](#sequence-timing-attack-on-the-learning-vulnerable-firmware) |
| 5 | [Sequence: the same attack on the hardened firmware](#sequence-the-same-attack-on-the-hardened-firmware) |
| 6 | [State machine of the lock](#state-machine-of-the-lock) |

## Use cases

Who interacts with HackLock and what they can do. `Verify PIN` is shared by the keypad and serial paths; opening the lock and denying access extend it.

```mermaid
flowchart LR
  stu["Student / Learner"]
  ins["Instructor"]
  ana["Analyst (attacks own device)"]
  dev["Team member (builder)"]
  subgraph SYS["System boundary: HackLock"]
    uc1(["UC1 Enter PIN on keypad"])
    uc2(["UC2 Submit PIN over serial (TRY)"])
    uc3(["UC3 Verify PIN"])
    uc4(["UC4 Open lock"])
    uc5(["UC5 Deny access, red LED"])
    uc6(["UC6 Measure response time"])
    uc7(["UC7 Recover PIN by timing attack"])
    uc8(["UC8 Select firmware variant"])
    uc9(["UC9 Compare vulnerable vs hardened"])
    uc10(["UC10 Run in Wokwi emulator"])
  end
  stu --- uc1
  stu --- uc10
  ins --- uc9
  ana --- uc2
  ana --- uc7
  dev --- uc8
  style SYS fill:none,stroke:#4F626D,stroke-dasharray:6 4
  uc1 -.->|"«include»"| uc3
  uc2 -.->|"«include»"| uc3
  uc4 -.->|"«extend» PIN correct"| uc3
  uc5 -.->|"«extend» PIN wrong"| uc3
  uc7 -.->|"«include»"| uc2
  uc7 -.->|"«include»"| uc6
  uc9 -.->|"«include»"| uc7
  uc9 -.->|"«include»"| uc8
  classDef actor fill:#DDF0F4,stroke:#0A7C93,color:#12202A
  class stu,ins,ana,dev actor
```

## Components

Two sides: the laptop with the timing-attack tooling, and the ESP32 firmware. The only external interface between them is the serial line (`TRY <pin>` / `OK` or `NO`). Dashed elements are planned.

```mermaid
flowchart LR
  subgraph LAP["Laptop (Python 3 + pyserial)"]
    AS["AttackScript"]
    TC["TimingCollector (perf_counter)"]
    AN["Analysis and Plots (measurements/)"]
    ML["MlDetector (planned)"]
  end
  subgraph FW["ESP32 firmware (Arduino core)"]
    SP["SerialCommandInput (115200)"]
    KI["KeypadInput (Keypad lib)"]
    AH["AttemptHandler (handleAttempt)"]
    RP["ResponsePadder (RESP_US 8000, hardened only)"]
    PCK["PinChecker (variant by VULNERABLE)"]
    LA["LockActuator (ESP32Servo)"]
    EI["ErrorIndicator (red LED)"]
    CC["CycleCounter (planned)"]
  end
  AS -->|"TRY pin"| SP
  SP -->|"OK / NO"| TC
  AS --> TC
  TC --> AN
  AN -.-> ML
  KI -->|"entry + hash key"| AH
  SP -->|"candidate"| AH
  AH --> PCK
  AH -.->|"hardened only"| RP
  AH -->|"granted"| LA
  AH -->|"denied"| EI
  CC -.->|"cycles"| AH
  classDef plan stroke-dasharray:4 3
  class ML,CC plan
```

## Deployment and wiring

Physical nodes and GPIO pins. Dashed elements are planned (green LED, buzzer).

```mermaid
flowchart LR
  subgraph LAPN["Node: Laptop"]
    PY["Execution env: Python 3 + pyserial"]
    ATK["Artifact: attack script"]
  end
  subgraph ESP["Device: ESP32 DevKit (WROOM, 240 MHz)"]
    ARD["Execution env: Arduino-ESP32 core"]
    SK["Artifact: HackLock sketch (VULNERABLE 1 or 0)"]
  end
  subgraph PER["Peripherals on breadboard"]
    KP["4x4 membrane keypad"]
    SV["SG90 servo, 180 degrees"]
    LDR["Red LED + 220 ohm"]
    LG["Green LED GPIO 19 (planned)"]
    BZ["Passive buzzer GPIO 22 (planned)"]
  end
  ENC["Enclosure (3D print / FabLab)"]
  PY ---|"USB serial, 115200 baud"| ARD
  ESP ---|"rows 13, 14, 27, 26 / cols 25, 33, 32, 23"| KP
  ESP ---|"GPIO 18 signal, 5V VIN power"| SV
  ESP ---|"GPIO 21"| LDR
  ESP -.-|"GPIO 19"| LG
  ESP -.-|"GPIO 22"| BZ
  PER ---|"mounted in"| ENC
  classDef plan stroke-dasharray:4 3
  class LG,BZ plan
```

## Sequence: timing attack on the learning (vulnerable) firmware

Each correct leading digit adds about 1.5 ms to the response, so the digit with the largest time is the correct one.

```mermaid
sequenceDiagram
  actor An as Analyst
  participant SC as AttackScript
  participant FW as Firmware (VULNERABLE 1)
  An->>SC: run attack
  loop position 1 to PIN_LEN
    loop digit 0 to 9
      loop SAMPLES times (30)
        SC->>FW: TRY candidate (t0 starts)
        FW->>FW: compare, early exit on first wrong digit
        Note over FW: +1.5 ms per correct leading digit
        FW-->>SC: OK or NO (t1 stops)
      end
      SC->>SC: trimmed mean of fastest half
    end
    SC->>SC: keep digit with the largest time
  end
  SC-->>An: recovered PIN
```

## Sequence: the same attack on the hardened firmware

Same script and protocol. The constant-time comparison and the fixed 8 ms response remove the signal, so the attack recovers noise.

```mermaid
sequenceDiagram
  actor An as Analyst
  participant SC as AttackScript
  participant FW as Firmware (VULNERABLE 0)
  An->>SC: run the same attack
  loop position 1 to PIN_LEN
    loop digit 0 to 9
      loop SAMPLES times (30)
        SC->>FW: TRY candidate (t0 starts)
        FW->>FW: start = micros()
        FW->>FW: XOR all PIN_LEN characters, no early exit
        FW->>FW: busy-wait until 8000 us have passed
        FW-->>SC: OK or NO (t1 stops)
      end
      SC->>SC: trimmed mean (about 8 ms for every digit)
    end
    SC->>SC: largest time is noise, keeps a wrong digit
  end
  SC-->>An: wrong PIN (attack failed)
```

## State machine of the lock

Current firmware behaviour. `delay()` blocks the main loop in `Granted` and `Denied`.

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Idle : setup()
  Idle --> Collecting : digit key
  Collecting --> Collecting : digit key
  Collecting --> Idle : star key
  Collecting --> Verifying : hash, len ok
  Collecting --> Idle : hash, too short
  Idle --> Verifying : serial TRY
  Verifying --> Granted : checkPin true
  Verifying --> Denied : checkPin false
  Granted --> Idle : after 1500 ms
  Denied --> Idle : after 300 ms
  note right of Granted
    entry: print OK, servo 90
    exit: servo 0
  end note
  note right of Denied
    entry: print NO, red LED on
    exit: red LED off
  end note
```

---

*Planned* parts (green LED, buzzer, cycle-counter mode, ML detector) are drawn dashed because they are not in the code yet.
