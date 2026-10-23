"""Run one method on the dataset and save its raw answers to runs/.

Usage:
  python run_eval.py rules                                   # no AI, free, a few seconds
  python run_eval.py anthropic:claude-haiku-5-5 --runs 3      # needs ANTHROPIC_API_KEY
  python run_eval.py deepseek:deepseek-flash --runs 3         # needs DEEPSEEK_API_KEY
  python run_eval.py qwen:qwen3.7-flash --runs 3              # needs DASHSCOPE_API_KEY
  python run_eval.py openai:gpt-6-luna --runs 3               # needs OPENAI_API_KEY

Then run `python run_analysis.py` to score everything and refresh the charts and the calculator.
Tip: try `--split dev --runs 1` first (20 inquiries) to check the key and the cost.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from llmroi.dataset import load_dataset  # noqa: E402
from llmroi.runner import run_method  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("method", help='"rules" or "provider:model", e.g. anthropic:claude-haiku-5-5')
    parser.add_argument("--runs", type=int, default=3, help="repeat runs, used for the consistency check")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--base-url", default=None, help="override the provider's API address")
    parser.add_argument("--pause", type=float, default=0.0, help="seconds to wait between calls")
    args = parser.parse_args()

    inquiries, _ = load_dataset(None if args.split == "all" else args.split)
    folder = run_method(args.method, inquiries, runs=args.runs, base_url=args.base_url, pause_s=args.pause)
    print(f"Saved to {folder.relative_to(ROOT)}. Next: python run_analysis.py")


if __name__ == "__main__":
    main()
