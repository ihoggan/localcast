#!/usr/bin/env python3
"""
library.py — a character's reference library, searched by keyword.

A library is a folder of .md and .txt files (e.g. ~/bubba/dave/library/).
Only files directly inside the folder are read; subfolders such as
originals/ are ignored.

  split_passages()  cuts one file into short passages, each with a heading
                    so the source can be named.
  Library           ranks passages against a question with BM25 (the standard
                    keyword-ranking method), in plain Python.
  pick_passages()   keeps the best few, under a hard character cap, so the
                    context window can't overflow.

Try it from the repo root:
    python library.py ~/bubba/dave/library "new cooker circuit"
"""

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Longest passage before a section is split into parts (characters).
MAX_PASSAGE_CHARS = 800

# Words too common to tell passages apart.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "do", "does", "for", "from", "had", "has", "have", "he", "her",
    "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "just",
    "me", "my", "no", "not", "of", "on", "or", "our", "out", "she", "should",
    "so", "some", "that", "the", "their", "them", "then", "there", "they",
    "this", "to", "up", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "you", "your", "dave",
    "maker", "mate", "pal", "ok", "okay", "yeah", "aye", "right", "any",
    "about", "all", "also", "than", "too", "very", "got", "get", "need",
    "needs", "did", "done", "one", "tell", "know",
    # everyday chat, so banter doesn't pull in passages
    "go", "going", "gone", "come", "see", "say", "said", "think", "well",
    "good", "morning", "afternoon", "evening", "hello", "hiya", "hi",
    "alright", "cheers", "thanks", "ta", "now", "still", "here", "again",
    "bit", "lot", "thing", "things", "way", "today",
}

_BRACKET_NOTE = re.compile(r"^\s*\[.*\]\s*$")


@dataclass
class Passage:
    source: str    # file name, e.g. "supplier.md"
    heading: str   # e.g. "AD P 2.5 Notifiable work" or "Deliveries"
    text: str      # the passage itself

    def label(self) -> str:
        """What gets printed so the Maker can check the source."""
        return f"{self.source}: {self.heading}"


# ---------- Splitting ----------

def _has_body(lines) -> bool:
    """True if there is real text, not just blank lines and [editor notes]."""
    return any(l.strip() and not _BRACKET_NOTE.match(l) for l in lines)


def _cut(lines, max_chars):
    """Group lines into pieces no longer than max_chars, breaking only
    between lines. A single line longer than max_chars becomes its own piece."""
    pieces, cur, size = [], [], 0
    for line in lines:
        extra = len(line) + (1 if cur else 0)
        if cur and size + extra > max_chars:
            pieces.append(cur)
            cur, size = [], 0
            extra = len(line)
        cur.append(line)
        size += extra
    if cur:
        pieces.append(cur)
    return pieces


def _make(source, heading, lines, max_chars):
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not _has_body(lines):
        return []
    lines = [l for l in lines if l.strip()]
    pieces = _cut(lines, max_chars)
    out = []
    for n, piece in enumerate(pieces, 1):
        h = heading if len(pieces) == 1 else f"{heading} (part {n} of {len(pieces)})"
        out.append(Passage(source, h, "\n".join(piece)))
    return out


def split_passages(text: str, source: str, max_chars: int = MAX_PASSAGE_CHARS):
    """Cut one file into passages.

    Markdown (.md): one passage per '## ' section. Text before the first
    '## ' is a passage too, headed by the '# ' title, if it has real text.
    Plain text (.txt): one passage per block separated by blank lines.
    Anything longer than max_chars is split into parts at line breaks, and
    every part keeps its section's heading.
    """
    lines = text.replace("\f", "").split("\n")
    passages = []
    if source.endswith(".md"):
        title = Path(source).stem
        heading, cur = None, []
        for line in lines:
            if line.startswith("## "):
                passages += _make(source, heading or title, cur, max_chars)
                heading, cur = line[3:].strip(), []
            elif line.startswith("# ") and heading is None and not cur:
                title = line[2:].strip()
            else:
                cur.append(line)
        passages += _make(source, heading or title, cur, max_chars)
    else:
        block = []
        for line in lines + [""]:
            if line.strip():
                block.append(line)
            elif block:
                passages += _make(source, Path(source).stem, block, max_chars)
                block = []
    return passages


def load_library(folder, max_chars: int = MAX_PASSAGE_CHARS):
    """Every passage from every .md and .txt file directly in folder."""
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        return []
    passages = []
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix in (".md", ".txt"):
            passages += split_passages(f.read_text(errors="replace"), f.name, max_chars)
    return passages


# ---------- Searching ----------

def words(text: str):
    """Lower-case keywords, stopwords removed, a plain 's' plural trimmed
    ('circuits' matches 'circuit')."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower().replace("’", "'")):
        if w in STOPWORDS or len(w) < 2:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class Library:
    """BM25 keyword search over a list of passages.

    Each word in the question scores a passage by how often it appears
    there, weighted by how rare the word is across the whole library, so
    'kettleworth' counts for far more than 'work'. The heading is searched
    along with the text.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self, passages):
        self.passages = list(passages)
        self.docs = [words(p.heading + "\n" + p.text) for p in self.passages]
        self.avg_len = (sum(len(d) for d in self.docs) / len(self.docs)) if self.docs else 0
        df = {}
        for d in self.docs:
            for w in set(d):
                df[w] = df.get(w, 0) + 1
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def search(self, question: str, k: int = 3, min_score: float = 0.0):
        """Best k passages as (score, passage), highest first. Passages that
        share no keyword with the question, or score below min_score, are
        never returned."""
        q = set(words(question))
        if not q or not self.docs:
            return []
        scored = []
        for p, d in zip(self.passages, self.docs):
            tf = {}
            for w in d:
                if w in q:
                    tf[w] = tf.get(w, 0) + 1
            if not tf:
                continue
            norm = self.K1 * (1 - self.B + self.B * len(d) / self.avg_len)
            score = sum(
                self.idf[w] * c * (self.K1 + 1) / (c + norm) for w, c in tf.items()
            )
            if score >= min_score:
                scored.append((score, p))
        scored.sort(key=lambda sp: -sp[0])
        return scored[:k]


def pick_passages(results, max_chars: int = 2000, relative: float = 0.5):
    """Keep results in rank order, leaving out:
      - any passage scoring under `relative` x the top score (weak matches
        that would only pad out the space), and
      - any passage that would take the total over max_chars. A passage is
        never cut short; it is left out whole, and a smaller lower-ranked
        one may still fit."""
    if not results:
        return []
    floor = results[0][0] * relative
    kept, total = [], 0
    for score, p in results:
        if score < floor:
            continue
        size = len(p.heading) + len(p.text)
        if total + size > max_chars:
            continue
        kept.append((score, p))
        total += size
    return kept


# ---------- Try it by hand ----------

def main():
    if len(sys.argv) < 3:
        sys.exit('Usage: python library.py <library folder> "question"')
    folder, question = sys.argv[1], " ".join(sys.argv[2:])
    passages = load_library(folder)
    lib = Library(passages)
    print(f"{len(passages)} passages in {folder}")
    print(f"Keywords: {' '.join(sorted(set(words(question)))) or '(none)'}\n")
    results = lib.search(question, k=5)
    if not results:
        print("No passage shares a keyword with that question.")
    for score, p in results:
        print(f"{score:6.2f}  {p.label()}")
    picked = pick_passages(results[:3])
    print(f"\nDave would be given: {', '.join(p.label() for _, p in picked) or 'nothing'}")


if __name__ == "__main__":
    main()
