"""Arithmetic and invalid-input regression tests; not investment validation."""

import importlib.util
from pathlib import Path
import unittest
import subprocess
import sys
import json

spec = importlib.util.spec_from_file_location(
    "research_math", Path(__file__).resolve().parents[1] / "scripts" / "research_math.py")
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


class ResearchMathTests(unittest.TestCase):
    def test_capacity_limits_sales(self):
        result = calc.supply(1_000_000, 2, .1, 150_000, 100, .3)
        self.assertEqual(result["delivered_units"], 150_000)
        self.assertEqual(result["revenue"], 15_000_000)
        self.assertEqual(result["gross_profit_not_net_income"], 4_500_000)

    def test_unused_capacity_is_not_sales(self):
        self.assertEqual(calc.supply(100, 2, .1, 1000, 10, .3)["revenue"], 200)

    def test_zero_share(self):
        self.assertEqual(calc.supply(100, 2, 0, 1000, 10, .3)["revenue"], 0)

    def test_loss_making_gross_margin(self):
        self.assertEqual(calc.supply(100, 1, 1, 100, 10, -.2)
                         ["gross_profit_not_net_income"], -200)

    def test_implied_eps(self):
        self.assertAlmostEqual(calc.implied_eps(100, .1, 2, 20)
                               ["required_terminal_eps_not_forecast"], 6.05)

    def test_invalid_supply_inputs(self):
        base = [100, 2, .1, 1000, 10, .3]
        for index, value in [(0, None), (0, True), (0, float("nan")),
                             (2, 10), (3, -1), (4, float("inf")), (5, 1.1)]:
            with self.subTest(index=index, value=value):
                args = base.copy()
                args[index] = value
                with self.assertRaises(ValueError):
                    calc.supply(*args)

    def test_invalid_valuation_inputs(self):
        for args in [(100, .1, 2, 0), (100, -1, 2, 20), (100, .1, 0, 20),
                     (100, .1, 2, float("nan"))]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                calc.implied_eps(*args)

    def test_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            calc.implied_eps(100, 10, 1000, 20)

    def test_partial_exposure_spans_limit(self):
        result = calc.exposure(100, [
            {"value": 20, "known_fraction": .5, "unknown_fraction": .5},
            {"value": 20, "known_fraction": .25, "unknown_fraction": .75},
            {"value": 10, "known_fraction": 1, "unknown_fraction": 0},
            {"value": 50, "known_fraction": 0, "unknown_fraction": 0}], .3)
        self.assertEqual(result["lower_fraction"], .25)
        self.assertEqual(result["upper_fraction"], .5)
        self.assertEqual(result["single_constraint_status_not_allocation_verdict"],
                         "insufficient_information")

    def test_unlisted_balance_is_unknown(self):
        result = calc.exposure(100, [{"value": 25, "known_fraction": 1,
                                     "unknown_fraction": 0}], .3)
        self.assertEqual(result["unknown_amount"], 75)
        self.assertEqual(result["upper_fraction"], 1)

    def test_known_breach_despite_unknowns(self):
        result = calc.exposure(100, [{"value": 40, "known_fraction": 1,
                                     "unknown_fraction": 0}], .3)
        self.assertEqual(result["single_constraint_status_not_allocation_verdict"],
                         "known_breach")

    def test_full_coverage_at_limit(self):
        result = calc.exposure(100, [{"value": 100, "known_fraction": .3,
                                     "unknown_fraction": 0}], .3)
        self.assertEqual(result["single_constraint_status_not_allocation_verdict"],
                         "within_given_bounds_only")

    def test_exposure_rejects_missing_and_inconsistent_inputs(self):
        for total, rows in [
            (0, []), (100, {}), (100, [None]),
            (100, [{"value": 100, "known_fraction": .5}]),
            (100, [{"value": 100, "known_fraction": .8, "unknown_fraction": .3}]),
            (100, [{"value": 101, "known_fraction": .5, "unknown_fraction": 0}]),
            (100, [{"value": -1, "known_fraction": .5, "unknown_fraction": 0}])]:
            with self.subTest(total=total, rows=rows), self.assertRaises(ValueError):
                calc.exposure(total, rows, .3)

    def test_exposure_cli(self):
        script = str(Path(__file__).resolve().parents[1] / "scripts" / "research_math.py")
        run = subprocess.run([sys.executable, script, "exposure", "--portfolio-value", "100",
                              "--limit", ".3", "--positions", "[]"],
                             text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(run.stdout)["result"]["upper_fraction"], 1)
        invalid = subprocess.run([sys.executable, script, "exposure", "--portfolio-value", "100",
                                  "--limit", ".3", "--positions", "not-json"],
                                 text=True, capture_output=True)
        self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
