"""Test a model without an API key: let a coding agent (Claude Code, Codex, ...) answer batch files.

Step 1, in this repo:     python batches.py make OUT_DIR
    Writes OUT_DIR/batch1.txt ... batch4.txt (the 80 test inquiries, 20 per file, with the instructions).
    Copy OUT_DIR somewhere outside the repo so the agent answering it cannot see the answer key.

Step 2, outside the repo: the agent answers each batch file in a fresh session and saves its reply
    next to it as reply1.txt ... reply4.txt (the MODEL line plus the jsonl block, nothing else).

Step 3, in this repo:     python batches.py import METHOD RUN REPLIES_DIR [VIA]
    e.g.  python batches.py import codex__<model-name> run1 ~/llm-batches "Codex, batch of 20"
    Copies the replies to runs/METHOD/raw/RUN/ and writes runs/METHOD/RUN.jsonl.
    Then run `python run_analysis.py`. Add a row for METHOD to data/pricing.csv if it has an API price.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from llmroi.batch import batch_prompt, batches, import_raw  # noqa: E402
from llmroi.dataset import load_dataset  # noqa: E402


def make(out_dir):
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    inquiries, _ = load_dataset("test")
    for k, batch in enumerate(batches(inquiries), 1):
        (out / f"batch{k}.txt").write_text(batch_prompt(batch), encoding="utf-8")
    print(f"Wrote {k} batch files to {out}")


def import_replies(method, run, replies_dir, via="coding agent, batch of 20"):
    src = Path(replies_dir).expanduser()
    dest = ROOT / "runs" / method / "raw" / run
    dest.mkdir(parents=True, exist_ok=True)
    replies = sorted(src.glob("reply*.txt"))
    if not replies:
        sys.exit(f"No reply*.txt files in {src}")
    for path in replies:
        shutil.copy(path, dest / path.name.replace("reply", "batch"))
    inquiries, _ = load_dataset("test")
    import_raw(ROOT / "runs" / method, [q["id"] for q in inquiries], via)
    print(f"Imported {len(replies)} replies into runs/{method}/{run}.jsonl. Next: python run_analysis.py")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "make":
        make(sys.argv[2])
    elif len(sys.argv) in (5, 6) and sys.argv[1] == "import":
        import_replies(*sys.argv[2:])
    else:
        print(__doc__)
