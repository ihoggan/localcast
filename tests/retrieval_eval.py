#!/usr/bin/env python3
"""
retrieval_eval.py — does the library search find the right passage?

No Ollama and no grading: this checks the search on its own, against the
Maker's question set in tests/retrieval_questions.txt. Each question names
the section(s) that answer it (EXPECT), or `none` if the library can't.

Run from the repo root with the venv active:

  python tests/retrieval_eval.py                  # summary + every miss
  python tests/retrieval_eval.py --all            # every question, not just misses
  python tests/retrieval_eval.py --library PATH   # a different library folder

For each answerable question it reports:
  found   an expected section is in the top 3 search results
  given   an expected section survives pick_passages(), so the character
          actually sees it (the same search, cap and cutoff as a real chat)
  first   the top result is an expected section
  cut     found but not given: the 0.4 cutoff (or the size cap) dropped it
For `none` questions:
  clean   nothing at all is given to the character

Results are grouped by the ## sections of the question file.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from library import Library, load_library, pick_passages  # noqa: E402

QUESTIONS = HERE / "retrieval_questions.txt"
DEFAULT_LIBRARY = Path("~/bubba/dave/library").expanduser()
_PART = re.compile(r"\s*\(part \d+ of \d+\)$")


def base_heading(heading):
    """'AD P 1.4 New dwellings (part 2 of 3)' -> 'AD P 1.4 New dwellings'"""
    return _PART.sub("", heading)


def load_questions(path):
    """Parse the question file into a list of dicts:
    {group, q, expect: [section, ...]}, where expect == [] means 'none'."""
    questions, group, cur = [], "(no group)", None
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if line.startswith("## "):
            group = line[3:].strip()
        elif line.startswith("Q:"):
            cur = {"group": group, "q": line[2:].strip(), "expect": [], "none": False, "line": n}
            questions.append(cur)
        elif line.startswith("EXPECT:"):
            if cur is None:
                sys.exit(f"Line {n}: EXPECT before any Q:")
            value = line[7:].strip()
            if value.lower() == "none":
                cur["none"] = True
            elif value:
                cur["expect"].append(value)
    for q in questions:
        if not q["q"]:
            sys.exit(f"Line {q['line']}: empty question")
        if q["none"] and q["expect"]:
            sys.exit(f"Line {q['line']}: EXPECT none and a section on the same question")
        if not q["none"] and not q["expect"]:
            sys.exit(f"Line {q['line']}: no EXPECT (write a section heading, or none)")
    return questions


def matches(expect, passage):
    """An EXPECT line matches a passage by heading ('AD P 2.5 Notifiable work')
    or by file and heading ('supplier.md: Deliveries'). Any part counts."""
    heading = base_heading(passage.heading)
    return expect == heading or expect == f"{passage.source}: {heading}"


def check_expects(questions, passages):
    """Every EXPECT must name a real section, or the test is meaningless."""
    bad = []
    for q in questions:
        for e in q["expect"]:
            if not any(matches(e, p) for p in passages):
                bad.append(f"  line {q['line']}: {e}")
    if bad:
        sys.exit("These EXPECT lines don't match any section in the library:\n" + "\n".join(bad))


def chat_settings():
    """The same search settings a real chat with Dave uses."""
    settings = {"library_passages": 3, "library_max_chars": 2000, "library_relative": 0.4}
    cfg = Path("~/bubba/dave/config.json").expanduser()
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            settings.update({k: data[k] for k in settings if k in data})
        except (ValueError, OSError):
            pass
    return settings


def run(questions, lib, settings):
    rows = []
    for q in questions:
        results = lib.search(q["q"], k=settings["library_passages"])
        picked = pick_passages(
            results,
            max_chars=settings["library_max_chars"],
            relative=settings["library_relative"],
        )
        hit = lambda p: any(matches(e, p) for e in q["expect"])  # noqa: E731
        row = {
            "q": q, "results": results, "picked": picked,
            "found": any(hit(p) for _, p in results),
            "given": any(hit(p) for _, p in picked),
            "first": bool(results) and hit(results[0][1]),
            "clean": not picked,
        }
        row["cut"] = row["found"] and not row["given"]
        row["ok"] = row["clean"] if q["none"] else row["given"]
        rows.append(row)
    return rows


def show(row):
    q = row["q"]
    mark = "ok  " if row["ok"] else "MISS"
    print(f"\n[{mark}] {q['q']}")
    print(f"       expect: {'none' if q['none'] else ' | '.join(q['expect'])}")
    picked_ids = {id(p) for _, p in row["picked"]}
    if not row["results"]:
        print("       (no passage shares a keyword)")
    for score, p in row["results"]:
        tag = "given" if id(p) in picked_ids else "cut  "
        print(f"       {score:6.2f} {tag} {p.label()}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="show every question, not just misses")
    ap.add_argument("--library", default=str(DEFAULT_LIBRARY), help="library folder")
    ap.add_argument("--questions", default=str(QUESTIONS), help="question file")
    args = ap.parse_args()

    passages = load_library(args.library)
    if not passages:
        sys.exit(f"No passages found in {args.library}")
    questions = load_questions(Path(args.questions))
    check_expects(questions, passages)
    settings = chat_settings()
    rows = run(questions, Library(passages), settings)

    print(f"{len(questions)} questions, {len(passages)} passages, settings {settings}")
    for row in rows:
        if args.all or not row["ok"]:
            show(row)

    print("\n" + "=" * 72)
    groups = list(dict.fromkeys(r["q"]["group"] for r in rows))
    for g in groups:
        rs = [r for r in rows if r["q"]["group"] == g]
        ans = [r for r in rs if not r["q"]["none"]]
        non = [r for r in rs if r["q"]["none"]]
        print(f"\n{g}  ({len(rs)} questions)")
        if ans:
            n = len(ans)
            print(f"  given (Dave sees the right section)   {sum(r['given'] for r in ans):2d} of {n}")
            print(f"  found in top 3                        {sum(r['found'] for r in ans):2d} of {n}")
            print(f"  right section ranked first            {sum(r['first'] for r in ans):2d} of {n}")
            print(f"  found but cut by the cutoff or cap    {sum(r['cut'] for r in ans):2d} of {n}")
        if non:
            print(f"  clean (nothing given)                 {sum(r['clean'] for r in non):2d} of {len(non)}")

    ok = sum(r["ok"] for r in rows)
    print(f"\nOverall: {ok} of {len(rows)} right")


if __name__ == "__main__":
    main()
