"""Score every finished run, compute the ROI numbers, and refresh charts and calculator data.

Usage:  python run_analysis.py
Reads runs/, data/ and prompts/. Writes results/*.csv, figures/*.png and docs/roi-data.js.
Methods without a run yet are listed as "pending" with an estimated cost only.
"""

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from llmroi import charts, roi  # noqa: E402
from llmroi.dataset import load_dataset  # noqa: E402
from llmroi.evaluate import RUNS, evaluate_method, load_prices  # noqa: E402
from llmroi.runner import build_prompt  # noqa: E402
from llmroi.scoring import FIELDS  # noqa: E402

RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
CALCULATOR_DATA = ROOT / "docs" / "roi-data.js"


def write_csv(path, rows, columns=None):
    columns = columns or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _round(row.get(k)) for k in columns})


def _round(value):
    return round(value, 4) if isinstance(value, float) else value


# What a correct answer looks like as model output, to estimate output tokens
def answer_text(gold):
    answer = json.loads(json.dumps({k: v for k, v in gold.items() if k != "id"}))
    for it in answer["items"]:
        it["spec"] = ", ".join(it["spec"]) or None
    return json.dumps(answer, ensure_ascii=False)


def per_field_by_group(metrics, inquiries):
    group = {q["id"]: q["difficulty"] for q in inquiries}
    rows = []
    for field in FIELDS:
        row = {"field": field}
        for g in ("all", "regular", "hard", "trap"):
            hits = [ok for scores in metrics["all_scores"] for s in scores
                    if g == "all" or group[s["id"]] == g
                    for f, ok in s["checks"] if f == field]
            row[g] = sum(hits) / len(hits) if hits else None
        rows.append(row)
    return rows


def main():
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    inquiries, gold = load_dataset("test")
    prices = load_prices()
    inp = roi.load_inputs()

    # Token estimate for methods that have not been run yet. Output is set to twice the length of a
    # correct answer, to leave room for spacing and longer reasons (real counts replace this after a run).
    tokens_in = statistics.mean(roi.estimate_tokens(build_prompt(q)) for q in inquiries)
    tokens_out = 2 * statistics.mean(roi.estimate_tokens(answer_text(gold[q["id"]])) for q in inquiries)

    # 1) Score every method that has runs; list the rest as pending
    folders = sorted(p.name for p in RUNS.iterdir() if p.is_dir()) if RUNS.exists() else []
    names = list(prices) + [f for f in folders if f not in prices]
    summary, measured = [], {}
    for method in names:
        price = prices.get(method, {})
        m = evaluate_method(RUNS / method, inquiries, gold, prices) if method in folders else None
        estimate = None
        if price:
            estimate = 1000 * (tokens_in * float(price["input_usd_per_mtok"])
                               + tokens_out * float(price["output_usd_per_mtok"])) / 1e6
        cost = m["cost_per_1000_usd"] if m and m["cost_per_1000_usd"] is not None else estimate
        row = {"method": method, "name": price.get("model", method), "provider": price.get("provider", ""),
               "status": "measured" if m else "pending",
               "cost_per_1000_usd": cost,
               "cost_basis": "measured" if m and method != "rules" else ("none" if method == "rules" else "estimated"),
               "breakeven_error_rate": roi.breakeven_error_rate(inp, (cost or 0) / 1000)}
        if m:
            measured[method] = m
            row.update({k: v for k, v in m.items() if not isinstance(v, (dict, list))})
            month = roi.monthly(inp, m["critical_error_rate"], (cost or 0) / 1000)
            row["net_per_month_usd"] = month["net_month"]
            row["payback_months"] = month["payback_months"]
        summary.append(row)

    columns = ["method", "name", "provider", "status", "cost_per_1000_usd", "cost_basis", "breakeven_error_rate",
               "critical_error_rate", "field_accuracy", "fabrication_rate", "invented_items_per_100",
               "json_fail_rate", "priority_accuracy", "missed_high_rate", "consistency", "runs",
               "latency_median_s", "latency_p90_s", "net_per_month_usd", "payback_months",
               "critical_error_rate_regular", "critical_error_rate_hard", "critical_error_rate_trap"]
    write_csv(RESULTS / "method_summary.csv", summary, columns)

    # 2) Per-field accuracy, confusion matrices and the rules' mistakes
    field_rows, confusion_rows = [], []
    for method, m in measured.items():
        for r in per_field_by_group(m, inquiries):
            field_rows.append({"method": method, **r})
        for g_level, preds in m["confusion"].items():
            for p_level, count in preds.items():
                confusion_rows.append({"method": method, "gold": g_level, "predicted": p_level, "count": count})
    write_csv(RESULTS / "field_accuracy.csv", field_rows)
    write_csv(RESULTS / "priority_confusion.csv", confusion_rows)

    group = {q["id"]: q["difficulty"] for q in inquiries}
    rules = measured["rules"]
    mistakes = [{"id": s["id"], "difficulty": group[s["id"]], "critical_error": s["critical_error"],
                 "wrong_fields": " ".join(f for f, ok in s["checks"] if not ok), "invented_items": s["extra_items"]}
                for s in rules["all_scores"][0] if s["critical_error"] or not all(ok for _, ok in s["checks"])]
    write_csv(RESULTS / "rules_mistakes.csv", mistakes)

    # 3) ROI: break-even curve, sensitivity, headline numbers
    llms = [r for r in summary if r["method"] != "rules" and r["cost_per_1000_usd"] is not None]
    cheapest = min(llms, key=lambda r: r["cost_per_1000_usd"])
    priciest = max(llms, key=lambda r: r["cost_per_1000_usd"])
    rates = [i / 200 for i in range(0, 81)]                  # 0% to 40%
    curve_rows, curves = [], []
    for r in (cheapest, priciest):
        ys = [roi.monthly(inp, e, r["cost_per_1000_usd"] / 1000)["net_month"] for e in rates]
        curves.append((f"{r['name']} (${r['cost_per_1000_usd']:.2f} per 1,000)", rates, ys))
        curve_rows += [{"method": r["method"], "critical_error_rate": e, "net_per_month_usd": y}
                       for e, y in zip(rates, ys)]
    write_csv(RESULTS / "breakeven_curve.csv", curve_rows)

    mid_cost = statistics.median(r["cost_per_1000_usd"] for r in llms) / 1000
    sens = roi.sensitivity(mid_cost)
    lo_be = roi.breakeven_error_rate(inp, cheapest["cost_per_1000_usd"] / 1000)
    hi_be = roi.breakeven_error_rate(inp, priciest["cost_per_1000_usd"] / 1000)
    sens.append({"input": "model_price", "low_value": cheapest["cost_per_1000_usd"],
                 "high_value": priciest["cost_per_1000_usd"], "breakeven_at_low": lo_be,
                 "breakeven_at_high": hi_be, "swing": abs(hi_be - lo_be)})
    sens.sort(key=lambda r: r["swing"], reverse=True)
    write_csv(RESULTS / "sensitivity.csv", sens)

    base_be = roi.breakeven_error_rate(inp, mid_cost)
    unit0 = roi.per_inquiry(inp, 0.0, 0.0)
    rules_month = roi.monthly(inp, rules["critical_error_rate"], 0.0)
    headline = {
        "hourly_cost_usd": roi.hourly_cost_usd(inp),
        "manual_cost_per_1000_usd": 1000 * unit0["manual_cost"],
        "labor_saved_per_1000_usd": 1000 * unit0["labor_saved"],
        "breakeven_error_rate_median_model": base_be,
        "breakeven_error_rate_cheapest": lo_be,
        "breakeven_error_rate_priciest": hi_be,
        "cheapest_model": cheapest["name"], "cheapest_cost_per_1000_usd": cheapest["cost_per_1000_usd"],
        "priciest_model": priciest["name"], "priciest_cost_per_1000_usd": priciest["cost_per_1000_usd"],
        "priciest_share_of_labor_saved": priciest["cost_per_1000_usd"] / (1000 * unit0["labor_saved"]),
        "rules_critical_error_rate": rules["critical_error_rate"],
        "rules_field_accuracy": rules["field_accuracy"],
        "rules_net_per_month_usd": rules_month["net_month"],
        # What one point of critical error rate is worth per month, vs. the price gap between models
        "value_of_one_point_per_month_usd": inp["monthly_volume"] * 0.01 * (
            roi.per_inquiry(inp, 0.0, 0.0)["net"] - roi.per_inquiry(inp, 1.0, 0.0)["net"]),
        "price_gap_priciest_vs_cheapest_per_month_usd": inp["monthly_volume"] * (
            priciest["cost_per_1000_usd"] - cheapest["cost_per_1000_usd"]) / 1000,
        "cost_to_test_all_models_3_runs_usd": 3 * len(inquiries) * sum(r["cost_per_1000_usd"] for r in llms) / 1000,
        "estimated_input_tokens": tokens_in, "estimated_output_tokens": tokens_out,
        "test_inquiries": len(inquiries),
    }
    write_csv(RESULTS / "headline.csv", [{"metric": k, "value": v} for k, v in headline.items()])

    # 4) Charts
    charts.use_style()
    charts.plot_cost_vs_labor([{"name": r["name"], "cost_per_1000": r["cost_per_1000_usd"]} for r in llms],
                              headline["labor_saved_per_1000_usd"], headline["manual_cost_per_1000_usd"],
                              FIGURES / "1_cost_vs_labor.png")
    charts.plot_breakeven(curves, (rules["critical_error_rate"], rules_month["net_month"]), base_be,
                          inp["monthly_volume"], FIGURES / "2_breakeven.png")
    rules_fields = [r for r in per_field_by_group(rules, inquiries)]
    trap_scores = [s for s in rules["all_scores"][0] if group[s["id"]] == "trap"]
    traps_caught = sum(s["pred_priority"] == "low" and s["extra_items"] == 0 for s in trap_scores)
    charts.plot_rules_by_field(rules_fields, {"regular": rules["critical_error_rate_regular"],
                                              "hard": rules["critical_error_rate_hard"]},
                               traps_caught, len(trap_scores), FIGURES / "3_rules_by_field.png")
    charts.plot_sensitivity(sens, base_be, FIGURES / "4_sensitivity.png")
    llm_measured = [r for r in summary if r["status"] == "measured" and r["method"] != "rules"]
    if llm_measured:                                   # only after at least one LLM has been run
        points = [{"method": r["method"], "name": r["name"], "cost_per_1000": r["cost_per_1000_usd"] or 0,
                   "critical_error_rate": r["critical_error_rate"]}
                  for r in summary if r["status"] == "measured"]
        charts.plot_measured(points, base_be, FIGURES / "5_measured.png")

    # 5) Data for the interactive calculator (docs/index.html)
    calculator = {
        "checked": "2026-10-23",
        "inputs": roi.load_input_table(),
        "methods": [{"method": r["method"], "name": r["name"], "provider": r["provider"], "status": r["status"],
                     "cost_per_1000": r["cost_per_1000_usd"], "cost_basis": r["cost_basis"],
                     "critical_error_rate": r.get("critical_error_rate"),
                     "field_accuracy": r.get("field_accuracy")} for r in summary],
        "headline": headline,
    }
    CALCULATOR_DATA.write_text("// Generated by run_analysis.py. Do not edit by hand.\nwindow.ROI_DATA = "
                               + json.dumps(calculator, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    print(f"Scored {len(measured)} method(s) on {len(inquiries)} test inquiries: {', '.join(measured)}")
    print(f"Break-even critical error rate: {base_be:.1%} (model price range moves it "
          f"{min(lo_be, hi_be):.1%} to {max(lo_be, hi_be):.1%})")
    print(f"Rules baseline: {rules['critical_error_rate']:.1%} critical errors, "
          f"{rules_month['net_month']:,.0f} USD per month")


if __name__ == "__main__":
    main()
