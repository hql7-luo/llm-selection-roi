"""Checks for the dataset, scoring, rules baseline, ROI model and calculator.

Run with:  pytest
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from llmroi import batch, roi, rules, runner  # noqa: E402
from llmroi.catalog import (normalize_currency, normalize_delivery, normalize_destination,  # noqa: E402
                            normalize_incoterm, normalize_product, normalize_spec, normalize_unit)
from llmroi.dataset import build_regular, load_dataset, read_jsonl  # noqa: E402
from llmroi.labels import missing_info, priority  # noqa: E402
from llmroi.scoring import load_weights, score_inquiry  # noqa: E402


# ---------- dataset ----------

def test_dataset_size_and_split():
    inquiries, gold = load_dataset()
    assert len(inquiries) == 100 and len(gold) == 100
    assert len({q["id"] for q in inquiries}) == 100
    counts = {}
    for q in inquiries:
        counts[(q["difficulty"], q["split"])] = counts.get((q["difficulty"], q["split"]), 0) + 1
    assert counts == {("regular", "dev"): 12, ("regular", "test"): 48, ("hard", "dev"): 5,
                      ("hard", "test"): 20, ("trap", "dev"): 3, ("trap", "test"): 12}


def test_committed_data_matches_the_builder():
    regular, regular_gold = build_regular()
    on_disk = {q["id"]: q for q in read_jsonl(ROOT / "data" / "inquiries.jsonl")}
    gold_disk = {g["id"]: g for g in read_jsonl(ROOT / "data" / "gold.jsonl")}
    for q, g in zip(regular, regular_gold):
        assert on_disk[q["id"]]["text"] == q["text"]
        assert gold_disk[g["id"]] == g


def test_answer_key_follows_the_written_rubric():
    _, gold = load_dataset()
    for g in gold.values():
        assert g["priority"] == priority(g["items"], g["incoterm"], g["destination"])
        assert g["missing_info"] == missing_info(g["items"], g["incoterm"], g["destination"], g["delivery"])


# ---------- normalizing and scoring ----------

def test_normalizers():
    assert normalize_unit("m²") == "sqm" and normalize_unit("шт") == "pcs" and normalize_unit("liters") == "L"
    assert normalize_destination("Санкт-Петербург") == "Saint Petersburg"
    assert normalize_destination("st. petersburg port") == "Saint Petersburg"
    assert normalize_delivery("6 weeks") == "42 days" and normalize_delivery("asap") is None
    assert "0.3mm" in normalize_spec("1030 × 790 mm, 0.30 mm") and "1.95mm" in normalize_spec("1060х860х1,95 мм")
    assert normalize_incoterm("CIF Novorossiysk") == "CIF" and normalize_incoterm("c.i.f.") == "CIF"
    assert normalize_incoterm("Delivered") is None
    assert normalize_destination("Saint-Petersburg") == "Saint Petersburg"
    assert normalize_product("CTP plate") == "ctp_plate" and normalize_currency("$") == "USD"


# A correct answer in the format the prompt asks for (spec as text)
def gold_answer(g):
    answer = json.loads(json.dumps(g))
    for it in answer["items"]:
        it["spec"] = ", ".join(it["spec"]) or None
    return answer


def answer_from_gold(g):
    return "```json\n" + json.dumps(gold_answer(g)) + "\n```"     # wrapped in a code fence on purpose


def test_a_perfect_answer_scores_100_percent():
    _, gold = load_dataset()
    weights = load_weights()
    for g in gold.values():
        s = score_inquiry(g, answer_from_gold(g), weights)
        assert all(ok for _, ok in s["checks"]), g["id"]
        assert not s["critical_error"] and s["invented"] == 0 and s["weighted_error"] == 0


def test_bad_output_counts_as_errors():
    _, gold = load_dataset()
    weights = load_weights()
    s = score_inquiry(gold["H03"], "Sorry, I cannot help with that.", weights)
    assert not s["json_ok"] and s["critical_error"] and not any(ok for _, ok in s["checks"])

    # Inventing a target price where the email gives none is flagged
    answer = gold_answer(gold["H03"])
    answer["items"][0]["target_price"] = {"value": 40, "currency": "USD"}
    s = score_inquiry(gold["H03"], json.dumps(answer), weights)
    assert s["invented"] == 1 and s["critical_error"]


# ---------- rules baseline ----------

def test_rules_run_file_matches_the_code():
    inquiries, _ = load_dataset()
    saved = {r["id"]: r["output"] for r in read_jsonl(ROOT / "runs" / "rules" / "run1.jsonl")}
    for q in inquiries:
        assert rules.extract(q["text"], q["received"]) == saved[q["id"]], q["id"]


def test_rules_catch_spam():
    out = json.loads(rules.extract("Our SEO team can bring you to page 1 of Google. USD 199 per month.", "2026-10-01"))
    assert out["priority"] == "low" and out["items"] == []


# ---------- subagent runs ----------

CLAUDE_RUNS = ["anthropic__claude-haiku-5-5", "anthropic__claude-sonnet-5-5", "anthropic__claude-opus-5-5"]
AGENT_RUNS = CLAUDE_RUNS + ["codex__gpt-6.1-sol", "codex__gpt-6-luna", "workbuddy__deepseek-v4-pro",
                            "workbuddy__deepseek-flash", "workbuddy__kimi-2-7"]


def test_batch_prompt_has_no_answers():
    inquiries, gold = load_dataset("test")
    text = batch.batch_prompt(inquiries[:20])
    assert all(q["id"] in text for q in inquiries[:20])
    assert "priority_reason\": \"Complete request" not in text and "gold" not in text.lower()


def test_parse_reply_reads_jsonl_lines():
    reply = 'MODEL: test\n```jsonl\n{"id": "R01", "answer": {"items": [], "priority": "low"}}\nnot json\n```'
    answers = batch.parse_reply(reply)
    assert list(answers) == ["R01"] and json.loads(answers["R01"])["priority"] == "low"


# Every agent run file (Claude subagents, Codex, WorkBuddy) must be exactly what its saved raw replies give
@pytest.mark.parametrize("method", AGENT_RUNS)
def test_subagent_run_files_match_raw_replies(method, tmp_path):
    inquiries, _ = load_dataset("test")
    ids = [q["id"] for q in inquiries]
    folder = ROOT / "runs" / method
    copy = tmp_path / method
    shutil.copytree(folder / "raw", copy / "raw")
    via = read_jsonl(folder / "run1.jsonl")[0]["via"]
    batch.import_raw(copy, ids, via)
    for run in ("run1.jsonl", "run2.jsonl"):
        assert (copy / run).read_text(encoding="utf-8") == (folder / run).read_text(encoding="utf-8")
        records = read_jsonl(folder / run)
        assert [r["id"] for r in records] == ids and all(r["output"] for r in records)


def test_agent_import_flow(tmp_path, monkeypatch):
    import batches as cli
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "runs").mkdir()
    cli.make(tmp_path / "out")
    for k in range(1, 5):
        raw = ROOT / "runs" / CLAUDE_RUNS[0] / "raw" / "run1" / f"batch{k}.txt"
        shutil.copy(raw, tmp_path / "out" / f"reply{k}.txt")
    cli.import_replies("codex__demo", "run1", tmp_path / "out", "Codex, batch of 20")
    records = read_jsonl(tmp_path / "runs" / "codex__demo" / "run1.jsonl")
    assert len(records) == 80 and all(r["output"] for r in records) and records[0]["via"] == "Codex, batch of 20"


# ---------- runner (API calls are faked) ----------

class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code, self.text = body, status, json.dumps(body)

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_runner_reads_both_api_styles(monkeypatch):
    inquiry = load_dataset("dev")[0][0]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")

    def fake_post(url, headers, json, timeout):
        assert inquiry["text"] in json["messages"][0]["content"]
        if "anthropic" in url:
            return FakeResponse({"content": [{"type": "text", "text": "{}"}], "usage": {"input_tokens": 900, "output_tokens": 120}})
        return FakeResponse({"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 880, "completion_tokens": 110}})

    monkeypatch.setattr(runner.requests, "post", fake_post)
    a = runner.call_once("anthropic:claude-haiku-5-5", inquiry, None, 500)
    d = runner.call_once("deepseek:deepseek-flash", inquiry, None, 500)
    assert a["error"] is None and a["input_tokens"] == 900 and a["output_tokens"] == 120
    assert d["error"] is None and d["input_tokens"] == 880 and d["output_tokens"] == 110


def test_runner_reports_a_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    record = runner.call_once("openai:gpt-6-luna", load_dataset("dev")[0][0], None, 500)
    assert "OPENAI_API_KEY" in record["error"]


# ---------- ROI ----------

def test_cost_scenarios_count_each_provider_model_once():
    import run_analysis as analysis

    summary = [
        {"method": "rules", "provider": "none", "cost_per_1000_usd": 0},
        {"method": "openai__sample", "provider": "openai", "cost_per_1000_usd": 2},
        {"method": "codex__sample", "provider": "openai", "cost_per_1000_usd": 2},
        {"method": "other__sample", "provider": "other", "cost_per_1000_usd": 3},
        {"method": "custom__one", "provider": "custom", "cost_per_1000_usd": 4},
        {"method": "custom__two", "provider": "custom", "cost_per_1000_usd": 5},
        {"method": "unknown", "provider": "unknown", "cost_per_1000_usd": None},
    ]
    prices = {method: {"provider": provider, "model_id": "sample"}
              for method, provider in [("openai__sample", "openai"),
                                       ("codex__sample", "openai"),
                                       ("other__sample", "other")]}
    original = [dict(row) for row in summary]

    scenarios = analysis.cost_scenarios(summary, prices)

    assert [row["method"] for row in scenarios] == ["openai__sample", "other__sample",
                                                   "custom__one", "custom__two"]
    assert sum(row["cost_per_1000_usd"] for row in scenarios) == 14
    assert summary == original


def test_breakeven_rate_gives_zero_net_benefit():
    inp = roi.load_inputs()
    for api_cost in (0.0, 0.0002, 0.01):
        e = roi.breakeven_error_rate(inp, api_cost)
        assert abs(roi.monthly(inp, e, api_cost)["net_month"]) < 1e-6


def test_hourly_cost_from_sourced_inputs():
    assert roi.hourly_cost_usd(roi.load_inputs()) == pytest.approx(9.70, abs=0.01)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_calculator_matches_python():
    inp = roi.load_inputs()
    cases = [(0.0, 0.0), (0.05, 0.0002), (0.2125, 0.0), (0.3, 0.0062)]
    script = (f"const M = require({json.dumps(str(ROOT / 'docs' / 'roi.js'))});"
              f"const inp = {json.dumps(inp)};"
              f"const cases = {json.dumps(cases)};"
              "console.log(JSON.stringify(cases.map(([e, a]) => [M.monthly(inp, e, a).net_month, M.breakevenErrorRate(inp, a)])));")
    js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    for (e, a), (net, be) in zip(cases, js):
        assert net == pytest.approx(roi.monthly(inp, e, a)["net_month"], abs=1e-9)
        assert be == pytest.approx(roi.breakeven_error_rate(inp, a), abs=1e-12)


def test_calculator_data_is_up_to_date():
    text = (ROOT / "docs" / "roi-data.js").read_text(encoding="utf-8")
    data = json.loads(text.split("window.ROI_DATA = ", 1)[1].rstrip().rstrip(";"))
    with open(ROOT / "results" / "method_summary.csv", encoding="utf-8") as f:
        import csv
        summary = {r["method"]: r for r in csv.DictReader(f)}
    assert {m["method"] for m in data["methods"]} == set(summary)
    for m in data["methods"]:
        assert m["status"] == summary[m["method"]]["status"]
        assert m["cost_per_1000"] == pytest.approx(float(summary[m["method"]]["cost_per_1000_usd"]), abs=1e-3)


def test_duplicate_inquiry_ids_are_rejected_in_run_files(tmp_path):
    from llmroi.evaluate import load_runs

    record = {"id": "R01", "output": {"items": []}}
    (tmp_path / "run1.jsonl").write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n")
    with pytest.raises(ValueError, match="Duplicate inquiry ID"):
        load_runs(tmp_path)
