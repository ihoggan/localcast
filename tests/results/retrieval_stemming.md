# Retrieval: stemming tried and rejected (28 September 2026)

Measured with `tests/retrieval_eval.py` against the Maker's 27 questions
(`tests/retrieval_questions.txt`), baseline at `fa9de4f`.

| | Keyword search (baseline) | + Snowball stemming |
|---|---|---|
| Document-worded (right section given) | 15 of 15 | 14 of 15 |
| Natural | 4 of 6 | 3 of 6 |
| Not in library (nothing given) | 2 of 6 | 2 of 6 |
| **Overall** | **21 of 27** | **19 of 27** |

Stemming made the search worse, so it was not kept.

Why:

- "replace" now matched "replacement" in AD P 2.5, but the consumer unit
  question still lost to Gary's job note (Job 3), which shares more of the
  question's words and is shorter.
- It merged words that should stay apart: "notifiable" and "non-notifiable",
  "rating" and "Rates", "supply" and "Supplier". The document-worded
  "which work is notifiable" question started getting AD P 2.7 (non-notifiable).
- Two small follow-ups (dropping stemmed stopwords such as "getting", and
  keeping "non-notifiable" as one word) changed nothing: still 19 of 27.

Conclusion: keyword matching can't tell what a question means. Changing how
words match doesn't separate "notifiable" from "non-notifiable", or a
regulations question from a question about a job. Tuning further against
these 27 questions would be tuning to the test, so we stopped and moved to
embeddings, the step agreed on 25 September if measurement showed too many
misses.
