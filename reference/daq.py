"""Reference model of the LabVIEW app's processing, one function per subVI.

The LabVIEW VIs are built by hand (labview/BUILD.md). Each subVI has a Python
twin here with the same inputs, outputs and rules; tests/test_daq.py checks the
twins, and test_vectors/ holds their input and expected output so the subVIs can
be checked in LabVIEW with the same numbers (SubVI Tester.vi).
"""
from dataclasses import dataclass, field
from typing import List, Optional

NAN = float("nan")


@dataclass
class Reading:                      # Reading.ctl (type-defined cluster)
    ms: int = 0
    temp_c: float = NAN
    dist_cm: float = NAN            # NaN = no echo
    light_pct: float = NAN
    valid: bool = False


def parse_line(line: str) -> Reading:
    """Parse Line.vi: '12345,23.4,41.7,63' -> Reading. Lines starting with '#'
    (answers to commands), empty lines and malformed lines give valid = False."""
    line = line.strip()
    if not line or line.startswith("#"):
        return Reading()
    parts = line.split(",")
    if len(parts) != 4:
        return Reading()
    try:
        ms = int(parts[0])
        temp = float(parts[1])
        dist = float(parts[2]) if parts[2] != "" else NAN
        light = float(parts[3])
    except ValueError:
        return Reading()
    if not (-40 <= temp <= 150) or not (0 <= light <= 100):
        return Reading()
    return Reading(ms, temp, dist, light, True)


@dataclass
class MovingAverage:                # Moving Average.vi (shift register holds the window)
    n: int = 5
    window: List[float] = field(default_factory=list)

    def step(self, x: float) -> float:
        """NaN inputs (no echo) are skipped: the output repeats the last mean."""
        if x == x:                                  # not NaN
            self.window.append(x)
            if len(self.window) > self.n:
                self.window.pop(0)
        return sum(self.window) / len(self.window) if self.window else NAN


OK, HIGH, LOW = "OK", "HIGH", "LOW"     # Alarm State.ctl (type-defined enum)


@dataclass
class LimitAlarm:                   # Check Limits.vi (feedback node holds the state)
    low: float
    high: float
    hysteresis: float
    state: str = OK

    def step(self, x: float) -> str:
        """Enter HIGH above high, leave it only below high - hysteresis (and the
        mirror for LOW), so a value that hovers at the limit does not flicker."""
        if x != x:
            return self.state
        if self.state == OK:
            if x > self.high:
                self.state = HIGH
            elif x < self.low:
                self.state = LOW
        elif self.state == HIGH and x < self.high - self.hysteresis:
            self.state = LOW if x < self.low else OK
        elif self.state == LOW and x > self.low + self.hysteresis:
            self.state = HIGH if x > self.high else OK
        return self.state


@dataclass
class Stats:                        # Statistics.vi (array functions: max, min, mean)
    values: List[float] = field(default_factory=list)

    def add(self, x: float) -> None:
        if x == x:
            self.values.append(x)

    def summary(self) -> Optional[tuple]:
        if not self.values:
            return None
        return min(self.values), max(self.values), sum(self.values) / len(self.values)


def log_row(r: Reading, temp_avg: float, alarm: str) -> str:
    """Write To Spreadsheet File row: tab-separated, '.' as decimal point."""
    f = lambda v: "" if v != v else f"{v:.2f}"
    return "\t".join([str(r.ms), f(r.temp_c), f(temp_avg), f(r.dist_cm), f(r.light_pct), alarm])
