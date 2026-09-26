# Level 4: Dave's reference library, results

Measured 25 September 2026. Commits: build `551ceff`, rubric `04d5396`, grades `9a5c69d`.

## Setup

- 16 questions: 5 about the notes, 5 about AD P, 3 needing both, and 3 the library can't answer. Answers were written before any runs.
- Each question was asked 3 times with the library and 3 times without, each time fresh with no history. That's 96 replies.
- Model: llama3.2:3b on nix6.
- Grading: Claude graded all 96 blind (with/without hidden). Iain spot-checked 11, also blind. We agreed on 7 of 11 answers, and the disagreements went both ways. Iain's source grades aren't used, because the rubric was misread; the wording has since been clarified.

## Result

| | With library | Without |
|---|---|---|
| Notes questions correct | 15 of 15 | 0 of 15 |
| AD P questions correct | 12 of 15 | 6 of 15 |
| Both questions correct | 7 of 9 | 3 of 9 |
| **All answerable questions** | **34 of 39** | **9 of 39** |
| Not in library: declined (right) | 9 of 9 | 3 of 9 |
| Not in library: made something up | 0 of 9 | 6 of 9 |

**The library works.** The notes can't be known without it, and there it's everything to nothing. On regulations it roughly doubles his hit rate. The rule about only using the shelf also stopped him making things up.

**Cost:** 16.9 s per reply against 12.5 s, and a prompt of 1,040 tokens against 614 (max 1,270 of 4,096).

## What still goes wrong

- **Search misses become confident wrong answers.** "Replacing" doesn't match "replacement", so AD P 2.5 wasn't found for P1. Dave then cited 2.8 and got the answer backwards. That was 2 of the 3 P1 runs (R18, R54). It's the worst failure mode: wrong, but it sounds sourced.
- **Named sources are still unreliable.** With the library, 14 of the 39 answerable replies named a real source correctly and 9 named one wrongly. Several of the wrong ones were right answers with the wrong paragraph attached; the cutoff had dropped AD P on B2 and B3.
- **Remaining misses:** P2 run 1, and B1 runs 2 and 3.

## Caveats

- The notes are made up and written by the builder, as are the questions.
- It's one small model, and one main grader, who also built the thing.
- Dave is for banter and pointers, never the authority on regs.

## Worth doing next (optional)

1. **Word forms in search:** a simple stemmer, so "replacing" matches "replacement".
2. **The cutoff:** don't let a high-scoring job note push AD P out when the question is about notification.
3. Check both against a fresh set of questions, not these 16, so the fix isn't tuned to the test.
