#!/usr/bin/env python3
"""
Checks for check_diary_line(): the code that decides whether a proposed diary
line is backed by the Maker's own words. No Ollama needed.

Run from the repo root with the venv active:
    python tests/test_diary_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chat import check_diary_line  # noqa: E402

MAKER = [
    "Morning Dave. My van's a 1979 Transit, it's an embarrassment at this point.",
    "I work in IT, network technician mostly. Lot of cabling.",
    "Anyway, Tranmere lost again.",
]

CASES = [
    # (proposed line, should it be kept?, why)
    ('- Drives a 1979 Transit | "My van\'s a 1979 Transit"', True,
     "real fact, real quote"),
    ('- Works as a network technician | "network technician mostly"', True,
     "real fact, partial quote"),
    ('- Supports Tranmere | "Tranmere lost again"', True,
     "reasonable reading of a real quote"),
    ('- Drives a 1979 Transit | “My van’s a 1979 Transit”', True,
     "curly quotes and apostrophes still match"),
    ("- Drives a 1979 Transit", False,
     "no quote at all"),
    ('- Has a dog called Tyson | "my dog Tyson"', False,
     "quote the Maker never said (Dave said it)"),
    ('- Company replaces vans every 5 years | "My van\'s a 1979 Transit"', False,
     "real quote stapled to an invented fact"),
    ('- Drives a Transit | "van"', False,
     "quote too short to prove anything"),
    ('- Does a lot of cabling | "cabling"', False,
     "one-word quote proves nothing (length check)"),
]


def main():
    failures = 0
    for line, want, why in CASES:
        ok, fact, quote, reason = check_diary_line(line, MAKER)
        status = "PASS" if ok == want else "FAIL"
        if ok != want:
            failures += 1
        verdict = "kept" if ok else f"rejected ({reason})"
        print(f"{status}  {why:45s} -> {verdict}")
    print()
    if failures:
        print(f"{failures} FAILED of {len(CASES)}")
        sys.exit(1)
    print(f"ALL PASS ({len(CASES)} cases)")


if __name__ == "__main__":
    main()
