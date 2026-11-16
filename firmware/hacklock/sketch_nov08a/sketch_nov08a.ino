#include <Keypad.h>
const byte ROWS = 4, COLS = 4;
char keys[ROWS][COLS] = {
  {'D','C','B','A'},
  {'#','9','6','3'},
  {'0','8','5','2'},
  {'*','7','4','1'}
};
byte rowPins[ROWS] = {13, 14, 27, 26};
byte colPins[COLS] = {25, 33, 32, 23};
Keypad kp = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);
int n = 1;
void setup(){ Serial.begin(115200); Serial.println("map test"); }
void loop(){
  char k = kp.getKey();
  if (k){ Serial.print(n++); Serial.print(" -> "); Serial.println(k); }
}
