# Evaluation

FixSaathi's answers depend on two things that can be measured without grading free text:

1. **Retrieval.** Gemini only sees the repair records that retrieval hands it. If the right record is not among them, the answer cannot be grounded in it.
2. **The safety filter.** Every AI reply passes through a server-side rule that withholds instructions needing the power isolated, until the technician records the two safety statements. It has to catch those instructions and leave diagnosis, questions and safety reminders readable.

Both are measured by `backend/scripts/evaluate.py` against hand-labelled test sets in [`data/eval/`](../data/eval). Full output, including every miss, is in [`EVALUATION_RESULTS.json`](EVALUATION_RESULTS.json).

## What the test sets are, and are not

- **Written by the FixSaathi team**, in the way technicians describe faults: short, informal, in English, Hinglish (Hindi in Roman letters) and Hindi in Devanagari. They are not logs from real technicians: there are none yet.
- Each fault description lists every record that correctly answers it (the knowledge base has near-duplicates from different manufacturers, so several can be right).
- **Three splits.** The *development* set (60 retrieval cases, 50 safety sentences) was used to find and fix problems. The *held-out* set (30 retrieval cases, 24 safety sentences) was written after the first round of fixes. It was used to change code twice, both described below, and the results before and after each change are given. *Held-out v2* (36 retrieval cases, [`retrieval_holdout_v2.jsonl`](../data/eval/retrieval_holdout_v2.jsonl)) was written before the field-weighted ranking was run on it. It was used once, to compare the old and new ranking, and not to tune anything.
- Retrieval runs with the **keyword and error-code channels only** (PostgreSQL full-text search plus exact error-code matching), so anyone can reproduce it without an API key. Production also adds Gemini embeddings, which should help paraphrased and Hindi queries; that configuration is not measured here.
- No model output is graded. Whether Gemini writes a good answer from the right records is not measured by this script.

## Results

Retrieval returns up to 6 records. *Hit@k* is the share of queries with a correct record in the first *k*; *MRR* is the mean reciprocal rank of the first correct record.

| Set | Ranking | Cases | Hit@1 | Hit@3 | Hit@6 | MRR |
|---|---|---|---|---|---|---|
| Development | first run, before any fix | 60 | 71.7% | 88.3% | 91.7% | 0.795 |
| Development | term-frequency `ts_rank` (v1.0) | 60 | 75.0% | 91.7% | 95.0% | 0.828 |
| Development | field-weighted (current) | 60 | 95.0% | 100% | 100% | 0.972 |
| Held-out | v1.0 | 30 | 83.3% | 96.7% | 100% | 0.901 |
| Held-out | field-weighted, first measurement | 30 | 83.3% | 96.7% | 96.7% | 0.894 |
| Held-out | field-weighted + *hil* fix (current) | 30 | 86.7% | 100% | 100% | 0.928 |
| **Held-out v2** | **v1.0** | **36** | **88.9%** | **94.4%** | **97.2%** | **0.914** |
| **Held-out v2** | **field-weighted (current)** | **36** | **94.4%** | **94.4%** | **100%** | **0.958** |

**Read the development row with care: the field-weighted ranking was built against those 60 queries.** The fair comparison is held-out v2, which neither version was tuned on: the correct record moves to first place more often (Hit@1 88.9% → 94.4%, MRR 0.914 → 0.958), and Hit@3 is unchanged. On the original held-out set the new ranking first scored slightly lower (MRR 0.901 → 0.894). Its one miss, "pankha hil raha hai bahut zyada", exposed a vocabulary gap: *hil* (shaking) was mapped to *vibration*, a word no fan record uses. It now also maps to *wobbling* and *shaking*. That fix was made after seeing a held-out query, so the current held-out figures are no longer an untouched result.

Appliance detected from text: development 100%, held-out 96.7%, held-out v2 97.2%. Current Hit@3 by language: held-out English 19/19, Hinglish 5/5, Hindi 6/6; held-out v2 English 28/30, Hinglish 5/5, Hindi 1/1.

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
| Held-out: "Check the voltage across the compressor terminals" was not withheld. | Checking or testing voltage across or at live parts is now treated as live work. This change was made after the held-out set was written, so the held-out safety result is reported both before and after it. |
| Development: long error-code records outranked the record about the symptom ("not draining" put the generic drain record 5th behind five code records); "Kent RO keeps beeping" was decided by *RO*, which every Kent record contains; "plate not rotating" found no turntable record. | Field-weighted keyword scoring (symptoms > faults > other text, words weighted by rarity), a small weight against code records when no code was given, and everyday-English synonyms. See `RAG_PIPELINE.md`. Development Hit@1 75.0% → 95.0%; held-out v2 Hit@1 88.9% → 94.4%. |

Each fix has a regression test (`tests/test_rag_ranking.py`, `tests/test_power_rules_phrasing.py`).

## Known misses

- **Retrieval, held-out v2:** "microwave light inside does not come on" and "microwave takes much longer than before to heat food" rank the right record 4th.
- **Retrieval, development set:** no query outside the top 3; "fan works on speed 1 and 2 but not on higher speeds", "microwave display is on but it will not start" and "RO purifier not giving any water" rank it 2nd or 3rd.
- **Safety filter, false positive:** "Make sure the inlet tap is fully open" is withheld because of the word *open*. This errs on the safe side: the technician sees a note to record the safety statements, then the full text.
- **Appliance detection:** "RO se paani bahut kam aa raha hai" is not recognised as a water purifier (the bare word *RO* is not used, to avoid false matches), nor "water dripping from the indoor unit onto the wall" as an AC. The technician normally picks the appliance, so retrieval still works.

## Reproduce

```bash
cd backend
createdb fixsaathi_eval
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval alembic upgrade head
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval python scripts/ingest_knowledge.py
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_eval python scripts/evaluate.py
```

The test sets are small (126 retrieval queries, 74 safety sentences), so one query moves Hit@3 by 1–3 points. Treat the numbers as a regression check and a fair picture of behaviour, not a benchmark result.
