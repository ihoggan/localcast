#!/usr/bin/env python3
"""
diary_eval.py — measure how honest the diary extractor is.

Three steps, run from the repo root with the venv active:

  python tests/diary_eval.py generate --label before --runs 3
  python tests/diary_eval.py grade
  python tests/diary_eval.py report

generate  runs the CURRENT extract_diary_update() in chat.py over every
          scripted conversation in diary_fixtures.json, --runs times each,
          and saves the raw proposals. --fixtures picks another file of
          conversations in tests/ (e.g. diary_holdout.json). Run it once before the fix
          (--label before) and once after (--label after).

grade     shows you every ungraded proposal, from all labels, SHUFFLED and
          WITHOUT its label, so you can't tell which version wrote it.
          For each proposed diary line you answer:
              s = supported  (the Maker really said this)
              i = invented   (not said by the Maker: made up, exaggerated,
                              or actually about the character)
          Then you say which of the Maker's real facts were captured.
          You can stop with Ctrl+C at any point; progress is saved.

report    prints the numbers per label.
"""

import argparse
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import chat  # noqa: E402  (the real localcast code, unchanged)

RESULTS = HERE / "results" / "diary_eval.jsonl"

# Anything in square brackets at the end of a line (e.g. a supporting quote
# added by a later version) is hidden while grading, so both versions look
# the same to the grader.
TRAILER = re.compile(r"\s*\[[^\]]*\]\s*$")


class StubCharacter:
    """Just enough of chat.Character for extract_diary_update()."""

    def __init__(self, name="dave"):
        self.name = name

    def diary(self):
        return ""


def load_rows():
    if not RESULTS.exists():
        return []
    return [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]


def save_rows(rows):
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text("".join(json.dumps(r) + "\n" for r in rows))


def load_fixtures():
    """Every conversation from every tests/diary_*.json file, keyed by id."""
    out = {}
    for f in sorted(HERE.glob("diary_*.json")):
        for fx in json.loads(f.read_text()):
            out[fx["id"]] = fx
    return out


def cmd_generate(args):
    if not chat.ollama_up():
        sys.exit("Ollama isn't answering on localhost:11434. Start it: sudo systemctl start ollama")
    path = HERE / args.fixtures
    if not path.exists():
        sys.exit(f"No such fixtures file: {path}")
    fixtures = json.loads(path.read_text())
    rows = load_rows()
    total = len(fixtures) * args.runs
    n = 0
    for fx in fixtures:
        for run in range(1, args.runs + 1):
            n += 1
            print(f"[{n}/{total}] {fx['id']} run {run} ...", flush=True)
            started = datetime.now()
            out = chat.extract_diary_update(StubCharacter(), fx["turns"], args.model)
            secs = (datetime.now() - started).total_seconds()
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            rows.append({
                "label": args.label,
                "fixture": fx["id"],
                "run": run,
                "model": args.model,
                "seconds": round(secs, 1),
                "raw": out,
                "lines": lines,
                "grades": None,
                "captured": None,
                "when": started.isoformat(timespec="seconds"),
            })
            save_rows(rows)
            print(f"    {len(lines)} line(s), {secs:.0f}s")
    print(f"\nDone. Saved to {RESULTS.relative_to(ROOT)}")


def cmd_grade(args):
    fixtures = load_fixtures()
    rows = load_rows()
    todo = [i for i, r in enumerate(rows) if r["grades"] is None]
    if not todo:
        print("Nothing left to grade.")
        return
    random.shuffle(todo)
    print(f"{len(todo)} extraction(s) to grade. Labels are hidden. Ctrl+C to stop; progress is saved.\n")
    try:
        for k, i in enumerate(todo, 1):
            r = rows[i]
            fx = fixtures[r["fixture"]]
            print("=" * 70)
            print(f"Extraction {k} of {len(todo)}   (conversation: {fx['id']})\n")
            for t in fx["turns"]:
                who = "MAKER" if t["role"] == "user" else "DAVE "
                print(f"  {who}: {t['content']}")
            print("\n  Proposed diary lines:")
            grades = []
            if not r["lines"]:
                print("    (none: the extractor said NONE)")
            for j, line in enumerate(r["lines"], 1):
                shown = TRAILER.sub("", line)
                print(f"\n    {j}. {shown}")
                g = ""
                while g not in ("s", "i"):
                    g = input("       s = Maker said it, i = invented/not the Maker's > ").strip().lower()
                grades.append(g)
            captured = []
            if fx["maker_facts"]:
                print("\n  The Maker's real facts in this conversation:")
                for j, f in enumerate(fx["maker_facts"], 1):
                    print(f"    {j}. {f}")
                ans = input("  Which were captured by the lines above? Numbers separated by spaces, or blank for none > ")
                captured = sorted({int(x) for x in ans.split() if x.isdigit() and 1 <= int(x) <= len(fx["maker_facts"])})
            r["grades"] = grades
            r["captured"] = captured
            save_rows(rows)
            print()
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Progress saved. Run grade again to carry on.")


def cmd_report(args):
    fixtures = load_fixtures()
    rows = [r for r in load_rows() if r["grades"] is not None]
    if not rows:
        print("Nothing graded yet.")
        return
    for label in sorted({r["label"] for r in rows}):
        rs = [r for r in rows if r["label"] == label]
        lines = sum(len(r["grades"]) for r in rs)
        supported = sum(g == "s" for r in rs for g in r["grades"])
        invented = lines - supported
        facts = sum(len(fixtures[r["fixture"]]["maker_facts"]) for r in rs)
        caught = sum(len(r["captured"]) for r in rs)
        empty_fx = [r for r in rs if not fixtures[r["fixture"]]["maker_facts"]]
        empty_ok = sum(1 for r in empty_fx if not r["lines"])
        secs = sum(r["seconds"] for r in rs) / len(rs)
        print(f"\n=== {label}  ({len(rs)} extractions graded) ===")
        print(f"  Diary lines proposed        : {lines}")
        if lines:
            print(f"  Supported (Maker said it)   : {supported}  ({100*supported/lines:.0f}%)")
            print(f"  Invented / not the Maker's  : {invented}  ({100*invented/lines:.0f}%)")
        if facts:
            print(f"  Real facts captured         : {caught} of {facts}  ({100*caught/facts:.0f}%)")
        if empty_fx:
            print(f"  Correct NONE on no-fact chats: {empty_ok} of {len(empty_fx)}")
        print(f"  Average time per extraction : {secs:.0f}s")
        print("  By conversation (invented / proposed):")
        for fid in fixtures:
            fr = [r for r in rs if r["fixture"] == fid]
            if fr:
                p = sum(len(r["grades"]) for r in fr)
                inv = sum(g == "i" for r in fr for g in r["grades"])
                print(f"    {fid:22s} {inv} / {p}")


def main():
    ap = argparse.ArgumentParser(description="Measure the diary extractor.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--label", required=True, help="e.g. before / after")
    g.add_argument("--runs", type=int, default=3)
    g.add_argument("--model", default="llama3.2:3b")
    g.add_argument("--fixtures", default="diary_fixtures.json",
                   help="which conversations file in tests/ (default: diary_fixtures.json)")
    sub.add_parser("grade")
    sub.add_parser("report")
    args = ap.parse_args()
    {"generate": cmd_generate, "grade": cmd_grade, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
