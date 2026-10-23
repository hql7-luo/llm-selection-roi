# Methodology

## 1. The decision

A fictional exporter of printing consumables and packaging (CTP and PS plates, blankets, ink, fountain solution, folding cartons, corrugated boxes, paper bags, labels) sells to buyers in Russia, Central Asia, Europe, the Gulf, East Africa and Brazil. A small sales team handles about 500 inquiries a month. For each one, a salesperson reads the message, types the details into a tracker and decides how fast to answer.

The proposal is "AI draft + human review": an LLM reads the message and fills in the tracker fields; the salesperson checks the draft instead of typing it. The manager needs to decide **which model to use, and whether to do it at all**.

## 2. Dataset

Built by [`build_dataset.py`](../build_dataset.py); same output every time.

| Group | Count | What it contains |
|---|---:|---|
| Regular | 60 | Template-based: Alibaba RFQ forms, short emails, chat messages, formal emails, 8 in Russian. About 20% are below MOQ and about 12% leave out the spec. |
| Hard | 25 | Written by hand: corrections, last year's quantity next to this year's, two products in one email, quantities in words or "50 cans of 20 L", "25k", prices per 1,000 pieces, comma decimals, relative dates ("end of next month"), a quoted older offer, a reply deadline that is not a delivery date, a city in the company name, Russian and mixed Russian/English. |
| Trap | 15 | Not real purchase inquiries: SEO and forwarder pitches, phishing links, a "vendor registration fee", a job application, generic "send your price list", products the company does not sell. |

**Split.** 20 inquiries (12 regular, 5 hard, 3 trap) are the dev set, used to write the prompt and the rules. The other 80 are the test set; every reported number comes from these 80.

**Answer key.** For each inquiry the label records what the message actually asks for: items (product key, spec tokens, quantity in the catalog unit, target price per unit), Incoterm, destination, delivery. Two fields are then derived by fixed rules in [`labels.py`](../src/llmroi/labels.py), so they cannot drift:

- **missing_info:** which of spec, quantity, destination, Incoterm and delivery are absent.
- **priority:** *low* if there is no catalog item (spam, phishing, fee requests, other products, generic requests); *high* if every item has spec and quantity at or above MOQ and there is an Incoterm or destination; *medium* otherwise.

Labeling decisions worth knowing:

- The quantity is the order requested **now** (not past orders, yearly volume or our earlier offer). Pallets or containers with no unit count give no quantity.
- The destination is the buyer's city or port. The Chinese port after FOB, FCA or EXW is not a destination.
- "Price including freight and insurance to Jebel Ali" is labeled CIF.
- "ASAP" is not a delivery date.

## 3. Methods

**Rules baseline** ([`rules.py`](../src/llmroi/rules.py)): keyword lists for products and spam, regular expressions for sizes, quantities, prices, Incoterms, ports and dates, and the same priority rubric. It needs no API and is the "what can we do for free" option.

**LLMs through the API** ([`runner.py`](../src/llmroi/runner.py)): one prompt for every model ([`prompts/extract_v1.txt`](../prompts/extract_v1.txt)) with the catalog, field rules, priority rubric and the JSON format; one inquiry per call; temperature 0; three runs per model. The runner supports the Anthropic API and any OpenAI-compatible API (OpenAI, DeepSeek, Qwen). It is ready but was not used for the published results, because no API key was used.

**Claude models through subagents** ([`batch.py`](../src/llmroi/batch.py)), which is how the published Claude results were made:

- The 80 test inquiries were split into 4 batches of 20. Each batch file holds the same instructions as the API prompt plus the 20 messages, and asks for one JSON line per message, each handled "exactly as if it were the only message".
- Each batch went to a separate Claude Haiku 5.5, Sonnet 5.5 or Opus 5.5 subagent. The subagent was told to open only that batch file; every subagent made exactly one file read and returned its answer. It could not see the answer key.
- Each model did the 4 batches twice (24 subagent runs in total). Replies are saved unchanged in `runs/<model>/raw/` and converted to the same run files the API runner writes, so scoring is identical.
- Differences from the API route: 20 messages per request instead of one; the subagent has its own system prompt and default settings (no temperature 0); no token counts or response times are reported, so cost is estimated from list prices and speed is not measured.

**GPT models through Codex**: GPT-6.1 Sol and GPT-6 Luna were tested on October 23, 2026 using Codex CLI 0.163.0-alpha.11.1 with account login and no API key. Sol was the account's configured default model; Luna was selected as a smaller, lower-priced alternative. Both used `model_reasoning_effort=medium`, since Luna does not support the account's `ultra` setting.

- Each model did the same 80 test inquiries twice, in four batches of 20 per run. The batch folders were outside this repository.
- Each batch used a fresh `codex exec` instance with an explicit model, `--sandbox read-only`, `--skip-git-repo-check`, `--ephemeral`, and `--output-last-message`. User configuration was excluded and web search was disabled. The instance was instructed to read only its batch file and answer directly, without code, scripts, regex or web searches. The coordinating agent did not answer the inquiries or edit replies.
- Raw replies are preserved in `runs/codex__<model>/raw/`. Each batch was checked for 20 valid JSON lines and unique, matching IDs and imported with `batches.py`. The execution records in each method folder document the settings, file reads and reply hashes.
- Every batch completed on its first attempt. Four Luna sessions reported a nonfatal warning that skill descriptions exceeded the context budget and were trimmed. Some Luna replies named the model only as `GPT-6`; model identity follows the explicit CLI selection, and these self-reported lines were left unchanged.
- These are Codex batch tests, not API tests. The imported records contain no API token counts or per-inquiry timings. API costs and ROI are scenarios based on official list prices and the project's token estimate; actual Codex cost was not measured. The shared single-inquiry token estimate does not measure batching savings, caching or model-specific reasoning usage. Agent system prompts and settings differ from the Claude subagent route, so this does not isolate model effects.

**DeepSeek and Kimi through WorkBuddy**: DeepSeek V4 Pro, DeepSeek V4.1 Flash and Kimi K2.7 Code were tested on October 23, 2026 with the built-in models of WorkBuddy (Tencent's AI agent app), using its own credits and no API key.

- A first try asked a subagent for a specific model through a parameter. Its reply named the app's own default model instead, so that answer was thrown away and the method was changed.
- The final method: one chat per model, with the model chosen by hand in the app's model picker (not Auto). In that chat, a coordinating session read each batch file and pasted the full text into a fresh subagent, which inherits the chat's model and had no file access. Each subagent handled one batch. The coordinating session did not answer or edit anything and did not open this repository.
- The app does not report which model actually answered, so model identity rests on the picker choice. Every reply's MODEL line named the expected model (`deepseek-v4-pro`, `Deepseek-V4.1-Flash`, `Kimi-K2.7-Code`). The reasoning setting was the app's default and was not confirmed.
- 23 of 24 batches were right on the first try. Kimi run 1, batch 3 was rerun once in a new subagent because the first reply had a duplicated JSON key; the first reply was not kept. Details and reply hashes are in `runs/workbuddy__<model>/execution.json`.
- DeepSeek said in September that API requests for V4 Pro would be routed to V4.1 Flash, while its pricing page still lists V4 Pro as served (as summarized by BenchLM). WorkBuddy may serve these models on its own, so which weights answered cannot be checked here. The two did behave differently on this test (see section 7).

**Untested API routes**: Qwen remains untested. The `openai__` and `deepseek__` rows are pending API routes; the measured GPT and DeepSeek results use separate `codex__` and `workbuddy__` methods. They are the same model identities, not additional models. Cost-only scenarios count each provider/model ID once.

## 4. Scoring

Code: [`scoring.py`](../src/llmroi/scoring.py) and [`evaluate.py`](../src/llmroi/evaluate.py).

1. Parse the output as JSON (code fences are allowed). If it fails, every field is wrong.
2. Put values in standard form: units (m², кв.м, sqm), ports (Санкт-Петербург, St. Petersburg), Incoterms ("CIF Novorossiysk" is CIF), currencies ("$" is USD), delivery ("6 weeks" is 42 days), spec text (×, *, Cyrillic х, comma decimals, "мм").
3. Match predicted items to answer-key items by product.
4. Mark each field right or wrong. A spec is right if it contains every key token (size and thickness, grade, ply, color or type). Quantities must match within 0.5% and in the right unit; prices within 1% and in the right currency.

| Metric | Meaning |
|---|---|
| Critical error rate | Share of inquiries with a wrong product, spec, quantity, target price or delivery date, an invented item, a JSON failure, or a high-priority lead ranked lower. This is the number the ROI model uses. |
| Field accuracy | Share of all field checks that are right. |
| Weighted error | Sum of [field weights](../data/field_weights.csv) of wrong fields per inquiry (quantity and product 5, spec 4, price and delivery 3, ...). |
| Fabrication rate | Of the places where the message gives no value, the share where the method filled one in anyway. |
| Priority accuracy, missed-high rate | From the 3 × 3 confusion matrix ([`results/priority_confusion.csv`](../results/priority_confusion.csv)). |
| JSON failure rate | Share of unreadable outputs. |
| Output consistency (`consistency`) | Share of inquiries with identical normalized output in every run, excluding the priority explanation. Different spec wording can reduce this rate. |
| Score consistency (`score_consistency`) | Share with the same right/wrong result on every field in every run. This can be identical even when the output values differ. |
| Cost, latency | From the token counts and timing the API reports. Before a run, cost is estimated from list prices: input tokens are about 4 characters each for English and 2.5 for Russian; output is set to twice the length of a correct answer. |

## 5. ROI model

Code: [`roi.py`](../src/llmroi/roi.py) (Python) and [`docs/roi.js`](roi.js) (calculator). A test checks that both give the same numbers.

Per inquiry, compared with doing it by hand:

```
minutes saved    = manual minutes - review minutes - error rate x catch rate x fix minutes
labor saved      = minutes saved x hourly cost / 60
error cost       = (error rate x (1 - catch rate) - manual error rate) x cost of an escaped error
net per inquiry  = labor saved - API cost - error cost
net per month    = volume x net per inquiry - maintenance
payback          = setup cost / net per month
```

The error cost compares with people working alone, who also make mistakes. It can be negative: a draft plus a check can let fewer mistakes through than one person.

**Break-even error rate** is the critical error rate where net per month is zero:

```
(manual - review) x wage/60 - API cost + manual error rate x error cost - maintenance/volume
---------------------------------------------------------------------------------------------
        catch rate x fix minutes x wage/60 + (1 - catch rate) x error cost
```

With the base case: hourly cost $9.70 (¥8,672 x 1.30 / 174 h / 6.6781), 6 minutes by hand, 1.5 to review, 3 to fix a caught error, 80% caught, 2% manual error rate, $40 per escaped error, 500 inquiries and $50 maintenance a month. This gives **17.0%**.

**Sensitivity.** Each assumption moves alone between the low and high values in [`data/roi_inputs.csv`](../data/roi_inputs.csv), plus a "model price" row (cheapest vs. most expensive model). Results: [`results/sensitivity.csv`](../results/sensitivity.csv).

## 6. Public leaderboard scores

[`data/public_benchmarks.csv`](../data/public_benchmarks.csv) lists the Artificial Analysis Intelligence Index, checked on October 23, 2026. The Codex method rows use the public API model's medium setting (Sol 48, Luna 30, Index v4.3.2), matching the named reasoning setting in this experiment. Existing rows retain their highest listed settings. The WorkBuddy rows use the highest setting listed (DeepSeek V4 Pro 36, with 20 for non-reasoning; V4.1 Flash 45), because the app's reasoning setting was not confirmed; Kimi K2.7 Code has a single entry (26). These settings and routes are shown explicitly because the scores are not directly interchangeable. The index is a broad composite, not an inquiry extraction test or a Codex benchmark, and is not turned into an error rate.

On the three models tested both ways, the leaderboard spread (Haiku 43, Sonnet 56, Opus 58) did not show up on this task (0.0%, 0.6%, 0.0% critical errors). Across all eight tested models, the two lowest scores (Kimi K2.7 Code 26, GPT-6 Luna 30) did go with the most errors, but DeepSeek V4 Pro (36) made none. For a narrow, well-specified extraction job, a general leaderboard is a weak guide; a small test on your own messages is a better one.

## 7. A disputed label

R55 is a Russian inquiry for "термальные пластины CTP" (thermal CTP plates) with no size or thickness. The answer key has no spec, because a plate cannot be quoted without size and thickness. Sonnet (first run only), GPT-6.1 Sol (both runs), GPT-6 Luna (both runs), DeepSeek V4.1 Flash (both runs) and Kimi K2.7 Code (first run only) wrote "thermal" as the spec, which also fits the prompt's wording ("size, thickness, grade, color or type"). Haiku, Opus and DeepSeek V4 Pro matched the key in both runs. These are all of Sonnet's, Sol's and V4.1 Flash's critical errors. The key was set before any model ran and was not changed after seeing the results. Counting R55 as correct, Sonnet, Sol and V4.1 Flash have no critical errors, Luna has 9 in 160 (5.6%) and Kimi 18 in 160 (11.25%).

## 8. Good leads ranked too low

The rubric marks an inquiry high when every item has a spec and a quantity at or above the minimum order, and there is an Incoterm or a destination. Delivery is not required. Kimi K2.7 Code broke this 17 times: each time it gave "medium" because the Incoterm, destination or delivery date was missing (for example "Real inquiry with spec and quantity but no incoterm provided"). GPT-6 Luna did it 7 times, sometimes for the same reason and sometimes calling a complete spec incomplete. These make up 17 of Kimi's 19 and 7 of Luna's 11 critical errors. Kimi's other non-R55 error treated a sample request (2 blankets, then about 200 a quarter) as not a real inquiry. Neither model got a target price wrong.

Priority follows a fixed rule, so one fix worth testing is to work it out in code from the extracted fields instead of asking the model.

## 9. Choices made along the way

- **Two tasks, not more.** Extraction and priority are easy to score objectively. Reply drafting was left out because it is hard to grade fairly.
- **Single prompt, no tuning per model.** Fair and cheap. A team could tune the winner later.
- **Critical error rate drives ROI**, not average field accuracy: one wrong quantity matters more than three wrong "missing info" lists.
- **Human error is part of the comparison.** Without it, any AI error looks like pure loss.
- **Maintenance is inside the break-even; setup is not.** Setup is one-time, so it sets the payback period instead.

## 10. What would make this a real decision

1. Label 50 to 100 real, anonymized inquiries and re-run. The synthetic set is too easy for the Claude models to tell them apart.
2. Run the cheapest candidates through the API. For a Chinese team, confirm DeepSeek's result through its own API and add Qwen; both are reachable in mainland China.
3. Time 10 inquiries by hand and 10 AI reviews to replace the minutes assumptions.
4. Pick the cheapest model under the bar, then track the catch rate in the first month.
