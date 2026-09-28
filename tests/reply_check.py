#!/usr/bin/env python3
"""
reply_check.py — ask the character a few Level 4 questions fresh and show
what he says, with the passages he was given. A quick look, not a graded
eval: nothing is saved to results/library_eval.jsonl.

Run from the repo root with the venv active:

  python tests/reply_check.py                    # P1, B2, P4, 3 runs each
  python tests/reply_check.py P1 P4 --runs 5

Each question is asked exactly as in library_eval.py's "with" condition:
empty history, empty diary, the fixed date, and the library passages chosen
by the same search a real chat uses.
"""

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import chat  # noqa: E402
from library_eval import FIXED_DAY, fresh_character, load_questions  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", default=["P1", "B2", "P4"], help="question ids from library_questions.json")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--character", default="dave")
    args = ap.parse_args()

    if not chat.ollama_up():
        sys.exit("Ollama isn't answering on localhost:11434. Start it: sudo systemctl start ollama")
    qs = {q["id"]: q for q in load_questions()}
    unknown = [i for i in args.ids if i not in qs]
    if unknown:
        sys.exit(f"Unknown question id(s): {', '.join(unknown)}")

    c = fresh_character(args.character, True)
    cfg = c.config
    model = cfg.get("model", "llama3.2:3b")
    print(f"{args.character}, {model}, {len(c.library.passages)} passages\n")

    for qid in args.ids:
        q = qs[qid]
        passages = c.find_passages(q["question"])
        print("=" * 72)
        print(f"{qid}: {q['question']}")
        print(f"Correct: {q['answer']}")
        print("Given:  " + ("\n        ".join(p.label() for p in passages) or "(nothing)"))
        for run in range(1, args.runs + 1):
            msgs = c.build_messages(q["question"], 0, passages, today=FIXED_DAY)
            started = time.time()
            reply = "".join(chat.chat_ollama(
                model, msgs, cfg.get("temperature", 0.85), cfg.get("num_ctx", 4096), stream=True))
            print(f"\n--- run {run} ({time.time() - started:.0f}s)")
            print(reply.strip())
        print()


if __name__ == "__main__":
    main()
