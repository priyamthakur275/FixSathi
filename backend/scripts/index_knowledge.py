"""Embed repair records with GEMINI_EMBED_MODEL so retrieval can use hybrid (keyword + embedding) mode. Needs a Gemini key; costs API usage.
Safe to re-run: records already embedded with unchanged text are skipped, changed ones are refreshed. Each batch is committed, and on a
free-tier rate limit the script waits and resumes where it stopped."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import func, select
from app.core.exceptions import AppError
from app.db.models import RepairEmbedding
from app.db.session import SessionLocal
from app.services.knowledge_base import index_records

WAIT_SECONDS, MAX_WAITS = 65, 10


async def main():
    for attempt in range(MAX_WAITS + 1):
        db = SessionLocal()
        try:
            await index_records(db, commit_each_batch=True); db.commit()
            n = db.scalar(select(func.count()).select_from(RepairEmbedding).where(RepairEmbedding.source_type == 'record'))
            print(f'Done. {n} repair records are in the embedding index.'); return
        except AppError as e:
            db.rollback()
            if e.code != 'QUOTA_EXCEEDED' or attempt == MAX_WAITS:
                sys.exit(f'Stopped: {e.code}: {e}. Batches embedded so far are saved; run the script again to continue.')
            print(f'Rate-limited by Gemini; waiting {WAIT_SECONDS}s, then resuming...', flush=True)
            await asyncio.sleep(WAIT_SECONDS)
        finally:
            db.close()

asyncio.run(main())
