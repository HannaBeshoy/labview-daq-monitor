# Building the VIs

LabVIEW files (.vi, .ctl) are binary and can only be made in LabVIEW, so this page is the build plan: every control, every node and every wire, in the order to build them. Each subVI is checked against the tables in `test_vectors/` before it is used, so a mistake shows up in the small VI where it was made.

**Needs:** LabVIEW Community Edition (free for non-commercial use) with NI-VISA, which comes with the LabVIEW installer as a driver option. About 3 hours.

Save everything in this `labview/` folder, and the project file as `labview/DAQ Monitor.lvproj` (File » Create Project » Blank Project). Make every file below from the project window (right-click My Computer » New) so they stay together.

| File | Course topic | What it does |
| --- | --- | --- |
| `Reading.ctl` | custom controls, type definitions (class 3, `TypeDef Demo.vi`) | one reading: ms, temperature, distance, light, valid |
| `Alarm State.ctl` | type-defined enum | OK, HIGH, LOW |
| `Parse Line.vi` | strings, error clusters (class 2) | one serial line → Reading |
| `Moving Average.vi` | arrays and shift registers (class 3, `Array Functions.vi`) | mean of the last N values |
| `Check Limits.vi` | case structures (class 4, `Temperature Warnings.vi`) | alarm state with hysteresis |
| `Statistics.vi` | array max and min (class 3, `Array Max and Min.vi`) | min, max, mean of the run |
| `Simulated Source.vi` | subVIs (class 5) | produces lines like the Arduino, for testing without hardware |
| `SubVI Tester.vi` | subVI testing (class 5, `SubVI Tester.vi`) | runs the test vectors through the subVIs |
| `DAQ Monitor.vi` | events, producer–consumer, file I/O (classes 4, 6, 7) | the application |

## 1. Type definitions

**Reading.ctl**: New » Custom Control. Place a Cluster and put in, in this order: `ms` (numeric, right-click » Representation » U32), `temp_c` (DBL), `dist_cm` (DBL), `light_pct` (DBL), `valid` (Boolean). Control type (the drop-down in the toolbar): **Type Def.** Save.

**Alarm State.ctl**: a Custom Control with an Enum; Edit Items: `OK` (0), `HIGH` (1), `LOW` (2). Type Def. Save.

From now on, place them from the project window (drag the .ctl onto a front panel), so every copy updates when the type definition changes.

## 2. Parse Line.vi

Front panel: input `line` (String control), `error in` (cluster); outputs `reading` (Reading.ctl indicator), `error out`.

Block diagram:

1. **Trim Whitespace** on `line` (removes the `\r` that Windows line endings leave).
2. **Case structure** on two conditions OR-ed together: `Empty String/Path?` and `Match Pattern` with regular expression `^#` (offset past match ≥ 0 means it matched). TRUE case: wire a Reading constant with `valid` = FALSE to the output (this is a comment line, not an error).
3. FALSE case: **Spreadsheet String To Array** with format `%s` and delimiter `,` → a 1D string array. **Array Size** = 4? If not, output `valid` = FALSE.
4. If 4: **Index Array** gives the four strings.
   - `ms`: **Decimal String To Number** (U32).
   - `temp_c` and `light_pct`: **Fract/Exp String To Number**. Use its **offset past number** output: if it is 0, the string was not a number → `valid` = FALSE.
   - `dist_cm`: if the string is empty, use the constant **NaN** (Numeric palette » Math Constants), else Fract/Exp String To Number.
5. Range check with **In Range and Coerce**: temperature −40…150, light 0…100. Both must be in range.
6. **Bundle By Name** into Reading (start from a Reading constant): all four values and `valid` = AND of all the checks.
7. Pass `error in` to `error out` unchanged: a bad line is data, not an error.

Connector pane: `line` and `error in` on the left, `reading` and `error out` on the right. Icon: "PARSE".

**Check it** with `test_vectors/parse_line.csv` (9 lines, including a comment, an empty line, a cut line, text, and two out-of-range values): run the VI with each `line` and compare the indicator with the table. `nan` shows as NaN in LabVIEW.

## 3. Moving Average.vi

Inputs `x` (DBL), `N` (I32, default 5), `reset` (Boolean, default FALSE). Output `mean` (DBL).

A While Loop that runs once (wire TRUE to the stop terminal) with an **uninitialised shift register** holding a DBL array: an uninitialised shift register keeps its value between calls of the subVI. This is the "functional global" pattern.

1. If `reset`: replace the array with an empty array.
2. If `x` is not NaN (**Not A Number/Path/Refnum?** is FALSE): **Build Array** to append `x`; if **Array Size** > N, **Delete From Array** index 0 (or **Array Subset** from index size − N).
3. `mean` = **Mean** (Mathematics » Probability & Statistics) of the array; if the array is empty, NaN.
4. Write the new array to the shift register.

Make it **reentrant** (File » VI Properties » Execution » Preallocated clone reentrant execution) if you later use it for more than one channel, otherwise the channels would share one window.

**Check it** with `test_vectors/moving_average.csv`: 10, 20, 30, NaN, 40, 50, 60, 70 must give 10, 15, 20, 20, 25, 30, 40, 50.

## 4. Check Limits.vi

Inputs `x` (DBL), `low`, `high`, `hysteresis` (DBL; defaults 18, 28, 0.5), `reset`. Output `state` (Alarm State.ctl).

Same single-run loop, with a **Feedback Node** (or uninitialised shift register) holding the state, initialised to OK. A **Case structure** on the previous state:

| Previous state | Condition | New state |
| --- | --- | --- |
| OK | x > high | HIGH |
| OK | x < low | LOW |
| HIGH | x < high − hysteresis | LOW if x < low, else OK |
| LOW | x > low + hysteresis | HIGH if x > high, else OK |
| any | x is NaN | unchanged |

Otherwise the state stays. The hysteresis band is what stops the alarm from flickering when the temperature hovers at the limit.

**Check it** with `test_vectors/check_limits.csv`: 25, 28.1, 27.8, 27.6, 27.4, 17.9, 18.2, 18.6, 29, 27.0 → OK, HIGH, HIGH, HIGH, OK, LOW, LOW, OK, HIGH, OK.

## 5. Statistics.vi

Input: DBL array. Outputs `min`, `max`, `mean`, `count`. **Array Max & Min** for min and max (skip NaN first: a For Loop with a conditional tunnel that keeps only the non-NaN values), **Mean**, **Array Size**.

## 6. Simulated Source.vi

So the app runs without an Arduino. Input `i` (iteration, I32), `period ms` (default 200). Output `line` (String). It computes the same signals as `reference/simulate_node.py` (without the random noise, or with **Random Number (0-1)** noise if you like):

- temperature = 23 °C, and after 20 s: 23 + 8·(1 − e^(−(t − 20)/15))
- distance = 55 + 25·sin(2πt/12) cm
- light = 70 − t %, not below 0

and builds the line with **Format Into String**, format `%d,%.1f,%.1f,%.0f` (ms, temperature, distance, light). Every 33rd line, leave the distance empty (`%d,%.1f,,%.0f`) to imitate a missing echo.

## 7. SubVI Tester.vi

The course's `SubVI Tester.vi` idea, applied to the three subVIs. Read each table with **Read Delimited Spreadsheet** (delimiter `;`, as string, skip the header row), run the subVI on every row in a For Loop, compare with the expected column (**Equal?**, with a tolerance of 0.001 for numbers via **Absolute Value** of the difference), and light a green LED per subVI if all rows pass. Also show the failing row number.

Then the end-to-end check: feed every line of `test_vectors/node_stream.txt` through Parse Line → Moving Average (N = 5) → Check Limits (18, 28, 0.5), and compare with `test_vectors/expected_log.tsv` (columns `temp_avg5` and `alarm`). Expect 300 valid lines, 180 OK and 120 HIGH, and the first HIGH at 36.0 s.

## 8. DAQ Monitor.vi: the application

### Front panel

- **Settings**: `VISA resource` (VISA resource name control), `source` (enum: Arduino, Simulated), `period ms` (default 200), `low` / `high` limits (18, 28 °C), `log file` (path control, default `data.txt`).
- **Buttons**: `Start`, `Stop`, `Quit` (Boolean, mechanical action **Latch When Released**).
- **Charts**: three Waveform Charts (temperature with two plots, raw and average; distance; light), chart history length 1024.
- **Indicators**: `alarm` (Alarm State.ctl, with a coloured LED next to it: red for HIGH, blue for LOW), `last line` (string), `lines`, `bad lines`, `min`, `max`, `mean`.

### Block diagram: three loops (producer–consumer with an event loop)

```text
 Obtain Queue (string)                         queue of lines
        │
 ┌──────▼─────── UI loop ──────────────┐   Event Structure: Start, Stop, Quit, period ms, limits
 │  Event Structure                     │   Start: VISA Configure Serial Port (115200, 8N1,
 │  (Value Change events)               │          termination char \n enabled), VISA Write "G\n"
 └──────────────────────────────────────┘   Stop: VISA Write "S\n";  period: VISA Write "P<ms>\n"
                                            Quit: release everything, stop all loops
 ┌──────────── producer loop ───────────┐
 │  Arduino: VISA Read (100 bytes,       │   reads one line (the termination char ends the read);
 │           timeout 1000 ms)            │   a timeout is not an error here: clear error -1073807339
 │  Simulated: Simulated Source.vi +     │
 │           Wait (period ms)            │
 │  → Enqueue Element                    │
 └──────────────────────────────────────┘
 ┌──────────── consumer loop ───────────┐
 │  Dequeue Element (timeout 100 ms)     │
 │  → Parse Line.vi → valid?             │   invalid: bad lines + 1, skip
 │  → Moving Average.vi (temperature)    │
 │  → Check Limits.vi                    │
 │  → charts, alarm LED, last line       │
 │  → Format Into String (tab-separated) │
 │  → Write to Text File (append)        │   the same columns as test_vectors/expected_log.tsv
 │  → Statistics.vi every 10 readings    │
 └──────────────────────────────────────┘
 Release Queue → VISA Close → Merge Errors → Simple Error Handler
```

Why three loops: the serial port must be read on time whatever the display is doing, so reading (producer) and processing (consumer) are separate loops joined by a queue, which buffers lines when the consumer is briefly slower, just like the UART ring buffer of the Data Structures project. The event loop sleeps until a button is pressed instead of polling the buttons (the course compares both in `Event-Driven Scenario (Polling Method).vi` and `(Event Method).vi`).

Stopping cleanly: Quit sets a local variable (or a notifier) read by the producer loop; the producer stops, the consumer stops when **Dequeue Element** returns an error after **Release Queue** (the standard way to end a consumer loop), then the VISA session is closed. Wire the error clusters through every VI and finish with **Merge Errors** and **Simple Error Handler** (class 2).

### Log file

Open the file once before the loops (**Open/Create/Replace File**, create or replace), write the header line `ms\ttemp_c\ttemp_avg5\tdist_cm\tlight_pct\talarm`, write one line per reading in the consumer, close it after the loops. Each row matches `reference/daq.py`'s `log_row`. Run the app on the simulated source and compare `data.txt` with `test_vectors/expected_log.tsv`: the simulated source has no noise, so the numbers differ, but the columns and format must match exactly.

## 9. Screenshots for the README

Save into `docs/img/`: `front_panel.png` (the app running on the simulated source, alarm HIGH), `block_diagram.png` (the three loops), `subvi_tester.png` (all LEDs green). Then the README's "VIs built" box can be ticked.
