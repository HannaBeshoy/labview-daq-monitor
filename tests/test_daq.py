"""Tests for the reference model (python3 -m unittest discover tests)."""
import math
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "reference"))
from daq import HIGH, LOW, OK, LimitAlarm, MovingAverage, Stats, log_row, parse_line  # noqa: E402
from simulate_node import node_lines  # noqa: E402


class ParseLine(unittest.TestCase):
    def test_good_line(self):
        r = parse_line("12345,23.4,41.7,63\n")
        self.assertTrue(r.valid)
        self.assertEqual((r.ms, r.temp_c, r.dist_cm, r.light_pct), (12345, 23.4, 41.7, 63))

    def test_no_echo_is_nan_but_valid(self):
        r = parse_line("200,22.9,,70")
        self.assertTrue(r.valid)
        self.assertTrue(math.isnan(r.dist_cm))

    def test_rejects_comments_short_garbage_and_out_of_range(self):
        for s in ["# period 200", "", "   ", "15000,2", "abc,1,2,3", "1,2,3,4,5", "100,180.0,20,50", "100,20,20,101"]:
            self.assertFalse(parse_line(s).valid, s)

    def test_windows_line_ending(self):
        self.assertTrue(parse_line("1,20.0,30.0,40\r\n").valid)


class MovingAverageTest(unittest.TestCase):
    def test_fills_then_slides(self):
        m = MovingAverage(5)
        outs = [m.step(x) for x in [10, 20, 30, 40, 50, 60]]
        self.assertEqual(outs, [10, 15, 20, 25, 30, 40])

    def test_nan_is_skipped(self):
        m = MovingAverage(3)
        m.step(1); m.step(2)
        self.assertEqual(m.step(float("nan")), 1.5)
        self.assertEqual(m.step(3), 2)

    def test_empty_is_nan(self):
        self.assertTrue(math.isnan(MovingAverage(3).step(float("nan"))))


class LimitAlarmTest(unittest.TestCase):
    def test_hysteresis_high(self):
        a = LimitAlarm(18, 28, 0.5)
        self.assertEqual([a.step(x) for x in [25, 28.1, 27.8, 27.6, 27.4]], [OK, HIGH, HIGH, HIGH, OK])

    def test_hysteresis_low_and_jump(self):
        a = LimitAlarm(18, 28, 0.5)
        self.assertEqual([a.step(x) for x in [17.9, 18.2, 18.6, 29, 17]], [LOW, LOW, OK, HIGH, LOW])

    def test_no_flicker_at_the_limit(self):
        a = LimitAlarm(18, 28, 0.5)
        states = [a.step(28 + 0.2 * (-1) ** i) for i in range(50)]      # 28.2, 27.8, 28.2, ...
        changes = sum(1 for p, q in zip(states, states[1:]) if p != q)
        self.assertEqual(changes, 0)
        self.assertEqual(states[0], HIGH)


class StreamTest(unittest.TestCase):
    def test_simulated_stream(self):
        lines = node_lines()
        valid = [parse_line(s) for s in lines if parse_line(s).valid]
        self.assertEqual(len(valid), 300)                 # comments and the cut line dropped
        no_echo = sum(1 for r in valid if math.isnan(r.dist_cm))
        self.assertTrue(3 <= no_echo <= 20)
        self.assertEqual([r.ms for r in valid], list(range(0, 60000, 200)))

    def test_alarm_fires_after_the_heater(self):
        avg, alarm = MovingAverage(5), LimitAlarm(18, 28, 0.5)
        first_high = None
        for s in node_lines():
            r = parse_line(s)
            if r.valid and alarm.step(avg.step(r.temp_c)) == HIGH and first_high is None:
                first_high = r.ms
        self.assertIsNotNone(first_high)
        self.assertTrue(30000 < first_high < 45000)       # heater on at 20 s, 28 C reached later

    def test_stats_and_log_row(self):
        s = Stats()
        for x in [3, float("nan"), 1, 2]:
            s.add(x)
        self.assertEqual(s.summary(), (1, 3, 2))
        self.assertIsNone(Stats().summary())
        r = parse_line("200,22.9,,70")
        self.assertEqual(log_row(r, 22.95, OK), "200\t22.90\t22.95\t\t70.00\tOK")

    def test_vectors_are_current(self):
        with open(os.path.join(ROOT, "test_vectors", "node_stream.txt")) as f:
            self.assertEqual(f.read().splitlines(), node_lines())


if __name__ == "__main__":
    unittest.main()
