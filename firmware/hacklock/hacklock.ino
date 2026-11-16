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
// NOTE: this keymap is adapted to our physical keypad, whose rows and
// columns are swapped and reversed versus the usual pinout. We mapped every
// key (press -> printed char) and rewrote the array so the labels match.
// For a standard keypad use the plain layout: row0 {'1','2','3','A'}, etc.
char keys[ROWS][COLS] = {
  {'D','C','B','A'},
  {'#','9','6','3'},
  {'0','8','5','2'},
  {'*','7','4','1'}
};
byte rowPins[ROWS] = {13, 14, 27, 26};   // keypad rows
byte colPins[COLS] = {25, 33, 32, 23};   // keypad cols
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
// Feedback (LEDs, buzzer, servo) is NON-BLOCKING: each output is switched on
// here and switched off later in loop() by serviceOutputs(). This keeps the
// device reading the next command immediately, so the attack tool measures
// the PIN-check time cleanly, without the 350ms/1.5s delays leaking in.
uint32_t redOffAt = 0, greenOffAt = 0, buzzOffAt = 0, servoCloseAt = 0;

void beepStart(int ms) {
  if (BUZZER < 0) return;
  digitalWrite(BUZZER, HIGH);
  buzzOffAt = millis() + ms;
}

void serviceOutputs() {
  uint32_t now = millis();
  if (redOffAt   && now >= redOffAt)   { digitalWrite(LED_RED, LOW);   redOffAt   = 0; }
  if (greenOffAt && now >= greenOffAt) { digitalWrite(LED_GREEN, LOW); greenOffAt = 0; }
  if (buzzOffAt  && now >= buzzOffAt)  { digitalWrite(BUZZER, LOW);    buzzOffAt  = 0; }
  if (servoCloseAt && now >= servoCloseAt) { lockServo.write(0);       servoCloseAt = 0; }
}

void openLock() {
  Serial.println("OK");                 // print the answer FIRST (so timing is clean)
  if (LED_GREEN >= 0) { digitalWrite(LED_GREEN, HIGH); greenOffAt = millis() + 1500; }
  beepStart(80);
  lockServo.write(90);                  // open the lid
  servoCloseAt = millis() + 1500;       // close it again later (non-blocking)
}

void denyLock() {
  Serial.println("NO");                 // print the answer FIRST
  digitalWrite(LED_RED, HIGH);
  beepStart(150);
  redOffAt = millis() + 200;            // turn the LED off later (non-blocking)
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
  serviceOutputs();   // turn off LEDs / buzzer / servo when their time is up

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
