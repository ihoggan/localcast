#!/usr/bin/env python3
"""
Checks for library.py: splitting files into passages, keyword search, and the
size cap. No Ollama needed. All text here is made up for the test.

Run from the repo root with the venv active:
    python tests/test_library.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from library import Library, Passage, pick_passages, split_passages, words  # noqa: E402

NOTES = """# Supplier: Brightwire

Our wholesaler is Brightwire, account BW-100.

## Deliveries

Brightwire deliver on Mondays only.

## Returns

Unused stock can go back within 14 days.
"""

GUIDE = """# Made-up Guide

[Source: invented for this test.]

## G 1.1 Circuits

1.1 Adding a new circuit must be reported to the inspector.

## G 1.2 Garden work

1.2 Lighting in a garden shed is covered by this guide.

[Diagram 1 is a picture and is not included.]

## G 1.3 Long rules
""" + "\n".join(f"Rule line {n}: every tester should be checked each year." for n in range(1, 31)) + "\n"

PLAIN = """First block about ladders.

Second block about the van
and its MOT.
"""


def by_heading(passages, heading):
    return [p for p in passages if p.heading.startswith(heading)]


def check_split_notes():
    ps = split_passages(NOTES, "supplier.md")
    heads = [p.heading for p in ps]
    assert heads == ["Supplier: Brightwire", "Deliveries", "Returns"], heads
    assert "BW-100" in ps[0].text, "text before the first ## is a passage too"
    assert ps[1].text == "Brightwire deliver on Mondays only.", repr(ps[1].text)


def check_bracket_only_preamble_skipped():
    ps = split_passages(GUIDE, "guide.md")
    assert not by_heading(ps, "Made-up Guide"), "a preamble that is only an [editor note] is not a passage"
    garden = by_heading(ps, "G 1.2")[0]
    assert "[Diagram 1" in garden.text, "an editor note inside a section is kept"


def check_long_section_split():
    ps = by_heading(split_passages(GUIDE, "guide.md", max_chars=400), "G 1.3")
    assert len(ps) > 1, "a long section is split into parts"
    for p in ps:
        assert len(p.text) <= 400, len(p.text)
        assert p.heading.startswith("G 1.3 Long rules (part "), p.heading
    rejoined = "\n".join(p.text for p in ps)
    original = "\n".join(f"Rule line {n}: every tester should be checked each year." for n in range(1, 31))
    assert rejoined == original, "splitting must not lose or change any text"


def check_split_plain_text():
    ps = split_passages(PLAIN, "misc.txt")
    assert len(ps) == 2, len(ps)
    assert ps[1].text == "Second block about the van\nand its MOT.", repr(ps[1].text)
    assert all(p.heading == "misc" for p in ps)


def library():
    return Library(split_passages(NOTES, "supplier.md") + split_passages(GUIDE, "guide.md"))


def top(question):
    res = library().search(question, k=3)
    return res[0][1].heading if res else None


def check_finds_right_passage():
    assert top("when does brightwire deliver?") == "Deliveries", top("when does brightwire deliver?")
    assert top("can I take stock back?") == "Returns", top("can I take stock back?")
    assert top("wiring a shed in the garden") == "G 1.2 Garden work", top("wiring a shed in the garden")


def check_plural_matches_singular():
    assert top("new circuits") == "G 1.1 Circuits", top("new circuits")


def check_rare_word_beats_common_word():
    # "every" appears many times in every long-rules part; "wholesaler" once, in one passage.
    assert top("wholesaler every") == "Supplier: Brightwire", top("wholesaler every")


def check_banter_finds_nothing():
    lib = library()
    for q in ["morning dave, how are you?", "aye go on then", "alright, cheers mate",
              "", "the and of"]:
        assert lib.search(q) == [], (q, lib.search(q))


def check_unrelated_question_finds_nothing():
    # Real keywords, but none of them are in the library.
    assert library().search("who won the football?") == [], library().search("who won the football?")


def check_heading_is_searched():
    # "returns" appears only in the heading "## Returns", not in its text.
    assert top("returns") == "Returns", top("returns")


def check_min_score():
    lib = library()
    all_hits = lib.search("brightwire", k=10)
    assert all_hits, "brightwire should match"
    best = all_hits[0][0]
    assert lib.search("brightwire", k=10, min_score=best + 0.01) == []


def check_empty_library():
    assert Library([]).search("anything") == []


def check_cap_never_cuts_and_never_overflows():
    a = Passage("x.md", "A", "a" * 900)
    b = Passage("x.md", "B", "b" * 900)
    c = Passage("x.md", "C", "c" * 900)
    d = Passage("x.md", "D", "d" * 50)
    kept = pick_passages([(3.0, a), (2.0, b), (1.5, c), (1.0, d)], max_chars=2000, relative=0)
    names = [p.heading for _, p in kept]
    assert names == ["A", "B", "D"], names
    total = sum(len(p.heading) + len(p.text) for _, p in kept)
    assert total <= 2000, total
    assert all(len(p.text) in (900, 50) for _, p in kept), "passages are whole, never trimmed"


def check_weak_matches_dropped():
    a = Passage("x.md", "A", "a")
    b = Passage("x.md", "B", "b")
    c = Passage("x.md", "C", "c")
    kept = pick_passages([(10.0, a), (6.0, b), (4.9, c)], relative=0.5)
    assert [p.heading for _, p in kept] == ["A", "B"], [p.heading for _, p in kept]
    assert pick_passages([]) == []


def check_words():
    assert words("The Circuits, and a SHED!") == ["circuit", "shed"], words("The Circuits, and a SHED!")
    assert words("glass") == ["glass"], "don't trim -ss words"


CHECKS = [
    check_split_notes,
    check_bracket_only_preamble_skipped,
    check_long_section_split,
    check_split_plain_text,
    check_finds_right_passage,
    check_plural_matches_singular,
    check_rare_word_beats_common_word,
    check_banter_finds_nothing,
    check_unrelated_question_finds_nothing,
    check_heading_is_searched,
    check_min_score,
    check_empty_library,
    check_cap_never_cuts_and_never_overflows,
    check_weak_matches_dropped,
    check_words,
]


def main():
    failures = 0
    for check in CHECKS:
        try:
            check()
            print(f"PASS  {check.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {check.__name__}: {e}")
    print()
    if failures:
        print(f"{failures} FAILED of {len(CHECKS)}")
        sys.exit(1)
    print(f"ALL PASS ({len(CHECKS)} checks)")


if __name__ == "__main__":
    main()
