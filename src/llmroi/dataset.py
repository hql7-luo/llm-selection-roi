"""Builds the 60 'regular' inquiries from templates and loads the full dataset.

Regular inquiries look like what a sales inbox gets every day: Alibaba RFQ forms, short emails,
chat messages and a few in Russian. The answer key comes straight from the values that were
put into each template, so it is exact by construction.
"""

import json
import random
from datetime import date
from pathlib import Path

from .catalog import PRODUCTS, add_days
from .labels import gold_record, item

DATA = Path(__file__).resolve().parents[2] / "data"

# ---------- building blocks ----------

# Spec choices per product: (English text variants, Russian text, answer-key tokens)
def pick_spec(rng, product):
    if product in ("ctp_plate", "ps_plate"):
        w, h = rng.choice([(1030, 790), (745, 605), (1050, 795), (650, 550)])
        t = rng.choice(["0.30", "0.28", "0.24"])
        en = rng.choice([f"{w}x{h} mm, {t} mm", f"size {w}*{h}, thickness {t}mm", f"{w} x {h} x {t} mm"])
        ru = f"{w}х{h} мм, толщина {t.replace('.', ',')} мм"
        return en, ru, [f"{w}x{h}", f"{float(t):g}mm"]
    if product == "blanket":
        w, h = rng.choice([(1050, 840), (790, 660), (1060, 860)])
        t = rng.choice(["1.95", "1.96"])
        en = rng.choice([f"{w}x{h}x{t} mm", f"{w}*{h} mm, {t} mm thick"])
        ru = f"{w}х{h}х{t.replace('.', ',')} мм"
        return en, ru, [f"{w}x{h}", f"{float(t):g}mm"]
    if product == "offset_ink":
        color = rng.choice(["cyan", "magenta", "yellow", "black"])
        en = rng.choice([f"process {color}", f"{color}, sheetfed", f"color: {color}"])
        ru = f"триадная ({color})"
        return en, ru, [color]
    if product == "fountain_solution":
        en = rng.choice(["alcohol-free", "alcohol free, for sheetfed presses", "alcohol-free concentrate"])
        ru = "без спирта (alcohol-free)"
        return en, ru, ["alcohol-free"]
    if product in ("folding_carton", "corrugated_box", "paper_bag"):
        dims = {
            "folding_carton": [(120, 80, 200), (90, 60, 150), (200, 150, 60)],
            "corrugated_box": [(400, 300, 250), (600, 400, 400), (300, 200, 150)],
            "paper_bag": [(260, 120, 350), (320, 110, 420)],
        }[product]
        a, b, c = rng.choice(dims)
        if product == "corrugated_box":
            ply = rng.choice([3, 5])
            en = rng.choice([f"{a}x{b}x{c} mm, {ply}-ply", f"{a}*{b}*{c}mm {ply} ply", f"{a}x{b}x{c}, {ply} layers"])
            ru = f"{a}х{b}х{c} мм, {ply}-слойный ({ply}-ply)"
            return en, ru, [f"{a}x{b}x{c}", f"{ply}ply"]
        gsm = rng.choice([300, 350, 400]) if product == "folding_carton" else rng.choice([100, 120])
        board = "white cardboard" if product == "folding_carton" else "kraft"
        en = rng.choice([f"{a}x{b}x{c} mm, {gsm}gsm {board}", f"{a}*{b}*{c}mm, {gsm} g/m2 {board}"])
        ru = f"{a}х{b}х{c} мм, {gsm} г/м2"
        return en, ru, [f"{a}x{b}x{c}", f"{gsm}gsm"]
    if product == "label":
        w, h = rng.choice([(50, 30), (100, 150), (70, 40)])
        mat = rng.choice(["semi-gloss", "thermal"])
        en = rng.choice([f"{w}x{h} mm, {mat} paper", f"{w}*{h}mm {mat.replace('-', ' ')}"])
        ru = f"{w}х{h} мм, {mat}"
        return en, ru, [f"{w}x{h}", mat]
    raise ValueError(product)


QTY_ABOVE = {
    "ctp_plate": [1500, 2000, 3000, 4000, 6000], "ps_plate": [1500, 2000, 3000, 5000],
    "blanket": [60, 80, 100, 150, 200], "offset_ink": [600, 800, 1000, 1500, 2000],
    "fountain_solution": [500, 600, 800, 1000, 1200], "folding_carton": [15000, 20000, 30000, 50000],
    "corrugated_box": [6000, 8000, 10000, 20000], "paper_bag": [8000, 10000, 20000, 30000],
    "label": [60000, 100000, 200000],
}
QTY_BELOW = {
    "ctp_plate": [300, 500, 800], "ps_plate": [300, 600], "blanket": [10, 20, 30],
    "offset_ink": [100, 200], "fountain_solution": [100, 200], "folding_carton": [3000, 5000],
    "corrugated_box": [1000, 2000], "paper_bag": [1000, 2000], "label": [10000, 20000],
}
PRICE_RANGE = {
    "ctp_plate": (3.0, 4.5), "ps_plate": (2.4, 3.6), "blanket": (35, 60), "offset_ink": (3.5, 6.0),
    "fountain_solution": (2.0, 3.0), "folding_carton": (0.05, 0.20), "corrugated_box": (0.40, 1.50),
    "paper_bag": (0.12, 0.30), "label": (0.004, 0.012),
}
UNIT_TEXT = {"sqm": ["sqm", "m2", "sq.m"], "pcs": ["pcs", "pieces"], "kg": ["kg", "kgs"], "L": ["liters", "L"]}
UNIT_RU = {"sqm": "м2", "pcs": "шт", "kg": "кг", "L": "л"}

# Fictional buyers: (company, country, destinations they use, contact name)
BUYERS = [
    ("Polygraph-Resurs LLC", "Russia", ["Novorossiysk", "Moscow"], "Andrey"),
    ("Severny Print LLC", "Russia", ["Saint Petersburg", "Moscow"], "Olga"),
    ("Vostok Tipografiya LLC", "Russia", ["Vladivostok"], "Sergey"),
    ("Steppe Print LLP", "Kazakhstan", ["Almaty"], "Aigerim"),
    ("Minsk Label House", "Belarus", ["Minsk"], "Pavel"),
    ("Tashkent Pack LLC", "Uzbekistan", ["Tashkent"], "Dilshod"),
    ("Bosphorus Ambalaj Ltd.", "Turkey", ["Istanbul"], "Emre"),
    ("Nordkarton GmbH", "Germany", ["Hamburg"], "Jonas"),
    ("Lowlands Packaging B.V.", "Netherlands", ["Rotterdam"], "Sanne"),
    ("Gulf Print Trading LLC", "UAE", ["Jebel Ali"], "Rashid"),
    ("Coastline Print Ltd.", "Kenya", ["Mombasa"], "Wanjiru"),
    ("Santos Embalagens Ltda.", "Brazil", ["Santos"], "Lucas"),
]
RU_BUYERS = BUYERS[:6]
PORTS = {"Novorossiysk", "Saint Petersburg", "Vladivostok", "Istanbul", "Hamburg", "Rotterdam",
         "Jebel Ali", "Mombasa", "Santos"}
DEST_RU = {"Novorossiysk": "Новороссийск", "Saint Petersburg": "Санкт-Петербург", "Moscow": "Москва",
           "Vladivostok": "Владивосток", "Almaty": "Алматы", "Minsk": "Минск", "Tashkent": "Ташкент"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def fmt_qty(rng, q, unit, russian=False):
    if russian:
        return f"{q:,}".replace(",", " ") + " " + UNIT_RU[unit]
    num = rng.choice([f"{q:,}", f"{q}"])
    return f"{num} {rng.choice(UNIT_TEXT[unit])}"


def fmt_price(rng, value, currency, unit):
    v = f"{value:.3f}".rstrip("0").rstrip(".") if value < 0.1 else f"{value:.2f}"
    per = {"sqm": "sqm", "pcs": "pc", "kg": "kg", "L": "liter"}[unit]
    sym = {"USD": "$", "EUR": "EUR "}[currency]
    return rng.choice([f"{currency} {v}/{per}", f"{sym}{v} per {per}", f"{v} {currency} per {per}"])


# Russian needs "дня" after 21, 31, ... and "дней" otherwise (for the numbers used here)
def ru_days(n):
    return "дня" if n % 10 == 1 and n % 100 != 11 else "дней"


# Delivery: returns (English text, Russian text, answer-key value)
def pick_delivery(rng, received):
    kind = rng.choice(["days", "weeks", "date"])
    if kind == "days":
        n = rng.choice([20, 30, 35, 40, 45, 60])
        return f"within {n} days", f"в течение {n} {ru_days(n)}", f"{n} days"
    if kind == "weeks":
        n = rng.choice([3, 4, 5, 6])
        return f"in {n} weeks", f"в течение {n * 7} {ru_days(n * 7)}", f"{n * 7} days"
    d = date.fromisoformat(add_days(received, rng.choice([30, 40, 45, 55, 60])))
    en = rng.choice([f"before {d.isoformat()}", f"by {MONTHS[d.month - 1]} {d.day}, {d.year}"])
    ru = f"до {d.day:02d}.{d.month:02d}.{d.year}"
    return en, ru, d.isoformat()


# Shipping terms: returns (Incoterm or None, destination or None, how it is written)
def pick_terms(rng, dests):
    dest = rng.choice(dests)
    roll = rng.random()
    if roll < 0.70:
        term = rng.choice(["CIF", "CFR"]) if dest in PORTS else rng.choice(["DAP", "DDP"])
        return term, dest, f"{term} {dest}"
    if roll < 0.82:
        port = rng.choice(["Ningbo", "Shanghai"])
        return "FOB", None, f"FOB {port}"
    if roll < 0.92:
        return None, dest, f"delivery to {dest}"
    return None, None, None


# ---------- the five message formats ----------

def text_rfq_form(p, spec, qty, terms, delivery, price, buyer):
    lines = [f"Subject: RFQ - {p}", "", "Buying request (via Alibaba.com)", f"Product name: {p}"]
    lines.append(f"Specification: {spec}" if spec else "Specification: please advise")
    lines.append(f"Quantity: {qty}")
    if terms:
        lines.append(f"Trade terms: {terms}")
    if price:
        lines.append(f"Target price: {price}")
    if delivery:
        lines.append(f"Delivery time: {delivery}")
    lines.append(f"Buyer: {buyer[0]}, {buyer[1]}")
    return "\n".join(lines)


def text_short_email(p, spec, qty, terms, delivery, price, buyer):
    parts = [f"Hello,\n\nWe are {buyer[0]} from {buyer[1]}. We need {qty} of {p}"]
    parts[0] += f", {spec}." if spec else "."
    if terms:
        parts.append(f"Please quote {terms}.")
    if delivery:
        parts.append(f"We need the goods {delivery}.")
    if price:
        parts.append(f"Our target price is {price}.")
    return " ".join(parts) + f"\n\nBest regards,\n{buyer[3]}"


def text_chat(p, spec, qty, terms, delivery, price, buyer):
    msg = f"hi, price for {p}"
    msg += f" {spec}?" if spec else "?"
    msg += f" qty {qty}"
    if terms:
        msg += f", {terms}"
    if delivery:
        msg += f". need {delivery}"
    if price:
        msg += f". target {price}"
    return msg + f"\n- {buyer[3]}, {buyer[0]}"


def text_formal(p, spec, qty, terms, delivery, price, buyer):
    intro = (f"Dear Sales Team,\n\n{buyer[0]} is a printing and packaging company in {buyer[1]}. "
             f"We are reviewing suppliers for next quarter and would like your offer for the item below.\n\n")
    body = [f"- Product: {p}"]
    if spec:
        body.append(f"- Specification: {spec}")
    body.append(f"- Quantity: {qty}")
    if terms:
        body.append(f"- Terms: {terms}")
    if delivery:
        body.append(f"- Required delivery: {delivery}")
    if price:
        body.append(f"- Target price: {price}")
    return intro + "\n".join(body) + f"\n\nKind regards,\n{buyer[3]}\nPurchasing, {buyer[0]}"


RU_NAMES = {"ctp_plate": "термальные пластины CTP", "ps_plate": "позитивные PS пластины",
            "blanket": "офсетное полотно", "offset_ink": "офсетную краску",
            "fountain_solution": "увлажняющий раствор", "folding_carton": "складные картонные коробки",
            "corrugated_box": "гофроящики", "paper_bag": "бумажные пакеты",
            "label": "самоклеящиеся этикетки"}


def text_russian(product, spec_ru, qty, term, dest, delivery_ru, buyer):
    txt = f"Здравствуйте!\n\nКомпания {buyer[0]} просит предложить цену на {RU_NAMES[product]}"
    txt += f", {spec_ru}" if spec_ru else ""
    txt += f", количество {qty}."
    if term and dest:
        txt += f" Условия поставки {term} {DEST_RU[dest]}."
    elif term:
        txt += f" Условия поставки {term} Нинбо."
    elif dest:
        txt += f" Пункт доставки: {DEST_RU[dest]}."
    if delivery_ru:
        txt += f" Срок поставки {delivery_ru}."
    return txt + f"\n\nС уважением,\n{buyer[3]}"


FORMATS = [text_rfq_form, text_short_email, text_chat, text_formal]


# Build the regular inquiries; returns (inquiries, answer key) in the same order
def build_regular(n=60, n_russian=8, seed=2026):
    rng = random.Random(seed)
    inquiries, gold = [], []
    products = list(PRODUCTS)
    for k in range(n):
        inq_id = f"R{k + 1:02d}"
        product = products[k % len(products)]
        russian = k >= n - n_russian
        buyer = rng.choice(RU_BUYERS if russian else BUYERS)
        received = date(2026, 10, rng.randint(1, 20))

        spec_en, spec_ru, tokens = pick_spec(rng, product)
        if rng.random() < 0.12:                          # some buyers leave the spec out
            spec_en, spec_ru, tokens = None, None, []
        unit = PRODUCTS[product]["unit"]
        q = rng.choice(QTY_BELOW[product] if rng.random() < 0.2 else QTY_ABOVE[product])
        term, dest, terms_text = pick_terms(rng, buyer[2])
        delivery_en, delivery_ru, delivery_gold = (None, None, None)
        if rng.random() < 0.65:
            delivery_en, delivery_ru, delivery_gold = pick_delivery(rng, received)
        price_value, currency, price_text = None, None, None
        if rng.random() < 0.40 and not russian:
            lo, hi = PRICE_RANGE[product]
            price_value = round(rng.uniform(lo, hi), 3 if hi < 0.1 else 2)
            currency = "EUR" if buyer[1] in ("Germany", "Netherlands") else "USD"
            price_text = fmt_price(rng, price_value, currency, unit)

        name = PRODUCTS[product]["name"]
        if russian:
            text = text_russian(product, spec_ru, fmt_qty(rng, q, unit, russian=True), term, dest, delivery_ru, buyer)
            fmt_name, language = "email", "ru"
        else:
            fmt = FORMATS[k % len(FORMATS)]
            text = fmt(name, spec_en, fmt_qty(rng, q, unit), terms_text, delivery_en, price_text, buyer)
            fmt_name, language = fmt.__name__.replace("text_", ""), "en"

        inquiries.append({"id": inq_id, "difficulty": "regular", "language": language, "format": fmt_name,
                          "received": received.isoformat(), "text": text})
        items = [item(product, tokens, q, unit, price_value, currency)]
        gold.append(gold_record(inq_id, items, term, dest, delivery_gold))
    return inquiries, gold


# ---------- loading ----------

def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# Inquiries (optionally one split) and the answer key, keyed by id
def load_dataset(split=None):
    inquiries = read_jsonl(DATA / "inquiries.jsonl")
    gold = {g["id"]: g for g in read_jsonl(DATA / "gold.jsonl")}
    if split:
        inquiries = [q for q in inquiries if q["split"] == split]
    return inquiries, gold
