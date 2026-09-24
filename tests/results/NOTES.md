# Diary extractor evaluation, 2026-09-24

What was measured: the lines the end-of-session diary extractor proposes, over
5 scripted conversations (`tests/diary_fixtures.json`) x 3 runs, before and
after the fix in commit b743db9. Model: llama3.2:3b on nix6 (i5-6500, CPU only).
Raw outputs and grades: `diary_eval.jsonl`.

## Results

| | Before | After |
|---|---|---|
| Diary lines proposed | 35 | 22 |
| Invented / not the Maker's (rubric grading) | 35 of 35 (100%) | 10 of 22 (45%) |
| General-knowledge filler lines (e.g. "The M56 is a major motorway in the UK") | 19 | 0 |
| Correct NONE on the 2 conversations with no Maker facts (6 runs) | 0 of 6 | 4 of 6 |
| Real Maker facts captured (rubric grading) | 0 of 18 | 9 of 18 |

What the 35 "before" lines were: 19 general-knowledge filler, 7 details of
Dave's invented Wrexham job, 3 versions of the invented "company van policy"
pinned on the Maker, and 6 invented traits of the Maker drawn from small talk
("The Maker is capable of performing electrical work").

Correction: the filler count was first published here as 14. It was a
miscount; recounted line by line from `diary_eval.jsonl`, it is 19.

"Real Maker facts" excludes van-joke fact 2, which was wrong in the fixture file:
it says the Maker wants rid of the van, but in the conversation he says he'll keep
it. 18 = the 6 remaining facts x 3 runs.

## Grading: two graders, and why they differ

Grading was blind. Before and after outputs were shuffled with their labels hidden.

- **Rubric grading (Claude, blind to labels):** a line is *supported* if it is a
  fact the Maker in that conversation stated about himself or his life
  (paraphrase allowed). Anything else is *invented*: world knowledge, facts about
  Dave or his customers, over-inference, and non-facts like "Speak later".
- **Iain's grading** (stored in `diary_eval.jsonl`): the prompt said
  "s = Maker said it", which Iain read as "am I sure *I* said this". The fixtures
  are scripted, not his own words, so correct lines such as "Lives on the Wirral"
  were marked invented. By that reading: before 34/35 invented, after 17/22.

Both gradings agree on the main point: before the fix, virtually everything was
invented. The instruction in the grader was ambiguous. That is a lesson for next
time, not a reason to discard either set.

## Known limits after the fix

- Trivia gets copied as "facts" ("Raining again here", "She was fine, just
  expensive"). The quote check proves the Maker said something, not that it's
  worth remembering.
- Meaning gets misread: "I'll get it signed off" (the garage wiring) became
  "Signed off for work".
- Recall is still poor: "works as a network technician" and "has a dog called
  Bess" were never captured.
- The five conversations were written by the same person as the fix. Real use is
  the next test.

The review step now shows the Maker's own words beside every line and has no
default, so these are easy to spot and discard.
