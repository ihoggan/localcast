#!/usr/bin/env python3
"""
Checks for how chat.py uses a character's library. No Ollama needed.
Builds a throwaway character in a temporary folder; ~/bubba is not touched.

Run from the repo root with the venv active:
    python tests/test_chat_library.py
"""

import sys
import tempfile
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


CHECKS = [
    check_passages_only_in_last_message,
    check_system_prompt_same_every_turn,
    check_no_library_no_change,
    check_banter_gets_no_passages,
    check_subfolders_ignored,
    check_config_respected,
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
