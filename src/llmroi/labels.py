"""Labeling rules shared by every inquiry, so the answer key follows one written rubric.

The person labeling writes down what the email says (items, Incoterm, destination, delivery).
"missing_info" and "priority" are then derived here by fixed rules, not by feel.
"""

from .catalog import PRODUCTS


# One requested product line
def item(product, spec=None, quantity=None, unit=None, price=None, currency=None):
    return {
        "product": product,
        "spec": spec or [],                       # key spec tokens, e.g. ["1030x790", "0.3mm"]
        "quantity": quantity,
        "unit": unit or (PRODUCTS[product]["unit"] if quantity is not None else None),
        "target_price": None if price is None else {"value": price, "currency": currency or "USD"},
    }


# Which of the five quote fields are absent
def missing_info(items, incoterm, destination, delivery):
    if not items:
        return []
    missing = []
    if any(not it["spec"] for it in items):
        missing.append("spec")
    if any(it["quantity"] is None for it in items):
        missing.append("quantity")
    if destination is None:
        missing.append("destination")
    if incoterm is None:
        missing.append("incoterm")
    if delivery is None:
        missing.append("delivery")
    return missing


# High = complete and at or above MOQ with a place to ship to; low = not a real catalog request
def priority(items, incoterm, destination):
    if not items:
        return "low"
    complete = all(it["spec"] and it["quantity"] is not None for it in items)
    at_moq = all(it["quantity"] is not None and it["quantity"] >= PRODUCTS[it["product"]]["moq"]
                 for it in items)
    if complete and at_moq and (incoterm or destination):
        return "high"
    return "medium"


# Short reason written from the same rule
def priority_reason(level, items, incoterm, destination, kind="genuine"):
    if level == "low":
        return {
            "spam": "Not a purchase inquiry (marketing or service offer).",
            "phishing": "Suspicious message (link, login or fee request), not a buyer.",
            "generic": "Generic request with no product details.",
            "off_catalog": "Asks for products we do not sell.",
        }.get(kind, "Not a purchase inquiry for our catalog.")
    if level == "high":
        return "Complete request at or above MOQ with shipping terms or destination."
    gaps = []
    if any(not it["spec"] for it in items):
        gaps.append("missing spec")
    if any(it["quantity"] is None for it in items):
        gaps.append("missing quantity")
    if any(it["quantity"] is not None and it["quantity"] < PRODUCTS[it["product"]]["moq"] for it in items):
        gaps.append("below MOQ")
    if not (incoterm or destination):
        gaps.append("no terms or destination")
    return "Genuine buyer, but " + ", ".join(gaps) + "."


# Build the full answer-key record for one inquiry
def gold_record(inq_id, items, incoterm=None, destination=None, delivery=None, kind="genuine"):
    level = priority(items, incoterm, destination)
    return {
        "id": inq_id,
        "items": items,
        "incoterm": incoterm,
        "destination": destination,
        "delivery": delivery,
        "missing_info": missing_info(items, incoterm, destination, delivery),
        "priority": level,
        "priority_reason": priority_reason(level, items, incoterm, destination, kind),
    }
