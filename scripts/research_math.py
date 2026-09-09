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


def exposure(portfolio_value, positions, limit):
    """Bounds for one category in a long-only, unlevered portfolio.

    Unlisted portfolio value is unknown, not cash. Each row has value,
    known_fraction (in this category), and unknown_fraction (unclassified).
    """
    portfolio_value = checked(portfolio_value, "portfolio_value", strict=True)
    limit = checked(limit, "limit", maximum=1)
    if not isinstance(positions, list):
        raise ValueError("positions: a JSON array is required")
    amounts, known_amounts, unknown_amounts = [], [], []
    for index, row in enumerate(positions):
        if not isinstance(row, dict):
            raise ValueError(f"positions[{index}]: an object is required")
        prefix = f"positions[{index}]"
        value = checked(row.get("value"), f"{prefix}.value")
        known = checked(row.get("known_fraction"), f"{prefix}.known_fraction", maximum=1)
        unknown = checked(row.get("unknown_fraction"), f"{prefix}.unknown_fraction", maximum=1)
        if known + unknown > 1:
            raise ValueError(f"{prefix}: known_fraction + unknown_fraction must be <= 1")
        amounts.append(value)
        known_amounts.append(value * known)
        unknown_amounts.append(value * unknown)
    try:
        listed = math.fsum(amounts)
        if listed > portfolio_value and not math.isclose(listed, portfolio_value, rel_tol=1e-12):
            raise ValueError("listed positions exceed portfolio_value; check double counting")
        known_value = math.fsum(known_amounts)
        unknown_value = math.fsum(unknown_amounts) + max(0, portfolio_value - listed)
    except OverflowError:
        raise ValueError("calculation overflow") from None
    lower = min(1, known_value / portfolio_value)
    upper = min(1, (known_value + unknown_value) / portfolio_value)
    if lower > limit:
        status = "known_breach"
    elif upper <= limit:
        status = "within_given_bounds_only"
    else:
        status = "insufficient_information"
    return {"lower_fraction": lower, "upper_fraction": upper,
            "known_amount": known_value, "unknown_amount": unknown_value,
            "single_constraint_status_not_allocation_verdict": status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("supply", help="same-period revenue and gross profit scenario")
    for flag in ("terminal-units", "units-per-terminal", "share", "good-capacity", "price", "margin"):
        s.add_argument(f"--{flag}", required=True, type=float)
    i = sub.add_parser("implied", help="no-dividend conditional EPS requirement")
    for flag in ("price", "required-return", "years", "terminal-pe"):
        i.add_argument(f"--{flag}", required=True, type=float)
    e = sub.add_parser("exposure", help="long-only category bounds; unlisted amounts are unknown")
    e.add_argument("--portfolio-value", required=True, type=float)
    e.add_argument("--limit", required=True, type=float)
    e.add_argument("--positions", required=True, type=json.loads,
                   help="JSON array: value, known_fraction, unknown_fraction per position")
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        result = {"supply": supply, "implied": implied_eps, "exposure": exposure}[mode](**args)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"assumptions": args, "result": result,
                      "scope": "conditional arithmetic only; not a forecast or allocation decision"},
                     ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
