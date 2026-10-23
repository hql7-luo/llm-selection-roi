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

**Other vendors**: OpenAI, DeepSeek and Alibaba could not be reached from the build environment, so they are compared on list price and a public leaderboard score only (section 6).

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
| JSON failure rate, consistency | Share of unreadable outputs; share of inquiries with identical output in every run, and share with the same right/wrong result on every field in every run (the spec may be worded differently). |
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

[`data/public_benchmarks.csv`](../data/public_benchmarks.csv) lists the Artificial Analysis Intelligence Index for each model, taken at the highest reasoning setting listed on October 23, 2026. It is a broad reasoning composite, not an extraction test, so it is shown for reference only and is not turned into an error rate.

On the three models tested both ways, the leaderboard spread (Haiku 43, Sonnet 56, Opus 58) did not show up on this task (0.0%, 0.6%, 0.0% critical errors). For a narrow, well-specified extraction job, a general leaderboard is a weak guide; a small test on your own messages is a better one.

## 7. A disputed label

R55 is a Russian inquiry for "термальные пластины CTP" (thermal CTP plates) with no size or thickness. The answer key has no spec, because a plate cannot be quoted without size and thickness. Sonnet's first run wrote "thermal" as the spec, which also fits the prompt's wording ("size, thickness, grade, color or type"). This is the only critical error by any Claude model. The key was not changed after seeing the results.

## 8. Choices made along the way

- **Two tasks, not more.** Extraction and priority are easy to score objectively. Reply drafting was left out because it is hard to grade fairly.
- **Single prompt, no tuning per model.** Fair and cheap. A team could tune the winner later.
- **Critical error rate drives ROI**, not average field accuracy: one wrong quantity matters more than three wrong "missing info" lists.
- **Human error is part of the comparison.** Without it, any AI error looks like pure loss.
- **Maintenance is inside the break-even; setup is not.** Setup is one-time, so it sets the payback period instead.

## 9. What would make this a real decision

1. Label 50 to 100 real, anonymized inquiries and re-run. The synthetic set is too easy for the Claude models to tell them apart.
2. Run the cheapest candidates through the API (for a Chinese team, include DeepSeek and Qwen, which are reachable in mainland China).
3. Time 10 inquiries by hand and 10 AI reviews to replace the minutes assumptions.
4. Pick the cheapest model under the bar, then track the catch rate in the first month.
