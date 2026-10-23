# Data sources

Sourced inputs are in [`data/pricing.csv`](../data/pricing.csv) and [`data/roi_inputs.csv`](../data/roi_inputs.csv) (each row marked **sourced** or **assumption**). All were checked on October 23, 2026. API prices change often; re-check before reusing.

## API prices (USD per million tokens)

| Model | Input | Output | Source |
|---|---:|---:|---|
| Claude Haiku 5.5 | 0.10 | 0.50 | [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing) (official; rate for prompts up to 100K tokens) |
| Claude Sonnet 5.5 | 2.00 | 10.00 | same |
| Claude Opus 5.5 | 4.00 | 20.00 | same |
| GPT-6 Luna (`openai__gpt-6-luna`, pending API test) | 0.10 | 0.50 | [BenchLM OpenAI price table](https://benchlm.ai/openai/api-pricing), synced Oct 20, 2026, citing developers.openai.com/api/docs/pricing; original reference row retained |
| GPT-6.1 Sol (`openai__gpt-6.1-sol`, pending API test) | 2.00 | 10.00 | same |
| GPT-6.1 Sol (`codex__gpt-6.1-sol`) | 2.00 | 10.00 | [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) (official; Standard, short context; checked October 23, 2026) |
| GPT-6 Luna (`codex__gpt-6-luna`) | 0.10 | 0.50 | same |
| DeepSeek V4.1 Flash (`deepseek-flash`) | 0.30 | 1.20 | [BenchLM DeepSeek price table](https://benchlm.ai/deepseek/api-pricing), citing api-docs.deepseek.com; peak-hour rate, off-peak is half |
| Qwen3.7 Flash | 0.03 | 0.13 | [BenchLM Alibaba price table](https://benchlm.ai/alibaba/api-pricing), synced Oct 20, 2026, citing Alibaba Model Studio; international rate |
| Qwen3.5 Plus | 0.40 | 2.40 | same |

The two `codex__` rows use official OpenAI API reference prices for Standard processing with up to 272K input tokens. The [GPT-6.1 Sol model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) also confirm these rates. Both models were tested in Codex in batches of 20 at medium reasoning. These were not API tests, and Codex cost was not measured. The reference token prices do not establish the cost of these Codex runs.

The original `openai__` rows remain as historical pricing references for pending API tests; their values came from the cited secondary table. The official OpenAI pages were opened and verified on October 23, 2026 for the new Codex rows. DeepSeek and Alibaba prices still come from secondary tables because their official pages could not be opened during the original collection. Qwen model IDs were not listed by the source; confirm them in Model Studio before running.

## Public leaderboard

| Model | Artificial Analysis Intelligence Index | Setting |
|---|---:|---|
| Claude Opus 5.5 | 58 | max with fallback |
| Claude Sonnet 5.5 | 56 | max with fallback |
| GPT-6.1 Sol (`openai__`, historical reference) | 52 | max |
| DeepSeek V4.1 Flash | 45 | 1017 (max) |
| Claude Haiku 5.5 | 43 | max |
| GPT-6 Luna (`openai__`, historical reference) | 38 | max |
| GPT-6.1 Sol (`codex__gpt-6.1-sol`) | 48 | medium; Intelligence Index v4.3.2 |
| GPT-6 Luna (`codex__gpt-6-luna`) | 30 | medium; Intelligence Index v4.3.2 |
| Qwen3.7 Flash, Qwen3.5 Plus | not listed | |

Source: [Artificial Analysis model leaderboard](https://artificialanalysis.ai/leaderboards/models), read October 23, 2026. The new medium entries are also documented on the [GPT-6.1 Sol medium page](https://artificialanalysis.ai/models/gpt-6-1-sol-medium) and [GPT-6 Luna medium page](https://artificialanalysis.ai/models/gpt-6-luna-medium), checked October 23, 2026. These are public API benchmark scores from a general reasoning composite, shown for reference only. They are not inquiry extraction scores or Codex benchmarks. The max entries remain as historical references and use a different reasoning setting from this Codex test.

## Labor and exchange rate

| Fact used | Source |
|---|---|
| Foreign-trade salesperson (外贸部业务员), Hangzhou: average ¥8,672 a month, 4,443 postings over the past year | [Liepin salary page](https://www.liepin.com/city-hz/zpwaimaobuyewuyuan/xinzi/) |
| 21.75 paid days a month (月计薪天数), the official figure for turning monthly pay into daily and hourly pay; x 8 hours = 174 hours | Ministry of Human Resources and Social Security notice on average monthly working time and pay conversion (2008) |
| USD/CNY 6.6781 on October 22, 2026 | [Pound Sterling Live, USD/CNY 2026 history](https://www.poundsterlinglive.com/history/USD-CNY-2026) |

## Assumptions

Every other ROI input (handling and review minutes, fix time, catch rate, manual error rate, cost of an escaped error, volume, setup and maintenance cost, employer overhead) is an assumption with a low and high value in [`data/roi_inputs.csv`](../data/roi_inputs.csv). The [sensitivity chart](../figures/4_sensitivity.png) shows how much each one matters.
