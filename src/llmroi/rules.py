"""Baseline without AI: keyword lists and regular expressions.

This is what a team could build in a day with no API cost. It gives a real, measured
point to compare the LLMs against: how far do simple rules get, and where do they break?
It returns the same JSON shape as the LLM prompt asks for, so it is scored the same way.
"""

import json
import re
from datetime import date

from .catalog import DESTINATIONS, PRODUCTS, normalize_unit
from .labels import missing_info, priority

PRODUCT_KEYWORDS = {
    "ctp_plate": ["ctp"],
    "ps_plate": ["ps plate", "ps пластин"],
    "blanket": ["blanket", "полотн"],
    "offset_ink": ["offset ink", " ink", "краск"],
    "fountain_solution": ["fountain solution", "увлажня"],
    "folding_carton": ["folding carton", "cartons", "картонные коробки"],
    "corrugated_box": ["corrugated", "гофро"],
    "paper_bag": ["paper bag", "пакет"],
    "label": ["label", "этикет"],
}
# Words that usually mean "not a buyer"
SPAM_WORDS = ["seo", "log in", "login", "http", "registration fee", "freight forwarder", "expo",
              "survey", "my cv", "looking for a job", "продвижени", "price list", "catalogue"]

NUM = r"(\d{1,3}(?:[ ,]\d{3})+|\d+(?:\.\d+)?)"
UNIT = r"(sqm|sq\.m|m2|m²|pcs|pieces|kgs|kg|liters|litres|l|шт|м2|м²|кг|л)"
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun",
                                          "jul", "aug", "sep", "oct", "nov", "dec"])}


def to_number(text):
    return float(re.sub(r"[ ,]", "", text))


# date() that returns None instead of crashing on impossible dates like 31.02
def safe_date(year, month, day):
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


# Which catalog products are mentioned (first keyword hit wins, in order of appearance)
def find_products(text):
    low = text.lower()
    hits = []
    for key, words in PRODUCT_KEYWORDS.items():
        positions = [low.find(w) for w in words if w in low]
        if positions:
            hits.append((min(positions), key))
    return [key for _, key in sorted(hits)]


# Collect anything that looks like a size, thickness, grade, ply, color or type
def find_spec(text):
    patterns = [
        r"\d{2,4}\s*[x×*х]\s*\d{2,4}(?:\s*[x×*х]\s*\d{1,4}(?:[.,]\d+)?)?",
        r"\d[.,]\d{1,2}\s*(?:mm|мм)",
        r"\d{2,3}\s*(?:gsm|g/m2|г/м2)",
        r"\d\s*-?\s*(?:ply|layers?)",
        r"cyan|magenta|yellow|black|alcohol[- ]free|semi[- ]gloss|thermal",
    ]
    found = []
    for pattern in patterns:
        found += re.findall(pattern, text, flags=re.IGNORECASE)
    return ", ".join(found) if found else None


# First "number + unit"; prefer the one right after a "Quantity:" label
def find_quantity(text):
    labelled = re.search(r"(?:quantity|qty|количество)\s*:?\s*" + NUM + r"\s*" + UNIT + r"(?!\w)",
                         text, flags=re.IGNORECASE)
    m = labelled or re.search(NUM + r"\s*(k)?\s*" + UNIT + r"(?!\w)", text, flags=re.IGNORECASE)
    if not m:
        return None, None
    value = to_number(m.group(1))
    if not labelled and m.group(2):
        value *= 1000
    return value, normalize_unit(m.groups()[-1])


# Target price: the first amount with a currency after the word target/price/цена
def find_price(text):
    m = re.search(r"(target|price|цена)", text, flags=re.IGNORECASE)
    if not m:
        return None
    rest = text[m.start():]
    pats = [(r"(USD|EUR|US\$|\$|€)\s*(\d+(?:[.,]\d+)?)", 1, 2),
            (r"(\d+(?:[.,]\d+)?)\s*(USD|EUR|руб|RUB)", 2, 1)]
    best = None
    for pat, cur_group, num_group in pats:
        hit = re.search(pat, rest, flags=re.IGNORECASE)
        if hit and (best is None or hit.start() < best[0]):
            best = (hit.start(), hit.group(cur_group), hit.group(num_group))
    if not best:
        return None
    cur = best[1].upper()
    cur = {"$": "USD", "US$": "USD", "€": "EUR", "РУБ": "RUB"}.get(cur, cur)
    return {"value": float(best[2].replace(",", ".")), "currency": cur}


def find_incoterm(text):
    m = re.search(r"\b(EXW|FCA|FOB|CFR|CIF|DAP|DDP)\b", text)
    return m.group(1) if m else None


# The destination mentioned first in the text
def find_destination(text):
    low = text.lower().replace("-", " ")
    best = None
    for name, aliases in DESTINATIONS.items():
        for alias in aliases:
            pos = low.find(alias)
            if pos >= 0 and (best is None or pos < best[0]):
                best = (pos, name)
    return best[1] if best else None


# First date or lead time in the text
def find_delivery(text, received):
    low = text.lower()
    candidates = []
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", low):
        candidates.append((m.start(), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"))
    for m in re.finditer(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", low):
        candidates.append((m.start(), safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
    for m in re.finditer(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:,\s*(\d{4}))?", low):
        year = int(m.group(3)) if m.group(3) else received.year
        candidates.append((m.start(), safe_date(year, MONTHS[m.group(1)], int(m.group(2)))))
    for m in re.finditer(r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", low):
        candidates.append((m.start(), safe_date(received.year, MONTHS[m.group(2)], int(m.group(1)))))
    for m in re.finditer(r"(\d+)\s*(days?|weeks?|дней|дня)", low):
        n = int(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
        candidates.append((m.start(), f"{n} days"))
    candidates = [c for c in candidates if c[1]]
    return min(candidates)[1] if candidates else None


# The whole baseline: message text -> JSON string in the same shape as the LLM output
def extract(text, received):
    received = date.fromisoformat(received)
    empty = {"items": [], "incoterm": None, "destination": None, "delivery": None,
             "missing_info": [], "priority": "low", "priority_reason": "Rules: no catalog product or spam words."}
    low = text.lower()
    products = find_products(text)
    if not products or any(w in low for w in SPAM_WORDS):
        return json.dumps(empty)

    items = []
    lines = text.splitlines()
    for key in products:
        # With several products, read each product's own line; with one, read the whole message
        context = text
        if len(products) > 1:
            context = next((ln for ln in lines if any(w in ln.lower() for w in PRODUCT_KEYWORDS[key])), text)
        qty, unit = find_quantity(context)
        items.append({"product": key, "spec": find_spec(context), "quantity": qty,
                      "unit": unit or (PRODUCTS[key]["unit"] if qty else None),
                      "target_price": find_price(context)})

    incoterm = find_incoterm(text)
    destination = find_destination(text)
    delivery = find_delivery(text, received)
    # Reuse the labeling rubric for priority and missing fields
    for_rubric = [{"product": it["product"], "spec": [it["spec"]] if it["spec"] else [],
                   "quantity": it["quantity"]} for it in items]
    level = priority(for_rubric, incoterm, destination)
    return json.dumps({
        "items": items, "incoterm": incoterm, "destination": destination, "delivery": delivery,
        "missing_info": missing_info(for_rubric, incoterm, destination, delivery),
        "priority": level, "priority_reason": f"Rules: {level} by the written rubric.",
    }, ensure_ascii=False)
