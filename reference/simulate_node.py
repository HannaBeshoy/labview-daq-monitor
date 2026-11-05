"""Simulated Arduino: writes the lines daq_node.ino would send (the LabVIEW app's
Simulated Source.vi produces the same shape). Also writes the test vectors.

    python3 reference/simulate_node.py           -> test_vectors/*.csv
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daq import LimitAlarm, MovingAverage, Stats, log_row, parse_line  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def node_lines(n=300, period_ms=200, seed=1):
    """Room at 23 C warming to 31 C (a heater switched on at 20 s), an object
    moving to and fro at 30-80 cm, light falling at dusk; 3 % no-echo readings,
    a few command answers and one corrupted line, like a real serial stream."""
    rng = random.Random(seed)
    out = ["# daq_node ready: ms,temp_c,dist_cm,light_pct"]
    for i in range(n):
        t = i * period_ms / 1000
        temp = 23 + (8 * (1 - math.exp(-(t - 20) / 15)) if t > 20 else 0) + rng.gauss(0, 0.25)
        dist = 55 + 25 * math.sin(2 * math.pi * t / 12) + rng.gauss(0, 0.6)
        light = max(0, min(100, 70 - 1.0 * t + rng.gauss(0, 1.5)))
        d = "" if rng.random() < 0.03 else f"{dist:.1f}"
        out.append(f"{i * period_ms},{temp:.1f},{d},{light:.0f}")
        if i == 100:
            out.append("# period 200")
        if i == 150:
            out.append("15000,2")                   # a line cut short by a reset
    return out


def main():
    os.makedirs(os.path.join(ROOT, "test_vectors"), exist_ok=True)
    lines = node_lines()
    with open(os.path.join(ROOT, "test_vectors", "node_stream.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    avg, alarm, stats = MovingAverage(5), LimitAlarm(18.0, 28.0, 0.5), Stats()
    with open(os.path.join(ROOT, "test_vectors", "expected_log.tsv"), "w") as f:
        f.write("ms\ttemp_c\ttemp_avg5\tdist_cm\tlight_pct\talarm\n")
        for line in lines:
            r = parse_line(line)
            if not r.valid:
                continue
            a = avg.step(r.temp_c)
            s = alarm.step(a)
            stats.add(r.temp_c)
            f.write(log_row(r, a, s) + "\n")
    lo, hi, mean = stats.summary()
    with open(os.path.join(ROOT, "test_vectors", "expected_stats.txt"), "w") as f:
        f.write(f"valid_lines\t{len(stats.values)}\nmin\t{lo:.2f}\nmax\t{hi:.2f}\nmean\t{mean:.3f}\n")
    # small hand-checkable vectors for each subVI
    with open(os.path.join(ROOT, "test_vectors", "parse_line.csv"), "w") as f:
        f.write("line;valid;ms;temp_c;dist_cm;light_pct\n")
        for s in ["12345,23.4,41.7,63", "200,22.9,,70", "# period 200", "", "15000,2",
                  "abc,1,2,3", "100,180.0,20,50", "100,20.0,20,101", "0,-5.5,399.9,0"]:
            r = parse_line(s)
            f.write(f"{s};{int(r.valid)};{r.ms};{r.temp_c};{r.dist_cm};{r.light_pct}\n")
    with open(os.path.join(ROOT, "test_vectors", "moving_average.csv"), "w") as f:
        f.write("x;mean5\n")
        m = MovingAverage(5)
        for x in [10, 20, 30, float("nan"), 40, 50, 60, 70]:
            f.write(f"{x};{m.step(x):.4f}\n")
    with open(os.path.join(ROOT, "test_vectors", "check_limits.csv"), "w") as f:
        f.write("x;state   (low 18, high 28, hysteresis 0.5)\n")
        c = LimitAlarm(18, 28, 0.5)
        for x in [25, 28.1, 27.8, 27.6, 27.4, 17.9, 18.2, 18.6, 29, 27.0]:
            f.write(f"{x};{c.step(x)}\n")
    print("wrote test_vectors/: node_stream.txt, expected_log.tsv, expected_stats.txt and three subVI tables")


if __name__ == "__main__":
    main()
