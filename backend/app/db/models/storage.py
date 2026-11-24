from datetime import datetime
from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base, utcnow


class StoredFile(Base):
    """Image bytes kept in PostgreSQL so they survive server restarts on hosts without a persistent disk."""
    __tablename__ = 'stored_files'
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
