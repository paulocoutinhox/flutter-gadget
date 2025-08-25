// esp32_flutter_keys.ino
// board: ESP32 C6

#include <Arduino.h>

// choose safe GPIOs
constexpr uint8_t BTN_CLEAN   = 20; // "flutter clean"
constexpr uint8_t BTN_GET     = 21; // "flutter pub get"
constexpr uint8_t BTN_UPGRADE = 22; // "flutter upgrade"

struct Btn {
  uint8_t pin;
  bool lastStable;      // debounced level (true = HIGH = released)
  bool lastReading;     // last raw reading
  unsigned long lastTs; // last change timestamp
};

Btn btns[3] = {
  {BTN_CLEAN,   true, true, 0},
  {BTN_GET,     true, true, 0},
  {BTN_UPGRADE, true, true, 0}
};

constexpr unsigned long DEBOUNCE_MS = 25;

static inline void handleButton(uint8_t index, const char* token) {
  bool reading = digitalRead(btns[index].pin); // HIGH (released) with pull-up
  unsigned long now = millis();

  if (reading != btns[index].lastReading) {
    btns[index].lastTs = now;                // start debounce
    btns[index].lastReading = reading;
  }

  if ((now - btns[index].lastTs) > DEBOUNCE_MS) {
    if (reading != btns[index].lastStable) {
      btns[index].lastStable = reading;
      // fire on press only (HIGH -> LOW transition)
      if (reading == LOW) {
        Serial.println(token);               // send short token + newline
      }
    }
  }
}

void setup() {
  // for ESP32-S2/S3 with native USB-CDC, Serial is over USB automatically.
  // for classic ESP32 DevKitC, Serial goes through the USB-UART bridge.
  Serial.begin(115200);
  // small delay to let host open the port
  delay(300);

  pinMode(BTN_CLEAN,   INPUT_PULLUP);
  pinMode(BTN_GET,     INPUT_PULLUP);
  pinMode(BTN_UPGRADE, INPUT_PULLUP);

  Serial.println("ESP32_FLUTTER_KEYS v1");
}

void loop() {
  handleButton(0, "CLEAN");
  handleButton(1, "PUBGET");
  handleButton(2, "UPGRADE");
  // very light loop pacing (optional)
  delay(1);
}
