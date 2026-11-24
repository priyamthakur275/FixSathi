# Synthetic demo records

Made-up records for demos and tests only. They are NOT real repair history and NOT industry data.
Every record has verification_status `synthetic_demo` and `SYNTHETIC` in source_name (enforced by the schema).
They are never ingested unless `ingest_knowledge.py --include-synthetic` is used, and retrieval excludes them by default.
