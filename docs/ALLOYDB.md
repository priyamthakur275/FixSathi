# AlloyDB and vector search: current state

**What is implemented:** embeddings from `GEMINI_EMBED_MODEL` are stored in `repair_embeddings.vector` as a JSON array, along with `model_identifier` and `dimensions`, and compared with cosine similarity in Python. Results are filtered by the caller's access scope before ranking. Only vectors from the current model with matching dimensions are compared. If embeddings are unavailable, keyword search runs and the response says `mode: "keyword"` with the reason.

This works on plain PostgreSQL and on AlloyDB without extensions, and is fine for thousands of records.

**Not implemented and not claimed:** pgvector or AlloyDB ScaNN indexes. The local sandbox PostgreSQL had no `vector` extension available, so no SQL using it was written or tested.

**To move to AlloyDB ScaNN (to do at the event, after verifying on the actual instance):**
1. On the AlloyDB instance, confirm the extensions with `SELECT * FROM pg_available_extensions WHERE name IN ('vector','alloydb_scann');`.
2. Write a new Alembic migration that adds a `vector(<dims>)` column and copies the JSON vectors into it.
3. Create the ScaNN index using the syntax from the current AlloyDB documentation for that instance's version.
4. Change `services/retrieval.py` to order by the vector distance operator in SQL. Keep the access-scope filter in the same query.
5. Keep keyword mode as the fallback.

Point `DATABASE_URL` at AlloyDB (the AlloyDB Auth Proxy or a private IP) and run `alembic upgrade head`. The schema uses only standard PostgreSQL types (UUID, JSONB, timestamptz).
