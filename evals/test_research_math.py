"""Arithmetic and invalid-input regression tests; not investment validation."""

import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
