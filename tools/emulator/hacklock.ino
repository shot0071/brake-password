// ============================================================
//  HackLock — Wokwi simulation sketch (ESP32)
//  4x4 keypad + servo + red LED.
//  PIN entry: from the keypad (4 digits, then '#') or
//  over Serial with the command:  TRY 1234
//
//  Wokwi project: https://wokwi.com/projects/476424977323738113
// ============================================================

#include <Keypad.h>
#include <ESP32Servo.h>

// ---------------- CONFIG ----------------
#define VULNERABLE 1              // 1 = vulnerable (leaky), 0 = safe (constant-time)
const char* SECRET   = "1379";   // test PIN
const int   PIN_LEN  = 4;
const uint32_t LEAK_US = 1500;   // amplified leak per correct digit (VULNERABLE only)
const uint32_t RESP_US = 8000;   // fixed response duration (SECURE only)

// ---------------- PINS ------------------
const byte ROWS = 4, COLS = 4;
char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[ROWS] = {13, 14, 27, 26};   // keypad rows
byte colPins[COLS] = {25, 33, 32, 23};   // keypad columns
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

const int SERVO_PIN = 18;   // servo signal
const int LED_RED   = 21;   // "error" signal
Servo lockServo;

char entry[16];
int  entryLen = 0;

// ---------------- PIN CHECK ----------------
bool checkPin(const char* input) {
#if VULNERABLE
  // UNSAFE: early exit + amplified leak.
  for (int i = 0; i < PIN_LEN; i++) {
    if (input[i] != SECRET[i]) return false;   // early exit reveals timing
    delayMicroseconds(LEAK_US);                // each correct digit = +1.5 ms
  }
  return true;
#else
  // SAFE: constant-time comparison, no early exit.
  volatile uint8_t diff = 0;
  for (int i = 0; i < PIN_LEN; i++)
    diff |= (uint8_t)(input[i] ^ SECRET[i]);
  return diff == 0;
#endif
}

void openLock() {
  Serial.println("OK");
  lockServo.write(90);     // open the lid
  delay(1500);
  lockServo.write(0);      // close it again
}

void denyLock() {
  Serial.println("NO");
  digitalWrite(LED_RED, HIGH);
  delay(300);
  digitalWrite(LED_RED, LOW);
}

void handleAttempt(const char* candidate) {
#if VULNERABLE
  bool ok = checkPin(candidate);
#else
  uint32_t start = micros();
  bool ok = checkPin(candidate);
  while ((uint32_t)(micros() - start) < RESP_US) { /* constant duration */ }
#endif
  if (ok) openLock(); else denyLock();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_RED, OUTPUT);
  digitalWrite(LED_RED, LOW);
  lockServo.attach(SERVO_PIN);
  lockServo.write(0);
  Serial.println("HackLock ready.");
  Serial.println("Keypad: 4 digits then '#'  (* = clear)");
  Serial.println("Serial: TRY 1234");
}

void loop() {
  // 1) Keypad (human)
  char k = keypad.getKey();
  if (k) {
    if (k == '#') {                       // confirm
      entry[entryLen] = '\0';
      if (entryLen >= PIN_LEN) handleAttempt(entry);
      entryLen = 0;
    } else if (k == '*') {                // clear
      entryLen = 0;
      Serial.println("cleared");
    } else if (entryLen < 15) {
      entry[entryLen++] = k;
      Serial.print("*");                  // mask the input
    }
  }

  // 2) Serial (attack): "TRY 1234"
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
