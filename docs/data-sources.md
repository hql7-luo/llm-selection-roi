# Data sources

Sourced inputs are in [`data/pricing.csv`](../data/pricing.csv) and [`data/roi_inputs.csv`](../data/roi_inputs.csv) (each row marked **sourced** or **assumption**). All were checked on October 23, 2026. API prices change often; re-check before reusing.

## API prices (USD per million tokens)

| Model | Input | Output | Source |
|---|---:|---:|---|
| Claude Haiku 5.5 | 0.10 | 0.50 | [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing) (official; rate for prompts up to 100K tokens) |
| Claude Sonnet 5.5 | 2.00 | 10.00 | same |
| Claude Opus 5.5 | 4.00 | 20.00 | same |
| GPT-6 Luna (`gpt-6-luna`) | 0.10 | 0.50 | [BenchLM OpenAI price table](https://benchlm.ai/openai/api-pricing), synced Oct 20, 2026, citing developers.openai.com/api/docs/pricing |
| GPT-6.1 Sol (`gpt-6.1-sol`) | 2.00 | 10.00 | same |
| DeepSeek V4.1 Flash (`deepseek-flash`) | 0.30 | 1.20 | [BenchLM DeepSeek price table](https://benchlm.ai/deepseek/api-pricing), citing api-docs.deepseek.com; peak-hour rate, off-peak is half |
| Qwen3.7 Flash | 0.03 | 0.13 | [BenchLM Alibaba price table](https://benchlm.ai/alibaba/api-pricing), synced Oct 20, 2026, citing Alibaba Model Studio; international rate |
| Qwen3.5 Plus | 0.40 | 2.40 | same |

The OpenAI, DeepSeek and Alibaba official pages could not be opened from the build environment, so their prices come from a secondary table that cites them. Qwen model IDs were not listed by the source; confirm them in Model Studio before running.

## Labor and exchange rate

| Fact used | Source |
|---|---|
| Foreign-trade salesperson (外贸部业务员), Hangzhou: average ¥8,672 a month, 4,443 postings over the past year | [Liepin salary page](https://www.liepin.com/city-hz/zpwaimaobuyewuyuan/xinzi/) |
| 21.75 paid days a month (月计薪天数), the official figure for turning monthly pay into daily and hourly pay; x 8 hours = 174 hours | Ministry of Human Resources and Social Security notice on average monthly working time and pay conversion (2008) |
| USD/CNY 6.6781 on October 22, 2026 | [Pound Sterling Live, USD/CNY 2026 history](https://www.poundsterlinglive.com/history/USD-CNY-2026) |

## Assumptions

Every other ROI input (handling and review minutes, fix time, catch rate, manual error rate, cost of an escaped error, volume, setup and maintenance cost, employer overhead) is an assumption with a low and high value in [`data/roi_inputs.csv`](../data/roi_inputs.csv). The [sensitivity chart](../figures/4_sensitivity.png) shows how much each one matters.
