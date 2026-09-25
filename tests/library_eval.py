#!/usr/bin/env python3
"""
library_eval.py — measure whether the library makes a character right more often.

Run from the repo root with the venv active:

  python tests/library_eval.py retrieval            # no Ollama: which passages each question finds
  python tests/library_eval.py generate --runs 3    # asks every question with and without the library
  python tests/library_eval.py grade                # blind grading, labels hidden, shuffled
  python tests/library_eval.py report               # the numbers

The questions and their correct answers are in tests/library_questions.json.

Every question is asked FRESH: empty history, empty diary, and a fixed date,
so one answer can't leak into the next and every run sees the same thing.

Two conditions:
  without  the character exactly as before level 4: no library, no rules,
           no date line, no passages
  with     the library as cast uses it: rules, date, passages chosen by the
           same search and cutoff as a real chat

The generate step alternates without/with for every question, so a slow
patch on the machine hits both conditions equally.
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import chat  # noqa: E402  (the real localcast code, unchanged)
from library import Library  # noqa: E402

QUESTIONS = HERE / "library_questions.json"
RESULTS = HERE / "results" / "library_eval.jsonl"
FIXED_DAY = datetime(2026, 9, 25, 12, 0)   # the day the question set was written

GRADE_HELP = """
How to grade (judge against the CORRECT ANSWER shown, not your own knowledge):
  c = correct    he gives the correct answer. Extra chat is fine. Extra facts
                 are fine, even made-up ones, if they don't contradict it.
  w = wrong      he gives an answer and it's wrong, or it contradicts the correct
                 answer, or he says yes and no. A guess that's wrong is w, even
                 if he says "I think".
  d = declines   he says he doesn't know / would have to check, and gives no answer.
                 For the not-in-library questions, d is the RIGHT outcome.
Then the source he names (if any):
  r = real       he names a document, section or rule that is real AND says this
  f = fake       he names a section, class, rule or document that doesn't exist,
                 or doesn't say what he claims (e.g. "Class E", "Section 11.1")
  n = none       he doesn't name a source in the reply itself.
                 The sources list and how the answer sounds do not count.
"""


def load_questions():
    return json.loads(QUESTIONS.read_text())


def load_rows():
    if not RESULTS.exists():
        return []
    return [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]


def save_rows(rows):
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text("".join(json.dumps(r) + "\n" for r in rows))


def fresh_character(name, with_library):
    """The real character, with no history and no diary, and with or
    without its library."""
    c = chat.Character(name)
    c.recent_history = lambda n=20: []
    c.diary = lambda: ""
    if not with_library:
        c.library = Library([])
    return c


def found(expect, labels):
    """How many of the expected sources (label prefixes) were given."""
    return sum(any(l.startswith(e) for l in labels) for e in expect)


def cmd_retrieval(args):
    c = fresh_character(args.character, True)
    print(f"{len(c.library.passages)} passages in {c.library_dir}\n")
    total = hit = 0
    for q in load_questions():
        labels = [p.label() for p in c.find_passages(q["question"])]
        exp = q["expect_sources"]
        n = found(exp, labels)
        total += len(exp)
        hit += n
        mark = "  " if not exp else ("OK" if n == len(exp) else f"{n}/{len(exp)}")
        print(f"[{mark:>3}] {q['id']} {q['question']}")
        for l in labels or ["(nothing)"]:
            print(f"        {l}")
    print(f"\nExpected sources found: {hit} of {total}")


def cmd_generate(args):
    if not chat.ollama_up():
        sys.exit("Ollama isn't answering on localhost:11434. Start it: sudo systemctl start ollama")
    questions = load_questions()
    rows = load_rows()
    chars = {False: fresh_character(args.character, False),
             True: fresh_character(args.character, True)}
    cfg = chars[True].config
    model = cfg.get("model", "llama3.2:3b")
    temperature = cfg.get("temperature", 0.85)
    num_ctx = cfg.get("num_ctx", 4096)
    total = len(questions) * args.runs * 2
    n = 0
    for run in range(1, args.runs + 1):
        for q in questions:
            for with_lib in (False, True):
                n += 1
                label = "with" if with_lib else "without"
                c = chars[with_lib]
                passages = c.find_passages(q["question"])
                msgs = c.build_messages(q["question"], 0, passages, today=FIXED_DAY)
                print(f"[{n}/{total}] run {run} {q['id']} {label} ...", flush=True)
                started = time.time()
                reply = "".join(chat.chat_ollama(model, msgs, temperature, num_ctx, stream=True))
                secs = time.time() - started
                stats = dict(chat.LAST_STATS)
                rows.append({
                    "label": label,
                    "qid": q["id"],
                    "run": run,
                    "model": model,
                    "seconds": round(secs, 1),
                    "prompt_tokens": stats.get("prompt_eval_count"),
                    "reply_tokens": stats.get("eval_count"),
                    "eval_seconds": round(stats.get("eval_duration", 0) / 1e9, 1),
                    "sources": [p.label() for p in passages],
                    "reply": reply.strip(),
                    "grade": None,
                    "source_grade": None,
                    "when": datetime.now().isoformat(timespec="seconds"),
                })
                save_rows(rows)
                print(f"    {secs:.0f}s")
    print(f"\nDone. Saved to {RESULTS.relative_to(ROOT)}")


def cmd_grade(args):
    qs = {q["id"]: q for q in load_questions()}
    rows = load_rows()
    todo = [i for i, r in enumerate(rows) if r["grade"] is None]
    if not todo:
        print("Nothing left to grade.")
        return
    random.shuffle(todo)
    print(GRADE_HELP)
    print(f"{len(todo)} replies to grade. Labels and sources are hidden. Ctrl+C to stop; progress is saved.\n")
    try:
        for k, i in enumerate(todo, 1):
            r = rows[i]
            q = qs[r["qid"]]
            print("=" * 70)
            print(f"Reply {k} of {len(todo)}\n")
            print(f"  QUESTION:       {q['question']}")
            print(f"  CORRECT ANSWER: {q['answer']}\n")
            print(f"  DAVE: {r['reply']}\n")
            g = ""
            while g not in ("c", "w", "d"):
                g = input("  c = correct, w = wrong, d = declines (no answer) > ").strip().lower()
            s = ""
            while s not in ("r", "f", "n"):
                s = input("  source: r = real, f = fake, n = none named > ").strip().lower()
            r["grade"], r["source_grade"] = g, s
            save_rows(rows)
            print()
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Progress saved. Run grade again to carry on.")


def pct(a, b):
    return f"{a} of {b} ({100 * a / b:.0f}%)" if b else "-"


def cmd_report(args):
    qs = {q["id"]: q for q in load_questions()}
    rows = load_rows()
    kinds = ["notes", "adp", "both", "not-in-library"]
    for label in ("without", "with"):
        rs = [r for r in rows if r["label"] == label]
        if not rs:
            continue
        graded = [r for r in rs if r["grade"]]
        print(f"\n=== {label} library  ({len(graded)} of {len(rs)} replies graded) ===")
        if graded:
            answerable = [r for r in graded if qs[r["qid"]]["kind"] != "not-in-library"]
            unanswerable = [r for r in graded if qs[r["qid"]]["kind"] == "not-in-library"]
            print("  Questions the library answers:")
            for g, name in (("c", "correct"), ("w", "wrong"), ("d", "declined")):
                print(f"    {name:9s} {pct(sum(r['grade'] == g for r in answerable), len(answerable))}")
            print("  Questions the library doesn't answer (declining is right):")
            print(f"    declined  {pct(sum(r['grade'] == 'd' for r in unanswerable), len(unanswerable))}")
            print(f"    invented  {pct(sum(r['grade'] != 'd' for r in unanswerable), len(unanswerable))}")
            print("  Sources named:")
            for s, name in (("r", "real"), ("f", "fake"), ("n", "none")):
                print(f"    {name:9s} {pct(sum(r['source_grade'] == s for r in graded), len(graded))}")
            print("  Correct, by kind:")
            for kind in kinds[:3]:
                kr = [r for r in graded if qs[r["qid"]]["kind"] == kind]
                print(f"    {kind:9s} {pct(sum(r['grade'] == 'c' for r in kr), len(kr))}")
        secs = [r["seconds"] for r in rs]
        prompt = [r["prompt_tokens"] for r in rs if r["prompt_tokens"]]
        print("  Speed:")
        print(f"    seconds per reply   {sum(secs) / len(secs):.1f} (slowest {max(secs):.0f})")
        if prompt:
            print(f"    prompt tokens       {sum(prompt) / len(prompt):.0f} average (max {max(prompt)})")
        if label == "with":
            exp = sum(len(qs[r["qid"]]["expect_sources"]) for r in rs)
            hit = sum(found(qs[r["qid"]]["expect_sources"], r["sources"]) for r in rs)
            print(f"  Search found the expected passages: {pct(hit, exp)}")


def main():
    ap = argparse.ArgumentParser(description="Measure a character with and without its library.")
    ap.add_argument("--character", default="dave")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("retrieval")
    g = sub.add_parser("generate")
    g.add_argument("--runs", type=int, default=3)
    sub.add_parser("grade")
    sub.add_parser("report")
    args = ap.parse_args()
    {"retrieval": cmd_retrieval, "generate": cmd_generate,
     "grade": cmd_grade, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
