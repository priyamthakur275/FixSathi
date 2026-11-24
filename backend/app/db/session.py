from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from ..config import get_settings

_engine = None
_Factory: sessionmaker | None = None


def engine():
    global _engine, _Factory
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=10, future=True)
        _Factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def SessionLocal() -> Session:
    engine(); assert _Factory
    return _Factory()


def get_db() -> Iterator[Session]:
    """Use as Depends(get_db, scope="function"): the commit then runs before the response is sent. With FastAPI's default
    request scope it runs after, so a client reading right after a write (create report, open report) could get a 404."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
