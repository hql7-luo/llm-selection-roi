"""The fictional exporter's catalog, plus small helpers that put values into one standard form.

Every method (rules or an LLM) is scored after its output goes through these same helpers,
so "3,000 m2" and "3000 sqm" count as the same answer.
"""

import re
from datetime import date, timedelta

# Products the fictional exporter sells: key -> display name, quoting unit, minimum order quantity
PRODUCTS = {
    "ctp_plate":         {"name": "CTP plate",            "unit": "sqm", "moq": 1000},
    "ps_plate":          {"name": "PS plate",             "unit": "sqm", "moq": 1000},
    "blanket":           {"name": "printing blanket",     "unit": "pcs", "moq": 50},
    "offset_ink":        {"name": "offset ink",           "unit": "kg",  "moq": 500},
    "fountain_solution": {"name": "fountain solution",    "unit": "L",   "moq": 400},
    "folding_carton":    {"name": "folding carton",       "unit": "pcs", "moq": 10000},
    "corrugated_box":    {"name": "corrugated box",       "unit": "pcs", "moq": 5000},
    "paper_bag":         {"name": "paper bag",            "unit": "pcs", "moq": 5000},
    "label":             {"name": "self-adhesive label",  "unit": "pcs", "moq": 50000},
}

INCOTERMS = ["EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP"]

# Destination cities and ports, with the other spellings buyers use
DESTINATIONS = {
    "Novorossiysk":     ["novorossiysk", "новороссийск"],
    "Saint Petersburg": ["saint petersburg", "st. petersburg", "st petersburg", "санкт петербург", "spb"],
    "Moscow":           ["moscow", "москва", "москву"],
    "Vladivostok":      ["vladivostok", "владивосток"],
    "Almaty":           ["almaty", "алматы"],
    "Minsk":            ["minsk", "минск"],
    "Tashkent":         ["tashkent", "ташкент"],
    "Istanbul":         ["istanbul"],
    "Hamburg":          ["hamburg"],
    "Rotterdam":        ["rotterdam"],
    "Jebel Ali":        ["jebel ali"],
    "Mombasa":          ["mombasa"],
    "Santos":           ["santos"],
}

# The five things a salesperson needs before quoting; used for "missing_info"
QUOTE_FIELDS = ["spec", "quantity", "destination", "incoterm", "delivery"]

UNIT_ALIASES = {
    "sqm": ["sqm", "m2", "m²", "sq m", "sq.m", "square meters", "square metres", "м2", "м²", "кв.м", "кв. м"],
    "pcs": ["pcs", "pc", "pieces", "piece", "units", "boxes", "bags", "sheets", "шт", "шт."],
    "kg":  ["kg", "kgs", "kilograms", "kilogram", "кг"],
    "L":   ["l", "liters", "litres", "liter", "litre", "л"],
}


# Turn any unit spelling into one of: sqm, pcs, kg, L (or None if unknown)
def normalize_unit(text):
    if text is None:
        return None
    t = str(text).strip().lower().rstrip(".")
    for unit, aliases in UNIT_ALIASES.items():
        if t in aliases or t == unit.lower():
            return unit
    return None


# Accept a product key ("ctp_plate") or its catalog name ("CTP plate")
def normalize_product(text):
    t = str(text or "").strip().lower()
    for key, p in PRODUCTS.items():
        if t in (key, key.replace("_", " "), p["name"].lower()):
            return key
    return t


# Turn any destination spelling into the standard English name (or None)
def normalize_destination(text):
    if not text:
        return None
    t = str(text).strip().lower().replace("-", " ")
    for name, aliases in DESTINATIONS.items():
        if t == name.lower() or any(a in t for a in aliases):
            return name
    return str(text).strip()


# Keep only a valid Incoterm code, e.g. "c.i.f." -> "CIF", "CIF Novorossiysk" -> "CIF"
def normalize_incoterm(text):
    if not text:
        return None
    first = str(text).strip().split()[0]
    t = re.sub(r"[^A-Za-z]", "", first).upper()
    return t if t in INCOTERMS else None


# "$" -> "USD", "€" -> "EUR", "RMB" -> "CNY", "руб" -> "RUB"
def normalize_currency(text):
    t = str(text or "").strip().upper()
    return {"$": "USD", "US$": "USD", "€": "EUR", "¥": "CNY", "RMB": "CNY", "₽": "RUB", "RUR": "RUB",
            "РУБ": "RUB", "РУБ.": "RUB"}.get(t, t)


# Make spec text comparable: lower case, no spaces, one "x", numbers without trailing zeros
def normalize_spec(text):
    if text is None:
        return ""
    if isinstance(text, list):
        text = " ".join(str(t) for t in text)
    t = str(text).lower()
    t = t.replace("×", "x").replace("*", "x").replace("х", "x")      # the last one is Cyrillic
    t = t.replace("мм", "mm")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)                              # 1,95 -> 1.95
    t = re.sub(r"g/m2|g/m²|г/м2|г/м²|gr/m2", "gsm", t)
    t = re.sub(r"\s*-?\s*(ply|layers?|layer)\b", "ply", t)
    t = re.sub(r"\s+", "", t)
    t = t.replace("semigloss", "semi-gloss").replace("alcoholfree", "alcohol-free")
    t = re.sub(r"\d+\.\d+", lambda m: f"{float(m.group()):g}", t)      # 0.30 -> 0.3
    return t


# Delivery in standard form: "YYYY-MM-DD" for a date, "N days" for a lead time, else None
def normalize_delivery(text):
    if text is None:
        return None
    t = str(text).strip().lower()
    if not t or t in ("null", "none", "asap"):
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    m = re.search(r"(\d+)\s*(days?|weeks?)", t)
    if m:
        n = int(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
        return f"{n} days"
    return None


# Lead time in days, used to compare two delivery answers fairly
def delivery_matches(pred, gold):
    return normalize_delivery(pred) == normalize_delivery(gold)


# Add days to a date (used by the dataset builder)
def add_days(day, n):
    return (day + timedelta(days=n)).isoformat()
