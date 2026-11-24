# Evaluation

FixSaathi's answers depend on two things that can be measured without grading free text:

1. **Retrieval.** Gemini only sees the repair records that retrieval hands it. If the right record is not among them, the answer cannot be grounded in it.
2. **The safety filter.** Every AI reply passes through a server-side rule that withholds instructions needing the power isolated, until the technician records the two safety statements. It has to catch those instructions and leave diagnosis, questions and safety reminders readable.

Both are measured by `backend/scripts/evaluate.py` against hand-labelled test sets in [`data/eval/`](../data/eval). Full output, including every miss, is in [`EVALUATION_RESULTS.json`](EVALUATION_RESULTS.json).

## What the test sets are, and are not

- **Written by the FixSaathi team**, in the way technicians describe faults: short, informal, in English, Hinglish (Hindi in Roman letters) and Hindi in Devanagari. They are not logs from real technicians: there are none yet.
- Each fault description lists every record that correctly answers it (the knowledge base has near-duplicates from different manufacturers, so several can be right).
- **Two splits.** The *development* set (60 retrieval cases, 50 safety sentences) was used to find and fix problems. The *held-out* set (30 retrieval cases, 24 safety sentences) was written after those fixes and was not used to change any code, except for one safety gap described below.
- Retrieval runs with the **keyword and error-code channels only** (PostgreSQL full-text search plus exact error-code matching), so anyone can reproduce it without an API key. Production also adds Gemini embeddings, which should help paraphrased and Hindi queries; that configuration is not measured here.
- No model output is graded. Whether Gemini writes a good answer from the right records is not measured by this script.

## Results

Retrieval returns up to 6 records. *Hit@k* is the share of queries with a correct record in the first *k*; *MRR* is the mean reciprocal rank of the first correct record.

| Set | Cases | Hit@1 | Hit@3 | Hit@6 | MRR | Appliance detected from text |
|---|---|---|---|---|---|---|
| Development, first run (before fixes) | 60 | 71.7% | 88.3% | 91.7% | 0.795 | 95.0% |
| Development, after fixes | 60 | 75.0% | 91.7% | 95.0% | 0.828 | 100% |
| **Held-out** | **30** | **83.3%** | **96.7%** | **100%** | **0.901** | **96.7%** |

Held-out by language (Hit@3): English 19/19, Hinglish 5/5, Hindi 5/6.

| Safety filter | Unsafe instructions withheld | Safe sentences shown |
|---|---|---|
| Development, first run | 24 / 25 | 25 / 25 |
| Development, after fixes | 25 / 25 | 25 / 25 |
| Held-out, first measurement | 11 / 12 | 11 / 12 |
| Held-out, after the voltage-check fix | 12 / 12 | 11 / 12 |

The retrieval numbers are the same whether the technician picks the appliance or FixSaathi detects it from the text.

## What the evaluation found, and what changed

| Finding | Change |
|---|---|
| Hindi typed in Devanagari ("एसी ठंडा नहीं कर रहा है") found no records at all by keyword, and the appliance was not detected. | Added Devanagari appliance names to appliance detection, and common Hindi symptom words to the search terms (search only; records are unchanged). Hindi: 0/2 → 2/2 on development, 5/6 on held-out. |
| "Take the regulator out of the switchboard and test it" was not withheld (the rule only matched "take it out"). | The rule now matches "take the *part* out", but still lets "take the plug / food / filter out" through. |
| Held-out: "Check the voltage across the compressor terminals" was not withheld. | Checking or testing voltage across or at live parts is now treated as live work. This is the one change made after the held-out set was written, so the held-out safety result is reported both before and after it. |

Each fix has a regression test (`tests/test_rag_ranking.py`, `tests/test_power_rules_phrasing.py`).

## Known misses

- **Retrieval, development set:** washing machine "not draining" ranks the generic drain record 5th behind brand error-code records (English) and misses it in Hinglish; "microwave switches itself off early", "turntable not rotating" and "Kent RO keeps beeping" are not in the top 3.
- **Retrieval, held-out set:** the Hindi drain query ranks the right record 5th.
- **Safety filter, false positive:** "Make sure the inlet tap is fully open" is withheld because of the word *open*. This errs on the safe side: the technician sees a note to record the safety statements, then the full text.
- **Appliance detection:** "RO se paani bahut kam aa raha hai" is not recognised as a water purifier (the bare word *RO* is not used, to avoid false matches). The technician normally picks the appliance, so retrieval still works.

## Reproduce

```bash
cd backend
createdb fixsaathi_eval
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval alembic upgrade head
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval python scripts/ingest_knowledge.py
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval python scripts/evaluate.py
```

The test sets are small (90 retrieval queries, 74 safety sentences), so one query moves Hit@3 by 1–3 points. Treat the numbers as a regression check and a fair picture of behaviour, not a benchmark result.
