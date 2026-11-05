/*
 * daq_node.ino - the Arduino side of the LabVIEW data-acquisition app.
 *
 * Sensors: LM35 temperature on A0, HC-SR04 distance (Trig D9, Echo D10),
 * LDR light sensor on A1 (5V -> LDR -> A1 -> 10 kOhm -> GND).
 * Every period it sends one line at 115200 baud:
 *
 *     <ms>,<temp_c>,<dist_cm>,<light_pct>\n        e.g.  12345,23.4,41.7,63
 *
 * An empty distance means no echo. Commands from LabVIEW, one per line:
 *   P<ms>   set the period (50..5000 ms), e.g. P200
 *   S       stop sending         G   go (start sending again)
 *   ?       print the column names
 * Answers to commands start with '#', so the LabVIEW parser can skip them.
 */
const uint8_t PIN_TEMP = A0, PIN_LIGHT = A1, PIN_TRIG = 9, PIN_ECHO = 10;

uint16_t periodMs = 200;
bool running = true;
unsigned long last = 0;
char cmd[16];
uint8_t cmdLen = 0;

float readTempC() {
  long sum = 0;
  for (uint8_t i = 0; i < 8; i++) sum += analogRead(PIN_TEMP);
  return sum / 8.0 * (5000.0 / 1023.0) / 10.0;        // LM35: 10 mV per degree C
}

float readDistanceCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long echo = pulseIn(PIN_ECHO, HIGH, 25000UL); // about 4 m
  if (echo == 0) return -1;
  return echo * 0.0343 / 2.0;
}

uint8_t readLightPct() { return (uint8_t)(analogRead(PIN_LIGHT) * 100L / 1023); }

void handleCommand() {
  cmd[cmdLen] = '\0';
  if (cmd[0] == 'P') {
    long p = atol(cmd + 1);
    if (p >= 50 && p <= 5000) { periodMs = p; Serial.print(F("# period ")); Serial.println(periodMs); }
    else Serial.println(F("# error: period must be 50..5000 ms"));
  } else if (cmd[0] == 'S') { running = false; Serial.println(F("# stopped")); }
  else if (cmd[0] == 'G') { running = true; Serial.println(F("# running")); }
  else if (cmd[0] == '?') Serial.println(F("# ms,temp_c,dist_cm,light_pct"));
  else Serial.println(F("# error: unknown command"));
  cmdLen = 0;
}

void setup() {
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  Serial.begin(115200);
  Serial.println(F("# daq_node ready: ms,temp_c,dist_cm,light_pct"));
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (cmdLen) handleCommand(); }
    else if (cmdLen < sizeof cmd - 1) cmd[cmdLen++] = c;
  }
  if (running && millis() - last >= periodMs) {
    last += periodMs;
    float d = readDistanceCm();
    Serial.print(millis()); Serial.print(',');
    Serial.print(readTempC(), 1); Serial.print(',');
    if (d >= 0) Serial.print(d, 1);
    Serial.print(',');
    Serial.println(readLightPct());
  }
}
