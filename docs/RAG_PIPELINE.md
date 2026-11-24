# Retrieval-augmented diagnosis

FixSaathi uses Google Gemini through its API. It does not train or fine-tune a model. Answers are grounded in a curated knowledge base of 377 records (see `DATASET_QUALITY_REPORT.md`).

Technician input → appliance category (session, or detected from text by `normalize.detect_appliance`) → brand detection + error-code extraction (`normalize.extract_codes`) → `knowledge_base.retrieve` → evidence block → Gemini → server-side citation check → stored with sources.

## Retrieval (`services/knowledge_base.py`)
1. **Filters:**
   - category: the session's appliance, or, when the session has none, the one detected from the text (named appliances are checked before generic words, so "fridge not cooling" is a refrigerator and "AC indoor fan" is an AC). Records from other appliances are never returned, except the listed related categories;
   - related categories plus related categories at a 0.6× weight (split_ac → aircon_dehumidifier, ceiling_fan → fan_other);
   - model if known;
   - when a brand is detected, only that brand's or brand-less records;
   - synthetic records excluded.
2. **Exact error-code match** (strongest signal, weight 10). Alternative codes a source lists (LG `CH38 / F4`) match too, as whole tokens only (weight 9), so `E1` never matches `E10`. Spaced codes (`CH 38`) are read as one code. Another brand's code never answers (the brand filter applies). Codes with no record are reported as `error_codes_unknown`.
3. **PostgreSQL full-text** (`to_tsvector('simple')` with a GIN index, OR-query, `ts_rank`).
4. **Embeddings** (optional): cosine similarity over `repair_embeddings` vectors from the same model and dimension, which gives `mode: hybrid`. Without them, retrieval falls back to keyword only, and the response says why.
5. **Weighting:** technician_reviewed 1.25, verified_source 1.15, unverified 1.0, plus a brand-match boost.
6. **Coverage:** `grounded` | `partial` | `none`.

## Grounding rules
- Each record is given to Gemini as `[record_id] (category, brand, market; verification status; RELATED/SYNTHETIC flags) …` inside `<knowledge>`, which is treated as data, not instructions.
- **Diagnosis:**
  - each fault is `supported_by_records` (with `record_ids`), `possible_cause` or `unverified_hypothesis`;
  - output also includes `confirmed_findings` (technician statements and visible facts only) and `missing_information`.
- **The server checks every citation:**
  - ids not in the retrieved set are deleted;
  - a "supported" fault left with no valid id is downgraded to `unverified_hypothesis`;
  - with coverage `none`, every fault becomes `unverified_hypothesis`, a missing-information note is added, and a follow-up question is ensured.
- **Unknown error codes:** the prompt forbids stating their meaning, and the server adds "No record for error code X" to `missing_information`.
- **Chat:** inline `[record_id]` citations are kept only if retrieved; invented ones are stripped and counted (`removed_invalid_citations`).
- **Guidance:** cited ids are filtered the same way. Every step's power sensitivity is re-checked by the server, so unverified source steps cannot become unlocked instructions.

## Server rules that do not depend on the model
- Microwave sessions: any generated step that opens the cabinet or mentions the magnetron, high-voltage capacitor, diode, transformer or interlock switch is replaced by a hand-over to authorised service.
- Power-sensitive steps stay locked until both safety statements are recorded (see `SECURITY.md`). A technician's statement is recorded as a statement, never as a measurement.

## Not done
- No ScaNN or pgvector (not available in the local Postgres).
- No ranking evaluation set, so no retrieval accuracy figures exist. Tests check category isolation and that the expected record is returned for one realistic query per appliance.
- Embedding re-ranking exists in code but production runs keyword-only (`VECTOR_SEARCH_MODE=keyword`).
- Real Gemini calls are untested from this environment.
