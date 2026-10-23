# Which LLM Should an Export Sales Team Use, and Is It Worth It?

**English** · [中文](README.zh-CN.md) · [Interactive ROI calculator](https://hql7-luo.github.io/llm-selection-roi/) · [Methodology](docs/methodology.md)

A small Chinese exporter of printing consumables and packaging gets about 500 inquiries a month by email, Alibaba and chat. Right now a salesperson reads each one, types the details into a tracker and decides which to answer first. The idea is to let an LLM draft the tracker entry (product, spec, quantity, target price, Incoterm, destination, delivery date, missing information, priority) and have the salesperson check it.

Two questions: **which model should the team use, and is it worth paying for?** To answer them I used 100 labeled inquiries, a scoring script, a no-AI baseline, eight models tested on the same inquiries (three Claude, two GPT, two DeepSeek, one Kimi), list prices, public leaderboard scores and a simple ROI model. The company and every inquiry are fictional.

## The answer

**Pick the cheapest model that does well on your own inquiries. On this test set, that was Claude Haiku 5.5.** With the base-case assumptions, AI drafts pay off as long as fewer than about **17% of inquiries** have a critical error. All eight models were under that line, though Kimi K2.7 Code (11.88%) was closer than the rest. Simple rules without AI were not.

- **Most models made very few mistakes, but not all of them.** Each model answered the same 80 inquiries twice. Haiku, Opus and DeepSeek V4 Pro made no critical errors. Sonnet made 1 in 160 (0.63%), GPT-6.1 Sol and DeepSeek V4.1 Flash 2 in 160 (1.25%), GPT-6 Luna 11 (6.88%) and Kimi K2.7 Code 19 (11.88%). All of Sonnet's, Sol's and V4.1 Flash's errors were on one inquiry with a debatable answer (see below). The rules baseline had a critical error on 20% of inquiries, and on 55% of the hard ones.
- **DeepSeek did just as well, which matters for a Chinese team.** If the company would rather use a provider it can reach and pay in mainland China, DeepSeek V4 Pro (about $1.64 per 1,000 inquiries) made no errors, and V4.1 Flash ($0.42) only missed the debatable one. These two were tested inside WorkBuddy, so this is worth confirming through DeepSeek's own API first.
- **It pays back quickly.** At 500 inquiries a month, Haiku comes out about **$714 a month** ahead after API, review and mistake costs, and pays back a $2,000 setup in about **2.8 months**. DeepSeek V4 Pro is about the same ($713). Sol and V4.1 Flash: about $660 and 3.0 months. Luna: about $425 and 4.7 months. Kimi: about $215 and 9.3 months. Rules alone lose about $125 a month.
- **A higher price did not mean fewer mistakes.** Luna and Haiku have the same list price, but Luna made 11 critical errors and Haiku none. Kimi costs about 9 times as much as Haiku and made the most errors. Opus and Sol cost about 40 and 20 times as much as Haiku and did no better.
- **Mistakes cost far more than tokens.** API cost ranges from **$0.04 to $6.18 per 1,000 inquiries**, while an AI draft could save about **$728 of labor** per 1,000. Each point of critical error rate costs about **$42 a month**; the biggest price gap between models is about **$3 a month**.
- **Treat these scores as optimistic.** The inquiries are synthetic and were written with Claude's help, which may favor Claude. Public leaderboards measure general reasoning, not this task. Before choosing a model for real, test 50 to 100 real (anonymized) inquiries.

These are model estimates, not measured savings.

![Monthly net benefit against critical error rate](figures/2_breakeven.png)

## Model results

All models got the same instructions and the same 80 test inquiries. Numbers come from [`results/method_summary.csv`](results/method_summary.csv).

| Method | Tested how | API cost per 1,000 (est.) | Critical errors | Fields correct | Same output both runs | Same score both runs | Public index (AA) |
|---|---|---:|---:|---:|---:|---:|---:|
| Rules baseline (no AI) | run locally | $0 | **20.00%** | 93.01% | (1 run) | (1 run) | |
| Claude Haiku 5.5 | Claude subagent, 2 runs | $0.15 | **0.00%** | 100.00% | 95.00% | 100.00% | 43 |
| Claude Sonnet 5.5 | Claude subagent, 2 runs | $3.09 | **0.63%** | 99.70% | 95.00% | 97.50% | 56 |
| Claude Opus 5.5 | Claude subagent, 2 runs | $6.18 | **0.00%** | 100.00% | 95.00% | 100.00% | 58 |
| GPT-6.1 Sol | Codex, 2 runs, medium | $3.09 | **1.25%** | 99.55% | 100.00% | 100.00% | 48 |
| GPT-6 Luna | Codex, 2 runs, medium | $0.15 | **6.88%** | 97.84% | 78.75% | 82.50% | 30 |
| DeepSeek V4 Pro | WorkBuddy, 2 runs | $1.64 | **0.00%** | 100.00% | 90.00% | 100.00% | 36 |
| DeepSeek V4.1 Flash | WorkBuddy, 2 runs | $0.42 | **1.25%** | 99.48% | 93.75% | 98.75% | 45 |
| Kimi K2.7 Code | WorkBuddy, 2 runs | $1.35 | **11.88%** | 97.77% | 66.25% | 87.50% | 26 |
| Qwen3.7 Flash | not tested | $0.04 | | | | | not listed |
| Qwen3.5 Plus | not tested | $0.68 | | | | | not listed |

"Same output" means both runs gave the same answer (spec wording can differ). "Same score" means both runs got the same fields right and wrong. Being consistent is not the same as being right: Sol gave the same answers both times, including the same mistake. Kimi changed its answer on about a third of the inquiries between runs. Public index scores come from Artificial Analysis; the GPT rows use the medium reasoning setting they were tested at, and the Claude and DeepSeek rows use the highest setting listed, so they are not directly comparable.

![Measured critical error rate against cost](figures/5_measured.png)

**How the models were tested.** No API key was used. Each model got the 80 test inquiries as 4 batches of 20, with the same instructions as the API prompt, and answered each batch in a fresh session that saw only that one batch. Every model did this twice.

- Claude Haiku, Sonnet and Opus 5.5 ran as Claude subagents.
- GPT-6.1 Sol (the account's default) and GPT-6 Luna ran in fresh `codex exec` sessions outside this repository, at medium reasoning, in a read-only sandbox with web search off. All 16 batches came back in the right format on the first try; none were rerun or edited. Details are in `runs/codex__*/execution.json`.
- DeepSeek V4 Pro, DeepSeek V4.1 Flash and Kimi K2.7 Code ran in WorkBuddy (Tencent's AI agent app) with its built-in models. Each model got its own chat, with the model picked by hand in the app. A coordinating session in that chat pasted each batch into a fresh subagent with no file access. The app does not show which model actually answered, so this rests on the picker choice; every reply named the expected model. One Kimi batch was rerun once because the first reply had a duplicated JSON key. Details are in `runs/workbuddy__*/execution.json`.

Raw replies are kept in [`runs/`](runs). Since none of this went through an API, there are no token counts; costs are estimated from list prices, and actual Codex and WorkBuddy cost was not measured.

**Not tested yet:** Qwen, and the GPT and DeepSeek models through the API (`openai__` and `deepseek__` rows in the data files). The [API runner](#re-run-through-the-api) is ready for them.

**Where the models went wrong.**

- **One debatable inquiry (R55).** A Russian inquiry asks for "термальные пластины CTP" (thermal CTP plates) with no size or thickness. The answer key says there is no spec, because a plate cannot be quoted without size and thickness. Sonnet (once), Sol, Luna and DeepSeek V4.1 Flash (both runs each) and Kimi (once) wrote "thermal" as the spec, which is a fair reading of the prompt. The key was set before any model ran and was not changed. Counting R55 as correct, Sonnet, Sol and V4.1 Flash have no critical errors, Luna has 9 in 160 (5.6%) and Kimi 18 in 160 (11.25%).
- **Good leads ranked too low.** This was most of the other mistakes: 17 of Kimi's 19 and 7 of Luna's 11. Each time, Kimi marked the lead "medium" because the Incoterm, destination or delivery date was missing, but the rule only needs a spec, a quantity at or above the minimum order, and an Incoterm or a destination. Since priority follows a fixed rule, one fix worth testing is to work it out in code from the extracted fields.
- **The rest:** Luna got two delivery dates wrong, and Kimi once treated a sample request as not a real inquiry. Neither got a target price wrong.

## Key charts

**Cost.** Even the most expensive model costs under 1% of the labor it could save.

![API cost per 1,000 inquiries by model](figures/1_cost_vs_labor.png)

**Where rules break.** Rules read tidy forms well. On the test set they failed on quantities written in words, in cans or as "25k", prices per 1,000 pieces, relative dates ("end of next month"), an older offer quoted below the reply, and company names that contain a product word or a city ("Minsk Label House").

![Rules baseline accuracy by field](figures/3_rules_by_field.png)

**What moves the bar.** The review step, the cost of a mistake and the human error rate matter most. Model price matters least.

![Sensitivity of the break-even error rate](figures/4_sensitivity.png)

## How it works

```mermaid
flowchart LR
    A[100 fictional inquiries<br/>with answer key] --> B[Method<br/>rules or an LLM]
    B --> C[JSON draft for<br/>the tracker]
    C --> D[Scoring<br/>field by field]
    D --> E[Critical error rate,<br/>consistency, cost]
    E --> F[ROI model<br/>net benefit, break-even]
```

- **Dataset:** 60 regular inquiries (Alibaba RFQ forms, short emails, chat messages, 8 in Russian), 25 hard ones written by hand, 15 traps (spam, phishing, fee scams, products we do not sell). 20 were used to build the prompt and rules; 80 were kept aside for testing.
- **Critical error:** a wrong product, spec, quantity, target price or delivery date, an invented item, or a high-priority lead ranked lower. I also track field accuracy, weighted error, invented values, a priority confusion matrix, JSON failures and run-to-run consistency.
- **ROI per inquiry:** labor saved, minus API cost, minus the extra cost of mistakes compared with a person doing it by hand (people make mistakes too). Monthly maintenance is included; the one-time setup cost sets the payback period.

Details: [methodology](docs/methodology.md).

## Data

| Input | Value | Source (date) |
|---|---|---|
| Claude Haiku / Sonnet / Opus 5.5 | $0.10 / $2 / $4 input, $0.50 / $10 / $20 output per million tokens | Anthropic pricing page (Oct 23, 2026) |
| GPT-6.1 Sol / GPT-6 Luna | $2 / $0.10 input, $10 / $0.50 output per million tokens | OpenAI API pricing page, standard rate (Oct 23, 2026) |
| DeepSeek V4 Pro / V4.1 Flash | $1.32 / $0.30 input, $3.96 / $1.20 output per million tokens (peak; off-peak is half) | BenchLM price table citing DeepSeek's pricing page; secondary source |
| Kimi K2.7 Code | $0.95 input, $4.00 output per million tokens | eesel.ai article citing Moonshot's pricing page; secondary source |
| Qwen3.7 Flash, Qwen3.5 Plus | see [`data/pricing.csv`](data/pricing.csv) | BenchLM price table citing Alibaba Model Studio; secondary source |
| Public leaderboard scores | see [`data/public_benchmarks.csv`](data/public_benchmarks.csv) | Artificial Analysis (Oct 23, 2026) |
| Foreign-trade salesperson salary, Hangzhou | ¥8,672 a month | Liepin, 4,443 postings over the past year (checked Oct 23, 2026) |
| USD/CNY | 6.6781 | Oct 22, 2026 |
| Handling time, review time, catch rate, error cost, volume | see [`data/roi_inputs.csv`](data/roi_inputs.csv) | Assumptions, labeled as such, with low and high values |

All sources with links: [docs/data-sources.md](docs/data-sources.md).

## Run it

```bash
pip install -r requirements.txt
python build_dataset.py      # rebuilds data/ (same output every time)
python run_eval.py rules     # no-AI baseline, free
python run_analysis.py       # scores every run, writes results/, figures/ and docs/roi-data.js
pytest                       # checks data, scoring, rules, runner, ROI and calculator parity
```

### Test a model without an API key

Make the batches outside the repo, answer each one in a fresh agent session, then import the replies. For example, with Codex:

```bash
python batches.py make ~/llm-batches/gpt-6.1-sol/run1
codex exec --cd ~/llm-batches/gpt-6.1-sol/run1 --model gpt-6.1-sol \
  --sandbox read-only --skip-git-repo-check --ignore-user-config --ephemeral \
  -c model_reasoning_effort=medium -c web_search=disabled --json \
  --output-last-message ~/llm-batches/gpt-6.1-sol/run1/reply1.txt \
  'Read batch1.txt in this folder and follow the instructions inside it. Answer every message yourself by reading it. Do not write or run any code, scripts or regex, and do not search the web. Do not open, list or search any other file or folder. Your final reply must be only the MODEL line followed by the ```jsonl block, exactly as batch1.txt asks.'
# repeat for batch2 to batch4 (new session each time, change both numbers)
python batches.py import codex__gpt-6.1-sol run1 ~/llm-batches/gpt-6.1-sol/run1 "Codex, batch of 20"
python run_analysis.py
```

WorkBuddy works too: pick the model by hand in a new chat, and have that chat paste each batch into a fresh subagent (see `runs/workbuddy__*/execution.json`). Before importing, check that each reply has 20 lines starting with `{"id"`. Do a second pass in a `run2` folder for the consistency check. Keep the answering agent out of this repo so it cannot see `data/gold.jsonl`.

### Re-run through the API

To test a model the usual way (one inquiry per call, temperature 0, real token counts), set its key and run:

```bash
export DEEPSEEK_API_KEY=...             # or ANTHROPIC_API_KEY, OPENAI_API_KEY, DASHSCOPE_API_KEY
python run_eval.py deepseek:deepseek-flash --split dev --runs 1   # quick check on 20 inquiries
python run_eval.py deepseek:deepseek-flash --runs 3               # full run
python run_analysis.py
```

Testing all ten API models three times would cost about $4.03 at list prices (estimate). For a model not in [`data/pricing.csv`](data/pricing.csv), add a row first.

## Repository

```
data/          inquiries.jsonl, gold.jsonl (answer key), catalog, prices, public scores, ROI inputs, field weights
prompts/       extract_v1.txt (the instructions every model gets)
src/llmroi/    dataset and labels, rules baseline, API runner, batches, scoring, ROI model, charts
batches.py     make batch files for an agent and import its replies (no API key)
runs/          answers per method; runs/<method>/raw/ keeps the replies as received
results/       output tables (CSV)
figures/       charts used in this README
docs/          methodology, data sources, ROI calculator (index.html)
tests/         checks for data, scoring, rules, runner and ROI
```

## Limits

- **Synthetic data, written with Claude's help.** The inquiries are modeled on common printing-consumables export inquiries, but they are cleaner than a real inbox, and they may favor Claude. All scores are likely optimistic.
- **Small sample.** 80 test inquiries, two runs each. Running the same inquiry twice is not two independent examples, and zero errors here does not mean zero errors in real use.
- **No API runs.** All models answered 20 inquiries at a time inside an agent (Claude subagents, Codex at medium reasoning, or WorkBuddy subagents), each with its own system prompt and settings. API results may differ, and costs are estimates.
- **The WorkBuddy models could not be verified.** The model was picked in the app, and the app's reasoning setting was left at its default. DeepSeek also said in September that V4 Pro API requests would go to V4.1 Flash, while its pricing page still lists V4 Pro. The two did answer differently here, but I cannot confirm which weights WorkBuddy used.
- **Not every vendor is covered.** Qwen is not tested yet. Kimi's K2 models take no new sign-ups after October 31, 2026. For a Chinese exporter, mainland access, data privacy and payment also matter; they are not scored here.
- **The rules baseline is probably optimistic too.** The same author wrote the rules and the data.
- **Labor and error-cost numbers are assumptions.** The most important ones (catch rate, cost of an escaped error, manual error rate) should be measured: time 10 inquiries by hand, and count how many AI errors reviewers catch in the first month.
- **Prices change.** DeepSeek, Kimi and Qwen prices come from secondary sources; check the official pages before reuse.

## About

Independent project by Haoqi Luo (University of Washington, Foster School of Business). I chose the business question from my export sales experience and set the scope. Claude helped a lot with the research, data, code and writing, Codex ran the GPT tests and helped update the docs, and WorkBuddy ran the DeepSeek and Kimi tests. Not financial advice.
