"""Send each inquiry to a method and save the raw answers.

Methods are written as "provider:model", e.g. "anthropic:claude-haiku-5-5" or "deepseek:deepseek-flash",
plus "rules" for the no-AI baseline. Every LLM gets the same prompt (prompts/extract_v1.txt),
temperature 0 and the same output format. Raw answers go to runs/<provider>__<model>/run<N>.jsonl,
one line per inquiry, so scoring can be re-run any time without calling the API again.
"""

import json
import os
import time
from pathlib import Path

import requests

from . import rules

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = ROOT / "prompts" / "extract_v1.txt"

# Where each provider lives and which environment variable holds its key
PROVIDERS = {
    "anthropic": {"style": "anthropic", "base_url": "https://api.anthropic.com/v1", "key_env": "ANTHROPIC_API_KEY"},
    "openai":    {"style": "openai", "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY"},
    "deepseek":  {"style": "openai", "base_url": "https://api.deepseek.com", "key_env": "DEEPSEEK_API_KEY"},
    # International endpoint; inside mainland China use https://dashscope.aliyuncs.com/compatible-mode/v1
    "qwen":      {"style": "openai", "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                  "key_env": "DASHSCOPE_API_KEY"},
}


def build_prompt(inquiry):
    template = PROMPT_FILE.read_text(encoding="utf-8")
    return template.replace("{received}", inquiry["received"]).replace("{text}", inquiry["text"])


def method_folder(method):
    return "rules" if method == "rules" else method.replace(":", "__")


# One Anthropic Messages API call -> (text, input tokens, output tokens)
def call_anthropic(base_url, api_key, model, prompt, max_tokens):
    response = requests.post(
        f"{base_url}/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    text = "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")
    usage = body.get("usage", {})
    return text, usage.get("input_tokens"), usage.get("output_tokens")


# One call to any OpenAI-compatible chat API (OpenAI, DeepSeek, Qwen) -> (text, input, output tokens)
def call_openai_style(base_url, api_key, model, prompt, max_tokens):
    payload = {"model": model, "temperature": 0, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": prompt}]}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=120)
    if response.status_code == 400 and "temperature" in response.text:
        payload.pop("temperature")                     # some newer models only allow the default
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=120)
    if response.status_code == 400 and "max_tokens" in response.text:
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    usage = body.get("usage", {})
    return body["choices"][0]["message"].get("content") or "", usage.get("prompt_tokens"), usage.get("completion_tokens")


# Run one method over the inquiries; resumes a half-finished run file instead of starting over
def run_method(method, inquiries, runs=1, base_url=None, max_tokens=1000, pause_s=0.0):
    folder = ROOT / "runs" / method_folder(method)
    folder.mkdir(parents=True, exist_ok=True)
    if method == "rules":
        runs = 1                                   # rules give the same answer every time

    for n in range(1, runs + 1):
        path = folder / f"run{n}.jsonl"
        done = set()
        if path.exists():
            with open(path, encoding="utf-8") as f:
                done = {json.loads(line)["id"] for line in f if line.strip() and '"error": null' in line}
        todo = [q for q in inquiries if q["id"] not in done]
        print(f"{method} run {n}: {len(done)} done, {len(todo)} to go")
        with open(path, "a", encoding="utf-8") as f:
            for q in todo:
                f.write(json.dumps(call_once(method, q, base_url, max_tokens), ensure_ascii=False) + "\n")
                f.flush()
                time.sleep(pause_s)
    return folder


def call_once(method, inquiry, base_url, max_tokens):
    record = {"id": inquiry["id"], "output": None, "latency_s": None,
              "input_tokens": None, "output_tokens": None, "error": None}
    start = time.perf_counter()
    try:
        if method == "rules":
            record["output"] = rules.extract(inquiry["text"], inquiry["received"])
        else:
            provider, model = method.split(":", 1)
            config = PROVIDERS[provider]
            api_key = os.environ.get(config["key_env"])
            if not api_key:
                raise RuntimeError(f"Set {config['key_env']} first")
            call = call_anthropic if config["style"] == "anthropic" else call_openai_style
            text, tokens_in, tokens_out = call(base_url or config["base_url"], api_key, model,
                                               build_prompt(inquiry), max_tokens)
            record.update(output=text, input_tokens=tokens_in, output_tokens=tokens_out)
    except Exception as exc:                       # keep going; the error is saved and the id is retried next time
        record["error"] = f"{type(exc).__name__}: {exc}"[:300]
    record["latency_s"] = round(time.perf_counter() - start, 3)
    return record
