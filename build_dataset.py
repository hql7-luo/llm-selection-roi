"""Build the 100-inquiry dataset and its answer key.

Usage:  python build_dataset.py
Writes data/inquiries.jsonl, data/gold.jsonl and data/catalog.csv. The output is the same every
time (fixed random seed), so the committed files can be checked against this script.
"""

import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from llmroi.catalog import PRODUCTS  # noqa: E402
from llmroi.dataset import DATA, build_regular, write_jsonl  # noqa: E402
from llmroi.handwritten import build_handwritten  # noqa: E402

DEV_PER_GROUP = {"regular": 12, "hard": 5, "trap": 3}   # 20 dev, 80 test


def main():
    regular, regular_gold = build_regular()
    hand, hand_gold = build_handwritten()
    inquiries = regular + hand
    gold = regular_gold + hand_gold

    # Stratified split: the same share of regular, hard and trap cases in dev and test
    rng = random.Random(7)
    dev_ids = set()
    for group, n in DEV_PER_GROUP.items():
        ids = [q["id"] for q in inquiries if q["difficulty"] == group]
        dev_ids.update(rng.sample(ids, n))
    for q in inquiries:
        q["split"] = "dev" if q["id"] in dev_ids else "test"

    # Put the columns in a readable order
    order = ["id", "split", "difficulty", "language", "format", "received", "text"]
    inquiries = [{k: q[k] for k in order} for q in inquiries]

    DATA.mkdir(exist_ok=True)
    write_jsonl(DATA / "inquiries.jsonl", inquiries)
    write_jsonl(DATA / "gold.jsonl", gold)
    with open(DATA / "catalog.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_key", "name", "unit", "moq"])
        for key, p in PRODUCTS.items():
            writer.writerow([key, p["name"], p["unit"], p["moq"]])

    n_dev = sum(q["split"] == "dev" for q in inquiries)
    print(f"{len(inquiries)} inquiries ({n_dev} dev, {len(inquiries) - n_dev} test) written to data/")


if __name__ == "__main__":
    main()
