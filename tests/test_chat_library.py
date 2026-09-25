#!/usr/bin/env python3
"""
Checks for how chat.py uses a character's library. No Ollama needed.
Builds a throwaway character in a temporary folder; ~/bubba is not touched.

Run from the repo root with the venv active:
    python tests/test_chat_library.py
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chat  # noqa: E402

NOTES = """# Supplier: Brightwire

## Deliveries

Brightwire deliver on Mondays only.

## Returns

Unused stock can go back within 14 days.
"""


def make_character(base: Path, name: str, with_library: bool) -> "chat.Character":
    d = base / name
    d.mkdir()
    (d / "system.txt").write_text(f"You are {name}.")
    if with_library:
        (d / "library").mkdir()
        (d / "library" / "supplier.md").write_text(NOTES)
        (d / "library" / "originals").mkdir()
        (d / "library" / "originals" / "ignored.md").write_text("## Secret\n\nBrightwire deliver never.")
    chat.BASE = base
    return chat.Character(name)


def check_passages_only_in_last_message(base):
    c = make_character(base, "withlib", True)
    c.append_turn("user", "earlier question")
    c.append_turn("assistant", "earlier answer")
    q = "when does brightwire deliver?"
    passages = c.find_passages(q)
    assert [p.heading for p in passages] == ["Deliveries"], [p.heading for p in passages]
    msgs = c.build_messages(q, 20, passages)
    last = msgs[-1]["content"]
    assert "Brightwire deliver on Mondays only." in last, last
    assert last.endswith("THE MAKER SAYS: " + q), last
    for m in msgs[:-1]:
        assert "Mondays" not in m["content"], ("passage leaked into", m["role"])


def check_system_prompt_same_every_turn(base):
    c = make_character(base, "cache", True)
    a = c.build_messages("when does brightwire deliver?", 20, c.find_passages("when does brightwire deliver?"))
    b = c.build_messages("can stock go back?", 20, c.find_passages("can stock go back?"))
    assert a[0] == b[0], "system prompt must not change with the question"
    assert chat.LIBRARY_RULES in a[0]["content"]


def check_no_library_no_change(base):
    c = make_character(base, "plain", False)
    assert c.find_passages("when does brightwire deliver?") == []
    msgs = c.build_messages("when does brightwire deliver?", 20, c.find_passages("x"))
    assert msgs[-1]["content"] == "when does brightwire deliver?", msgs[-1]
    assert chat.LIBRARY_RULES not in msgs[0]["content"]


def check_banter_gets_no_passages(base):
    c = make_character(base, "banter", True)
    assert c.find_passages("morning, how are you?") == []
    msgs = c.build_messages("morning, how are you?", 20, [])
    assert msgs[-1]["content"] == "morning, how are you?"


def check_subfolders_ignored(base):
    c = make_character(base, "subdir", True)
    assert all(p.source == "supplier.md" for p in c.library.passages), [p.label() for p in c.library.passages]


def check_config_respected(base):
    c = make_character(base, "cfg", True)
    c.config["library_max_chars"] = 10   # smaller than any passage
    assert c.find_passages("when does brightwire deliver?") == []


def check_reminder_next_to_question(base):
    c = make_character(base, "remind", True)
    q = "when does brightwire deliver?"
    last = c.build_messages(q, 20, c.find_passages(q))[-1]["content"]
    tail = f"END OF PASSAGES.\n\n{chat.PASSAGE_REMINDER}\n\nTHE MAKER SAYS: {q}"
    assert last.endswith(tail), last[-300:]
    # No passages, no reminder: banter stays plain.
    assert chat.PASSAGE_REMINDER not in c.build_messages("morning", 20, [])[-1]["content"]


def check_date_line(base):
    fixed = datetime(2027, 3, 2, 9, 0)   # not today, so the real clock can't pass by luck
    c = make_character(base, "dated", True)
    assert "Today is Tuesday 2 March 2027." in c.build_system(fixed), c.build_system(fixed)[-80:]
    msgs = c.build_messages("hello", 20, [], today=fixed)
    assert "Today is Tuesday 2 March 2027." in msgs[0]["content"]
    p = make_character(base, "undated", False)
    assert "Today is" not in p.build_system(fixed), "no library, no change: no date line"


def check_default_cutoff_is_0_4(base):
    c = make_character(base, "cutoff", True)
    seen = {}
    real = chat.pick_passages
    def spy(results, **kw):
        seen.update(kw)
        return real(results, **kw)
    chat.pick_passages = spy
    try:
        c.find_passages("when does brightwire deliver?")
    finally:
        chat.pick_passages = real
    assert seen.get("relative") == 0.4, seen


CHECKS = [
    check_passages_only_in_last_message,
    check_system_prompt_same_every_turn,
    check_no_library_no_change,
    check_banter_gets_no_passages,
    check_subfolders_ignored,
    check_config_respected,
    check_reminder_next_to_question,
    check_date_line,
    check_default_cutoff_is_0_4,
]


def main():
    failures = 0
    for check in CHECKS:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                check(Path(tmp))
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
