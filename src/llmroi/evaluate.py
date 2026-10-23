"""Turn per-inquiry scores into the metrics a manager would compare across methods."""

import csv
import json
import statistics
from pathlib import Path

from .scoring import CRITICAL_FIELDS, FIELDS, PRIORITIES, load_weights, score_inquiry

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"


def load_prices():
    with open(ROOT / "data" / "pricing.csv", encoding="utf-8") as f:
        return {row["method"]: row for row in csv.DictReader(f)}


# Every finished run file for one method folder, e.g. runs/anthropic__claude-haiku-5-5/run1.jsonl
def load_runs(method_dir):
    runs = []
    for path in sorted(method_dir.glob("run*.jsonl")):
        with open(path, encoding="utf-8") as f:
            runs.append({r["id"]: r for r in map(json.loads, f) if r.get("id") and not r.get("error")})
    return runs


def rate(part, whole):
    return part / whole if whole else None


# Metrics for one run over a set of inquiries
def summarize_run(scores):
    checks = [c for s in scores for c in s["checks"]]
    out = {
        "n": len(scores),
        "field_accuracy": rate(sum(ok for _, ok in checks), len(checks)),
        "critical_error_rate": rate(sum(s["critical_error"] for s in scores), len(scores)),
        "weighted_error": statistics.mean(s["weighted_error"] for s in scores),
        "fabrication_rate": rate(sum(s["invented"] for s in scores), sum(s["chances"] for s in scores)),
        "invented_items_per_100": 100 * sum(s["extra_items"] for s in scores) / len(scores),
        "json_fail_rate": rate(sum(not s["json_ok"] for s in scores), len(scores)),
        "priority_accuracy": rate(sum(s["gold_priority"] == s["pred_priority"] for s in scores), len(scores)),
        "missed_high_rate": rate(sum(s["missed_high"] for s in scores),
                                 sum(s["gold_priority"] == "high" for s in scores)),
    }
    for field in FIELDS:
        hits = [ok for s in scores for f, ok in s["checks"] if f == field]
        out[f"acc_{field}"] = rate(sum(hits), len(hits))
    return out


def confusion(scores):
    table = {g: {p: 0 for p in PRIORITIES + ["invalid"]} for g in PRIORITIES}
    for s in scores:
        table[s["gold_priority"]][s["pred_priority"]] += 1
    return table


# Score all runs of one method; average the metrics across runs and add cost, speed, consistency
def evaluate_method(method_dir, inquiries, gold, prices):
    weights = load_weights()
    runs = load_runs(method_dir)
    ids = [q["id"] for q in inquiries]
    difficulty = {q["id"]: q["difficulty"] for q in inquiries}
    runs = [r for r in runs if all(i in r for i in ids)]          # only complete runs count
    if not runs:
        return None

    per_run, all_scores = [], []
    for run in runs:
        scores = [score_inquiry(gold[i], run[i].get("output"), weights) for i in ids]
        all_scores.append(scores)
        per_run.append(summarize_run(scores))
    metrics = {k: _mean([m[k] for m in per_run]) for k in per_run[0]}

    # Same metrics by difficulty group (averaged across runs)
    for group in ("regular", "hard", "trap"):
        group_runs = [summarize_run([s for s in scores if difficulty[s["id"]] == group]) for scores in all_scores]
        metrics[f"field_accuracy_{group}"] = _mean([g["field_accuracy"] for g in group_runs])
        metrics[f"critical_error_rate_{group}"] = _mean([g["critical_error_rate"] for g in group_runs])

    # Consistency: share of inquiries with identical output in every run
    metrics["runs"] = len(runs)
    metrics["consistency"] = (_mean([len({scores[k]["normalized"] for scores in all_scores}) == 1
                                     for k in range(len(ids))]) if len(runs) > 1 else None)

    # Cost and speed come from what the API reported
    records = [run[i] for run in runs for i in ids]
    price = prices.get(method_dir.name)
    if price:
        cost = [(r.get("input_tokens") or 0) * float(price["input_usd_per_mtok"]) / 1e6
                + (r.get("output_tokens") or 0) * float(price["output_usd_per_mtok"]) / 1e6 for r in records]
        metrics["cost_per_1000_usd"] = 1000 * statistics.mean(cost)
    else:
        metrics["cost_per_1000_usd"] = None          # add a row to data/pricing.csv for this method
    latencies = sorted(r["latency_s"] for r in records if r.get("latency_s") is not None)
    metrics["latency_median_s"] = statistics.median(latencies) if latencies else None
    metrics["latency_p90_s"] = latencies[int(0.9 * (len(latencies) - 1))] if latencies else None
    metrics["confusion"] = confusion(all_scores[0])
    metrics["all_scores"] = all_scores
    return metrics


def _mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


__all__ = ["evaluate_method", "load_prices", "RUNS", "CRITICAL_FIELDS"]
