// ============================================================
//  HackLock - ESP32 keypad lock (teaching firmware)
//
//  One sketch, two behaviours, selected by the VULNERABLE switch:
//    VULNERABLE 1 -> "learning" firmware: the PIN check exits on the
//                    first wrong digit and spends extra time on every
//                    correct one, so the response time leaks how many
//                    leading digits were right (a timing side channel).
//    VULNERABLE 0 -> "hardened" firmware: the PIN is compared in
//                    constant time and every answer takes the same
//                    fixed time, so nothing leaks.
//
//  PIN entry:
//    - from the keypad: 4 digits, then '#' to confirm ('*' clears);
//    - over Serial (used by the attack tool):  TRY 1234
//
//  Answers printed on Serial:  OK  (correct)   /   NO  (wrong)
//
//  Libraries (Arduino Library Manager):  Keypad , ESP32Servo
//  Wokwi project: https://wokwi.com/projects/476424977323738113
// ============================================================

#include <Keypad.h>
#include <ESP32Servo.h>

// ----------------------- CONFIG -----------------------
#define VULNERABLE 1                 // 1 = leaky (learning), 0 = constant-time (hardened)

const char*    SECRET  = "1379";     // test PIN (change freely)
const int      PIN_LEN = 4;          // PIN length
const uint32_t LEAK_US = 1500;       // extra time per correct digit, VULNERABLE only (makes the leak visible)
const uint32_t RESP_US = 8000;       // fixed total answer time, HARDENED only (must be > worst-case check time)

// ----------------------- PINS -------------------------
// Keypad 4x4
const byte ROWS = 4, COLS = 4;
char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[ROWS] = {13, 14, 27, 26};   // keypad rows  R1..R4
byte colPins[COLS] = {25, 33, 32, 23};   // keypad cols  C1..C4
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

const int SERVO_PIN = 18;    // servo signal
const int LED_RED   = 21;    // "denied"  LED
const int LED_GREEN = 19;    // "granted" LED   -- optional, set to -1 to disable
const int BUZZER    = 5;     // active buzzer   -- optional, set to -1 to disable

Servo lockServo;

char entry[16];
int  entryLen = 0;

// ----------------------- PIN CHECK --------------------
bool checkPin(const char* input) {
#if VULNERABLE
  // UNSAFE on purpose: early exit + extra time per correct digit.
  // Response time grows with the number of correct leading digits.
  for (int i = 0; i < PIN_LEN; i++) {
    if (input[i] != SECRET[i]) return false;   // early exit reveals timing
    delayMicroseconds(LEAK_US);                // each correct digit costs +LEAK_US
  }
  return true;
#else
  // SAFE: compare the whole PIN, no early exit, no data-dependent time.
  volatile uint8_t diff = 0;
  for (int i = 0; i < PIN_LEN; i++)
    diff |= (uint8_t)(input[i] ^ SECRET[i]);
  return diff == 0;
#endif
}

// ----------------------- OUTPUTS ----------------------
void beep(int ms) {
  if (BUZZER < 0) return;
  digitalWrite(BUZZER, HIGH);
  delay(ms);
  digitalWrite(BUZZER, LOW);
}

void openLock() {
  Serial.println("OK");                 // print the answer FIRST (so timing is clean)
  if (LED_GREEN >= 0) digitalWrite(LED_GREEN, HIGH);
  beep(80);
  lockServo.write(90);                  // open the lid
  delay(1500);
  lockServo.write(0);                   // close it again
  if (LED_GREEN >= 0) digitalWrite(LED_GREEN, LOW);
}

void denyLock() {
  Serial.println("NO");                 // print the answer FIRST
  digitalWrite(LED_RED, HIGH);
  beep(150);
  delay(200);
  digitalWrite(LED_RED, LOW);
}

// Run one attempt. In HARDENED mode the whole attempt is padded to a
// fixed duration so the answer time carries no information.
void handleAttempt(const char* candidate) {
  // The input must be exactly PIN_LEN long: otherwise "1379" and "137999"
  // would both pass (the check only looks at the first PIN_LEN digits).
  // The length is attacker-chosen, not secret, so this guard leaks nothing.
  bool lenOk = (strlen(candidate) == (size_t)PIN_LEN);
#if VULNERABLE
  bool ok = lenOk && checkPin(candidate);
#else
  uint32_t start = micros();
  bool ok = lenOk && checkPin(candidate);
  while ((uint32_t)(micros() - start) < RESP_US) { /* constant duration */ }
#endif
  if (ok) openLock(); else denyLock();
}

// ----------------------- SETUP / LOOP -----------------
void setup() {
  Serial.begin(115200);
  pinMode(LED_RED, OUTPUT);
  digitalWrite(LED_RED, LOW);
  if (LED_GREEN >= 0) { pinMode(LED_GREEN, OUTPUT); digitalWrite(LED_GREEN, LOW); }
  if (BUZZER    >= 0) { pinMode(BUZZER,    OUTPUT); digitalWrite(BUZZER,    LOW); }

  lockServo.attach(SERVO_PIN);
  lockServo.write(0);

  Serial.println("HackLock ready.");
#if VULNERABLE
  Serial.println("Mode: VULNERABLE (timing leak enabled)");
#else
  Serial.println("Mode: HARDENED (constant-time)");
#endif
  Serial.println("Keypad: 4 digits then '#'  (* = clear)");
  Serial.println("Serial: TRY 1234");
}

void loop() {
  // 1) Keypad (a human typing)
  char k = keypad.getKey();
  if (k) {
    if (k == '#') {                      // confirm
      entry[entryLen] = '\0';
      if (entryLen >= PIN_LEN) handleAttempt(entry);
      entryLen = 0;
    } else if (k == '*') {               // clear
      entryLen = 0;
      Serial.println("cleared");
    } else if (entryLen < 15) {
      entry[entryLen++] = k;
      Serial.print("*");                 // mask the typed digit
    }
  }

  // 2) Serial (the attack tool): line "TRY 1234"
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.startsWith("TRY ")) {
      String pin = line.substring(4);
      pin.trim();
      handleAttempt(pin.c_str());
    }
  }
}
