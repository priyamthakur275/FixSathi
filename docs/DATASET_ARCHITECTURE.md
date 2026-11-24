# Dataset architecture

```mermaid
flowchart LR
  A[data/raw/appliancedb CSV] --> I1[importers/appliancedb.py]
  B[data/raw/openrepair/*.csv] --> I2[importers/openrepair.py]
  C[backend/app/knowledge/faults.json] --> I3[importers/curated.py]
  I1 & I2 & I3 --> N[normalize.py]
  N --> V[pipeline.validate: schema, rules, de-dup]
  V --> P[data/processed/repair_records.jsonl]
  V --> R[data/processed/rejected.jsonl]
  S[data/synthetic/demo_records.jsonl] -. only with --include-synthetic .-> DB
  P --> DB[(PostgreSQL repair_records)]
  DB --> KB[services/knowledge_base.retrieve]
  DB -. scripts/index_knowledge.py .-> E[(repair_embeddings)]
  E --> KB
```

## Unified schema

`backend/app/datasets/schema.py` (JSON Schema export: `data/schemas/repair_record.schema.json`). The fields are those in the brief, plus:
- `market` and `error_code_original`;
- `fixsaathi_safety_policy`, kept separate from the source's own `safety_requirements`;
- `requires_power_off`;
- `provenance`, holding the upstream ids, commit and source type.

Unknown values stay `null` or `[]`.

## Verification tiers

| Status | Meaning |
|---|---|
| `verified_source` | The upstream source says it came from an official manufacturer listing. **FixSaathi did not re-verify.** |
| `technician_reviewed` | Reviewed by a named technician. No records have this status yet. |
| `unverified` | Secondary/community source, or FixSaathi-authored guidance. |
| `synthetic_demo` | Made up for demos. Must say SYNTHETIC in `source_name` (enforced). Never in `data/processed`, and excluded from retrieval by default. |

## Cleaning rules (pipeline.py, normalize.py)
- **Invalid:**
  - unknown category;
  - no symptom, fault, code or step;
  - missing licence;
  - no `source_url` or author;
  - bad year or severity;
  - mislabelled synthetic.
- **Duplicates:** by `record_id`, and by content key = category + brand + market + model + code + stated fault + observed text. The same code on another brand, market or model is **never** merged (for example, Samsung `4C` US and UK stay two records).
- **Brands:** normalised through an alias map. "unknown", "n/a" and similar become `null`.
- **Error codes:** uppercased with separators stripped (`e-21` becomes `E21`); the original is kept.
- **Components:** canonicalised (`NTC thermistor` becomes `thermistor`). Symptoms are extracted by pattern from free text.
- **Safety:** source steps are scanned for power-sensitive words (open, remove, wire, capacitor, board...). If any are found, `requires_power_off=true`. This does not make a source's steps trusted. Generated steps are still re-checked and gated by `SafetyService`.

## Multimodal metadata (`dataset_media`)
- Stores `media_type` (appliance_photo / component_photo / fault_image / audio_recording), `uri`, `repair_record_id`, labels, annotations (boxes in 0-1000 coordinates), sample rate, duration, source, licence, `license_checked`, and verification status.
- It is metadata only: **no image or audio model is trained**, and no media has been imported.

## Commands
```bash
cd backend
python scripts/download_datasets.py      # ApplianceDB via git; prints manual steps for the others
python scripts/process_datasets.py       # raw -> processed + rejected + processing_report.json + JSON schema
python scripts/validate_datasets.py      # re-check processed and synthetic files (exit 1 on error)
alembic upgrade head
python scripts/ingest_knowledge.py       # upsert into PostgreSQL (add --include-synthetic for demos)
python scripts/index_knowledge.py        # optional: embeddings (needs GEMINI_API_KEY + GEMINI_EMBED_MODEL; paid API usage)
```
The app also auto-seeds the 12 curated entries at startup, so it works before any ingestion.
