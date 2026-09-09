#!/usr/bin/env python3
"""Local scenario arithmetic. No data fetching, ranking, or investment verdicts."""

import argparse
import json
import math


def checked(value, name, minimum=0, maximum=None, strict=False):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: a finite number is required") from None
    if not math.isfinite(number):
        raise ValueError(f"{name}: a finite number is required")
    if number < minimum or (strict and number == minimum):
        raise ValueError(f"{name}: must be {'>' if strict else '>='} {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name}: must be <= {maximum}")
    return number


def supply(terminal_units, units_per_terminal, share, good_capacity, price, margin):
    """All quantities refer to the same period; capacity is already good units."""
    terminal_units = checked(terminal_units, "terminal_units")
    units_per_terminal = checked(units_per_terminal, "units_per_terminal")
    share = checked(share, "share", maximum=1)
    good_capacity = checked(good_capacity, "good_capacity")
    price = checked(price, "price")
    # Negative gross margin is valid; losses can exceed revenue.
    margin = checked(margin, "margin", minimum=-math.inf, maximum=1)
    demand = terminal_units * units_per_terminal * share
    delivered = min(demand, good_capacity)
    revenue = delivered * price
    gross_profit = revenue * margin
    if not all(math.isfinite(v) for v in (demand, revenue, gross_profit)):
        raise ValueError("calculation overflow")
    return {"demand_units": demand, "delivered_units": delivered,
            "revenue": revenue, "gross_profit_not_net_income": gross_profit}


def implied_eps(price, required_return, years, terminal_pe):
    """Conditional terminal EPS in a simplified model with no dividends."""
    price = checked(price, "price", strict=True)
    required_return = checked(required_return, "required_return", minimum=-1, strict=True)
    years = checked(years, "years", strict=True)
    terminal_pe = checked(terminal_pe, "terminal_pe", strict=True)
    try:
        result = price * (1 + required_return) ** years / terminal_pe
    except OverflowError:
        raise ValueError("calculation overflow") from None
    if not math.isfinite(result):
        raise ValueError("calculation overflow")
    return {"required_terminal_eps_not_forecast": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("supply", help="same-period revenue and gross profit scenario")
    for flag in ("terminal-units", "units-per-terminal", "share", "good-capacity", "price", "margin"):
        s.add_argument(f"--{flag}", required=True, type=float)
    i = sub.add_parser("implied", help="no-dividend conditional EPS requirement")
    for flag in ("price", "required-return", "years", "terminal-pe"):
        i.add_argument(f"--{flag}", required=True, type=float)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = supply(**args) if mode == "supply" else implied_eps(**args)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"assumptions": args, "result": result,
                      "scope": "conditional arithmetic only; not a forecast or allocation decision"},
                     ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
