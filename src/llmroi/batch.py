"""Run the test through Claude subagents (no API key) instead of the API.

The API runner sends one inquiry per call. Here a batch of inquiries goes to one subagent with the
same instructions (prompts/extract_v1.txt), and the reply is one JSON line per inquiry. The replies
are saved as-is in runs/<method>/raw/ and converted into the same run files the API runner writes,
so scoring does not change. Differences from the API route are listed in docs/methodology.md.
"""

import json
import re
from pathlib import Path

from .runner import PROMPT_FILE

BATCH_SIZE = 20


# The shared instructions: everything in the prompt file before the single-message part
def instructions():
    template = PROMPT_FILE.read_text(encoding="utf-8")
    return template.split("MESSAGE (received {received})")[0].rstrip()


def batch_prompt(inquiries):
    parts = [
        "Work only from the text in this file. Do not open, list or search any other file or folder.",
        "",
        instructions(),
        "",
        f"BATCH: you will get {len(inquiries)} messages. Handle each one on its own, exactly as if it were the "
        "only message. Reply in this format and add nothing else:",
        "MODEL: <your model name>",
        "```jsonl",
        '{"id": "<message id>", "answer": <the JSON object for that message>}',
        "... one line per message, in the same order ...",
        "```",
        "",
    ]
    for q in inquiries:
        parts.append(f"=== MESSAGE {q['id']} (received {q['received']}) ===")
        parts.append(q["text"])
        parts.append("")
    return "\n".join(parts)


def batches(inquiries, size=BATCH_SIZE):
    return [inquiries[i:i + size] for i in range(0, len(inquiries), size)]


# Subagent reply -> {id: raw answer text}; lines that do not parse are kept as raw text (scored as failures)
def parse_reply(text):
    answers = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        m = re.match(r'\{\s*"id"\s*:\s*"([^"]+)"', line)
        if not m:
            continue
        try:
            answers[m.group(1)] = json.dumps(json.loads(line)["answer"], ensure_ascii=False)
        except (json.JSONDecodeError, KeyError):
            answers[m.group(1)] = line
    return answers


def model_line(text):
    m = re.search(r"MODEL:\s*(.+)", text)
    return m.group(1).strip() if m else None


# Turn saved raw replies into runs/<method>/run<N>.jsonl (one record per inquiry, no token counts)
def import_raw(method_dir, ids):
    method_dir = Path(method_dir)
    for raw_run in sorted((method_dir / "raw").glob("run*")):
        answers, models = {}, set()
        for path in sorted(raw_run.glob("batch*.txt")):
            text = path.read_text(encoding="utf-8")
            answers.update(parse_reply(text))
            models.add(model_line(text))
        with open(method_dir / f"{raw_run.name}.jsonl", "w", encoding="utf-8") as f:
            for i in ids:
                record = {"id": i, "output": answers.get(i), "latency_s": None, "input_tokens": None,
                          "output_tokens": None, "error": None, "via": "claude subagent, batch of 20",
                          "model_reported": ", ".join(sorted(m for m in models if m))}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
