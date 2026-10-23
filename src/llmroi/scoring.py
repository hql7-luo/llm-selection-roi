"""Score a method's outputs against the answer key.

Every method (rules or LLM) is scored by the same code. Steps for one inquiry:
1. parse the raw output as JSON (failure = every field wrong),
2. put values into standard form (units, ports, dates, spec text),
3. match predicted items to answer-key items by product,
4. mark each field right or wrong, and count invented values.
"""

import csv
import json
import re
from pathlib import Path

from .catalog import (normalize_currency, normalize_delivery, normalize_destination, normalize_incoterm,
                      normalize_product, normalize_spec, normalize_unit)

DATA = Path(__file__).resolve().parents[2] / "data"

ITEM_FIELDS = ["product", "spec", "quantity", "target_price"]
HEADER_FIELDS = ["incoterm", "destination", "delivery", "missing_info", "priority"]
FIELDS = ITEM_FIELDS + HEADER_FIELDS
# A wrong value here could reach a customer in a quote
CRITICAL_FIELDS = ["product", "spec", "quantity", "target_price", "delivery"]
PRIORITIES = ["high", "medium", "low"]


def load_weights():
    with open(DATA / "field_weights.csv", encoding="utf-8") as f:
        return {row["field"]: float(row["weight"]) for row in csv.DictReader(f)}


# Raw model text -> dict, or None if it is not valid JSON with the expected keys
def parse_output(raw):
    if raw is None:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items", []), list):
        return None
    return data


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


# Put one parsed output into standard form
def normalize_prediction(data):
    items = []
    for it in data.get("items") or []:
        if not isinstance(it, dict):
            continue
        price = it.get("target_price")
        if isinstance(price, dict) and to_float(price.get("value")) is not None:
            price = {"value": to_float(price.get("value")), "currency": normalize_currency(price.get("currency"))}
        else:
            price = None
        items.append({
            "product": normalize_product(it.get("product")),
            "spec": normalize_spec(it.get("spec")) or None,
            "quantity": to_float(it.get("quantity")),
            "unit": normalize_unit(it.get("unit")),
            "target_price": price,
        })
    missing = data.get("missing_info") or []
    return {
        "items": items,
        "incoterm": normalize_incoterm(data.get("incoterm")),
        "destination": normalize_destination(data.get("destination")),
        "delivery": normalize_delivery(data.get("delivery")),
        "missing_info": sorted(str(m).lower() for m in missing) if isinstance(missing, list) else [],
        "priority": str(data.get("priority") or "").strip().lower(),
    }


def close(a, b, tol=0.005):
    return a is not None and b is not None and abs(a - b) <= tol * max(abs(b), 1e-9)


# Compare one item field; returns (correct, invented)
def check_item_field(field, gold_item, pred_item):
    if field == "product":
        return pred_item is not None, False
    if field == "spec":
        tokens = [normalize_spec(t) for t in gold_item["spec"]]
        pred_spec = pred_item["spec"] if pred_item else None
        if not tokens:
            return pred_spec is None, pred_spec is not None
        return pred_spec is not None and all(t in pred_spec for t in tokens), False
    if field == "quantity":
        q = pred_item["quantity"] if pred_item else None
        if gold_item["quantity"] is None:
            return q is None, q is not None
        return close(q, gold_item["quantity"]) and pred_item["unit"] == gold_item["unit"], False
    if field == "target_price":
        p = pred_item["target_price"] if pred_item else None
        g = gold_item["target_price"]
        if g is None:
            return p is None, p is not None
        return p is not None and close(p["value"], g["value"], 0.01) and p["currency"] == g["currency"], False
    raise ValueError(field)


# Score one inquiry. Returns a dict with per-field checks and summary flags.
def score_inquiry(gold, raw, weights):
    data = parse_output(raw)
    json_ok = data is not None
    pred = normalize_prediction(data) if json_ok else None

    checks = []          # (field, correct)
    invented = 0         # values filled in where the email gives none
    chances = 0          # places where inventing was possible
    unused = list(pred["items"]) if pred else []

    for g_item in gold["items"]:
        match = next((p for p in unused if p["product"] == g_item["product"]), None)
        if match is not None:
            unused.remove(match)
        for field in ITEM_FIELDS:
            if not json_ok:
                checks.append((field, False))
                continue
            ok, made_up = check_item_field(field, g_item, match)
            checks.append((field, ok))
            if field != "product" and match is not None and _gold_empty(field, g_item):
                chances += 1
                invented += made_up

    extra_items = len(unused) if json_ok else 0

    for field in HEADER_FIELDS:
        if not json_ok:
            checks.append((field, False))
            continue
        g, p = gold[field], pred[field]
        if field == "missing_info":
            ok = sorted(g) == p
        else:
            ok = (g == p) or (g is None and p in (None, ""))
        checks.append((field, ok))
        if field in ("incoterm", "destination", "delivery") and g is None:
            chances += 1
            invented += p is not None

    wrong = [f for f, ok in checks if not ok]
    pred_priority = pred["priority"] if json_ok else None
    missed_high = gold["priority"] == "high" and pred_priority != "high"
    critical = (not json_ok or extra_items > 0 or missed_high
                or any(f in CRITICAL_FIELDS for f in wrong))
    return {
        "id": gold["id"],
        "json_ok": json_ok,
        "checks": checks,
        "extra_items": extra_items,
        "invented": invented,
        "chances": chances,
        "critical_error": critical,
        "missed_high": missed_high,
        "weighted_error": sum(weights[f] for f in wrong) + extra_items * weights["extra_item"],
        "gold_priority": gold["priority"],
        "pred_priority": pred_priority if pred_priority in PRIORITIES else "invalid",
        "normalized": json.dumps(pred, sort_keys=True) if json_ok else None,
    }


def _gold_empty(field, g_item):
    if field == "spec":
        return not g_item["spec"]
    if field == "quantity":
        return g_item["quantity"] is None
    if field == "target_price":
        return g_item["target_price"] is None
    return False
