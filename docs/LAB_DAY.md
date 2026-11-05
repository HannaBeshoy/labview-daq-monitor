# Lab-day test sheet (15 minutes)

**Need:** the laptop with LabVIEW and the built VIs, Arduino Uno or Nano with USB cable, LM35, HC-SR04, LDR with a 10 kΩ resistor, breadboard, jumper wires (the same wiring as the Java serial monitor project).

1. Wire: LM35 → A0; HC-SR04 Trig → D9, Echo → D10; 5V → LDR → A1 → 10 kΩ → GND. Upload `arduino/daq_node/daq_node.ino`.
2. Serial Monitor at 115200: lines like `12345,23.4,41.7,63`. Close the Serial Monitor (only one program can own the port).
3. Open `DAQ Monitor.vi`, choose the Arduino's COM port and source "Arduino", press Start.
4. Expect: three charts moving; `bad lines` stays at 0 or 1 (the start-up `#` line is counted as skipped).
5. Move a hand in front of the ultrasonic sensor → the distance chart follows. Cover the LDR → light drops.
6. Set `high` to 1 °C above the room temperature, warm the LM35 between two fingers → alarm turns HIGH; release → it returns to OK only after the average falls 0.5 °C below the limit.
7. Change `period ms` to 500 → the Arduino answers `# period 500` and the charts slow down.
8. Stop, Quit. Open `data.txt` in Excel: one row per reading with the six columns.

**Record:** a screenshot of the front panel during the alarm, `data.txt`, and a photo of the setup.
