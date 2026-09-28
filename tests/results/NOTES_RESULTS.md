# Search fix: results (28 September 2026)

Known problem #1 from Level 4: when the search missed the right passage, Dave
answered confidently and wrongly (the consumer unit question, P1, got it
backwards in 2 of 3 runs). This is what we tried, measured on the search alone
(`tests/retrieval_eval.py`, no model, no grading).

## The test

- **Original set** (`tests/retrieval_questions.txt`, 27 questions): 15 worded
  like the document, 6 natural (the way you'd ask Dave), 6 not in the library.
- **Fresh set** (`tests/retrieval_questions_2.txt`, 10 questions): written by
  Iain before he saw the notes. 2 answerable, 8 not in the library.
- EXPECT lines name the section(s) that answer each question. "Given" means
  the right section is among the passages Dave actually receives.

## What we tried

| | Original set | Natural (of 6) | Fresh set answerable (of 2) |
|---|---|---|---|
| Keyword search (as shipped) | 21 of 27 | 4 | 0 |
| + Snowball stemming | 19 of 27 | 3 | — |
| Embeddings (nomic-embed-text) | 19 of 27 | 4 | 0 |
| Keyword + plain-English notes | **23 of 27** | **6** | **2** |
| Embeddings + plain-English notes | **21 of 27** | **6** | **2** |

Document-worded questions: 15 of 15 in every run except stemming (14).
The not-in-library questions got passages in almost every run; see below.

## What we learned

1. **Stemming made things worse.** It merged words that must stay apart:
   "notifiable" and "non-notifiable", "rating" and "Rates". Rejected
   (`retrieval_stemming.md`).
2. **Embeddings missed the same two natural questions as keywords.** Searching
   by meaning didn't help, because the document itself is the problem:
   - AD P 2.7 says "additions and alterations to existing installations outside
     special locations" and never mentions sockets or rooms.
   - AD P 2.5 lists "the replacement of a consumer unit" in legal wording, while
     2.7 says "replacements … anywhere" are *not* notifiable. That is very
     likely how Dave got P1 backwards.
3. **Plain-English notes fixed it, with either search method.**
   `part-p-in-plain-words.md` puts common jobs in everyday words, each pointing to
   its AD P section, and warns about the 2.7 "replacements" trap. With the notes,
   all 6 natural questions and both fresh answerable ones get the right
   section. The notes were drafted and their md5 locked (`8c404085…`) before
   the fresh questions were read.
4. **Keyword and embeddings tie once the notes are in.** Keyword search stays:
   no extra model, instant. The embedding code stays in `library.py` as an
   unused option.
5. **A score cutoff can't filter off-topic questions.** With embeddings, "kettle
   trips the circuit" (off-topic) scored 0.669 and "pop up to Runcorn"
   (answerable) scored 0.597, so no cutoff separates them. Declining stays
   Dave's job; in Level 4 he declined 9 of 9 not-in-library questions.
6. **Most natural questions were about faults.** Four of Iain's six fresh
   questions (a tripping kettle, a melting socket, an overloaded plug, the
   supply voltage) are fault-finding. AD P covers rules and paperwork, not
   diagnosis, so the library has nothing on them. That's a scope question for
   later.

## Scoring note

After the notes were added, the three original natural questions they answer
got an extra EXPECT line naming the notes section (socket, consumer unit, third
party). Without that, a right answer from the notes counted as a miss. The
without-notes runs are unaffected: EXPECT lines naming a file that isn't in the
library are skipped.

Raw output: `tests/results/notes/`.

## Reply check: does Dave now answer the right way round?

`tests/reply_check.py`, llama3.2:3b, library with notes, 3 fresh runs each.
Read by eye, not blind-graded: a quick look, not a measurement.

| Question | Right answer | Level 4 | With notes |
|---|---|---|---|
| P1 Is replacing a consumer unit notifiable? | Yes | 1 of 3 | **3 of 3** |
| B2 Gary's fuse box swap, does it need notifying? | Yes | right way round, but cited made-up sections | 2 of 3 |
| P4 Is replacing a broken light switch notifiable? | No | not graded | 2 of 3 |

- P1, the Level 4 failure, is fixed in all three runs, citing AD P 2.5.
- The two wrong replies had the right passages in front of them and
  contradicted them: B2 run 2 said "not notifiable" after being given two
  sections saying it is, and P4 run 1 said "notifiable" while quoting the
  line that says it isn't. That's the 3B model, not the search.
- P4 was the check for over-correction (the notes making everything sound
  notifiable). One run of three went that way.

Raw output: `tests/results/reply_check_notes.txt`.
