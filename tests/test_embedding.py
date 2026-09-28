#!/usr/bin/env python3
"""
Checks for EmbeddingLibrary in library.py: ranking, the cache, and min_score.
No Ollama needed: a fake embedder turns text into word-count vectors, so the
checks test the plumbing, not the real model. All text here is made up.

Run from the repo root with the venv active:
    python tests/test_embedding.py
"""

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from library import (  # noqa: E402
    DOC_PREFIX, QUERY_PREFIX, EmbeddingLibrary, Passage,
)

VOCAB = ["deliver", "monday", "return", "stock", "circuit", "shed", "garden", "light"]


class FakeEmbed:
    """Word-count vectors over VOCAB. Records every text it is sent."""

    def __init__(self):
        self.sent = []

    def __call__(self, texts):
        self.sent += texts
        out = []
        for t in texts:
            w = re.findall(r"[a-z]+", t.lower())
            out.append([float(sum(x.startswith(v) for x in w)) + 0.01 for v in VOCAB])
        return out


PASSAGES = [
    Passage("supplier.md", "Deliveries", "Brightwire deliver on Mondays only."),
    Passage("supplier.md", "Returns", "Unused stock can go back within 14 days."),
    Passage("guide.md", "G 1.2 Garden work", "Lighting in a garden shed is covered."),
]


def check_finds_right_passage():
    lib = EmbeddingLibrary(PASSAGES, embed=FakeEmbed())
    top = lib.search("when do they deliver?")[0][1]
    assert top.heading == "Deliveries", top.heading


def check_scores_are_cosine():
    lib = EmbeddingLibrary(PASSAGES, embed=FakeEmbed())
    for score, _ in lib.search("garden shed lights", k=3):
        assert -1.0001 <= score <= 1.0001, score


def check_prefixes_used():
    fake = FakeEmbed()
    lib = EmbeddingLibrary(PASSAGES, embed=fake)
    lib.search("returns?")
    assert all(t.startswith(DOC_PREFIX) for t in fake.sent[:3]), fake.sent[:3]
    assert fake.sent[3] == QUERY_PREFIX + "returns?", fake.sent[3]


def check_cache_reused():
    with tempfile.TemporaryDirectory() as d:
        cache = Path(d) / "embeddings.json"
        first = EmbeddingLibrary(PASSAGES, cache_path=cache, embed=FakeEmbed())
        assert first.embed_calls == 3, first.embed_calls
        assert cache.exists()
        fake = FakeEmbed()
        second = EmbeddingLibrary(PASSAGES, cache_path=cache, embed=fake)
        assert second.embed_calls == 0 and fake.sent == [], fake.sent


def check_only_changed_passages_embedded():
    with tempfile.TemporaryDirectory() as d:
        cache = Path(d) / "embeddings.json"
        EmbeddingLibrary(PASSAGES, cache_path=cache, embed=FakeEmbed())
        edited = PASSAGES[:2] + [Passage("guide.md", "G 1.2 Garden work", "Now edited.")]
        lib = EmbeddingLibrary(edited, cache_path=cache, embed=FakeEmbed())
        assert lib.embed_calls == 1, lib.embed_calls
        assert len(json.loads(cache.read_text())) == 3  # the old text is dropped


def check_model_change_re_embeds():
    with tempfile.TemporaryDirectory() as d:
        cache = Path(d) / "embeddings.json"
        EmbeddingLibrary(PASSAGES, cache_path=cache, model="a", embed=FakeEmbed())
        lib = EmbeddingLibrary(PASSAGES, cache_path=cache, model="b", embed=FakeEmbed())
        assert lib.embed_calls == 3, lib.embed_calls


def check_broken_cache_rebuilt():
    with tempfile.TemporaryDirectory() as d:
        cache = Path(d) / "embeddings.json"
        cache.write_text("{not json")
        lib = EmbeddingLibrary(PASSAGES, cache_path=cache, embed=FakeEmbed())
        assert lib.embed_calls == 3
        json.loads(cache.read_text())


def check_min_score():
    lib = EmbeddingLibrary(PASSAGES, embed=FakeEmbed())
    everything = lib.search("deliver", k=3)
    kept = lib.search("deliver", k=3, min_score=0.5)
    assert len(kept) < len(everything), (everything, kept)
    assert all(s >= 0.5 for s, _ in kept), kept
    assert lib.search("deliver", k=3, min_score=1.01) == []


def check_empty():
    assert EmbeddingLibrary([], embed=FakeEmbed()).search("anything") == []
    assert EmbeddingLibrary(PASSAGES, embed=FakeEmbed()).search("   ") == []


CHECKS = [
    check_finds_right_passage,
    check_scores_are_cosine,
    check_prefixes_used,
    check_cache_reused,
    check_only_changed_passages_embedded,
    check_model_change_re_embeds,
    check_broken_cache_rebuilt,
    check_min_score,
    check_empty,
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
