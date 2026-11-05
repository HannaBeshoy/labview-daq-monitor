# Project guide

How the application uses each topic of the Introduction to Graphical Programming course (Tóth Ádám's classes 1–7 and their example VIs).

| Class | Course example | Used here |
| --- | --- | --- |
| 1–2 | Thermometer, Convert C to F, Read Voltage; dataflow, data types, debugging, error clusters | the temperature conversion on the Arduino; error clusters wired through every VI; Simple Error Handler at the end |
| 3 | Array Functions, Array Max and Min, Initialize Array; custom controls and type definitions | Moving Average's window array, Statistics.vi; Reading.ctl and Alarm State.ctl as type definitions |
| 4 | Case Structures, Temperature Warnings, Event-Driven Scenario (polling vs event method) | Check Limits.vi's state cases; the UI loop's Event Structure instead of polling |
| 5 | SubVI Tester, Weather Data.ctl (a cluster type) | every processing step is a subVI with a connector pane and an icon; SubVI Tester.vi checks them against test vectors |
| 6 | Spreadsheet Example | the tab-separated log file |
| 7 | Temperature Monitor (while loop with a chart) | the three waveform charts in the consumer loop |

## 1. Dataflow and why three loops

A LabVIEW node runs when all its inputs have arrived, and a loop iteration ends when everything inside it has run. If one loop read the port, parsed, drew three charts and wrote a file, a slow step would delay the next VISA Read, and lines would pile up in the operating system's buffer or be lost. Separating the producer (only reads) from the consumer (everything else) with a queue lets each run at its own pace; the queue absorbs short bursts, the same job the ring buffer does in the Data Structures project.

## 2. Events instead of polling

Polling reads every button in every iteration and wastes CPU when nothing happens; an Event Structure sleeps until a value changes and then runs exactly the case for that control. The course shows both versions of the same scenario; the UI loop here is the event version.

## 3. Functional globals: state inside a subVI

Moving Average needs the last N values and Check Limits needs the previous state. An uninitialised shift register (or a feedback node) keeps its value from one call of the subVI to the next, so the caller only passes the new value. A `reset` input clears it when a new run starts.

## 4. Hysteresis

With one threshold, a temperature that hovers at 28 °C (28.2, 27.8, 28.2, …) would switch the alarm on and off at every reading. With two thresholds (on above 28, off below 27.5), the same input gives one change. The unit test `test_no_flicker_at_the_limit` feeds exactly that zig-zag and expects no flicker.

## 5. Bad data is counted, not passed on

The serial stream contains more than data lines: command answers, a line cut short when the Arduino resets, a missing echo. Parse Line marks anything that is not a complete, in-range reading as invalid; the consumer counts it and skips it. A missing echo is a valid reading with NaN distance, so the chart shows a gap instead of a false 0 cm.

## Notes for the three tracks

- **Embedded systems and edge AI.** The node and the PC agree on a small text protocol with commands; the same producer–consumer split is how a microcontroller firmware separates its interrupt from its main loop.
- **FPGA to semiconductors.** LabVIEW's dataflow is the same model as hardware: a node "fires" when its inputs are ready, like a pipeline stage; LabVIEW FPGA compiles block diagrams to FPGA logic.
- **Product security.** The parser treats every incoming line as untrusted: length, format and range are checked before a value is used, and a malformed line can never crash the program or be logged as a real measurement.
