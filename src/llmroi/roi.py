"""ROI model: is AI-assisted inquiry handling worth it, and how accurate must it be?

Per inquiry, compared with doing it by hand:
    minutes saved   = manual - review - error_rate x catch_rate x fix_minutes
    labor saved     = minutes saved x hourly cost / 60
    error cost      = (error_rate x (1 - catch_rate) - manual_error_rate) x cost of one escaped error
    net per inquiry = labor saved - API cost - error cost
The error cost is measured against doing it by hand, because people make mistakes too. It can be
negative: an AI draft plus a review can let fewer mistakes through than one person alone.
Per month:
    net per month   = volume x net per inquiry - maintenance
    payback months  = setup cost / net per month
"error_rate" is the critical error rate from scoring: the share of inquiries with at least one
wrong product, spec, quantity, target price or delivery date, an invented item, or a missed high-priority lead.
"""

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"


def load_inputs(column="value"):
    with open(DATA / "roi_inputs.csv", encoding="utf-8") as f:
        return {row["name"]: float(row[column]) for row in csv.DictReader(f)}


def load_input_table():
    with open(DATA / "roi_inputs.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Fully loaded labor cost of a salesperson, USD per hour
def hourly_cost_usd(inp):
    return inp["monthly_salary_cny"] * inp["employer_overhead"] / inp["hours_per_month"] / inp["usd_cny"]


def per_inquiry(inp, error_rate, api_cost):
    wage = hourly_cost_usd(inp)
    minutes_saved = inp["manual_minutes"] - inp["review_minutes"] - error_rate * inp["catch_rate"] * inp["fix_minutes"]
    labor_saved = minutes_saved * wage / 60
    error_cost = (error_rate * (1 - inp["catch_rate"]) - inp["manual_error_rate"]) * inp["escaped_error_cost_usd"]
    return {
        "manual_cost": inp["manual_minutes"] * wage / 60,
        "minutes_saved": minutes_saved,
        "labor_saved": labor_saved,
        "api_cost": api_cost,
        "error_cost": error_cost,
        "net": labor_saved - api_cost - error_cost,
    }


def monthly(inp, error_rate, api_cost):
    unit = per_inquiry(inp, error_rate, api_cost)
    net = inp["monthly_volume"] * unit["net"] - inp["monthly_maintenance_usd"]
    payback = inp["setup_cost_usd"] / net if net > 0 else None
    return {**unit, "net_month": net, "payback_months": payback}


# The highest critical error rate at which the monthly net benefit is still zero or better
# (monthly maintenance included; the one-time setup cost is handled by the payback period)
def breakeven_error_rate(inp, api_cost):
    wage = hourly_cost_usd(inp)
    gain = ((inp["manual_minutes"] - inp["review_minutes"]) * wage / 60 - api_cost
            + inp["manual_error_rate"] * inp["escaped_error_cost_usd"]
            - inp["monthly_maintenance_usd"] / inp["monthly_volume"])
    loss_per_error = inp["catch_rate"] * inp["fix_minutes"] * wage / 60 + (1 - inp["catch_rate"]) * inp["escaped_error_cost_usd"]
    return max(gain / loss_per_error, 0.0)


# The monthly volume needed to pay back the setup cost within `months`
def breakeven_volume(inp, error_rate, api_cost, months=12):
    unit = per_inquiry(inp, error_rate, api_cost)["net"]
    if unit <= 0:
        return None
    return (inp["setup_cost_usd"] / months + inp["monthly_maintenance_usd"]) / unit


# One-at-a-time sensitivity: how far each assumption moves the break-even error rate
def sensitivity(api_cost):
    base = load_inputs()
    low, high = load_inputs("low"), load_inputs("high")
    rows = []
    for name in base:
        if low[name] == high[name] or name == "setup_cost_usd":
            continue                       # fixed values, and the one-time cost (it only changes payback time)
        results = []
        for value in (low[name], high[name]):
            changed = dict(base, **{name: value})
            results.append(breakeven_error_rate(changed, api_cost))
        rows.append({"input": name, "low_value": low[name], "high_value": high[name],
                     "breakeven_at_low": results[0], "breakeven_at_high": results[1],
                     "swing": abs(results[1] - results[0])})
    return sorted(rows, key=lambda r: r["swing"], reverse=True)


# Rough token count when no API run exists yet: about 4 characters per token for English,
# about 2.5 for Russian and other non-Latin text. Replaced by real token counts after a run.
def estimate_tokens(text):
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    return ascii_chars / 4 + (len(text) - ascii_chars) / 2.5
