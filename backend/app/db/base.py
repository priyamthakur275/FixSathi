import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, MetaData, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {'ix': 'ix_%(column_0_label)s', 'uq': 'uq_%(table_name)s_%(column_0_name)s', 'ck': 'ck_%(table_name)s_%(constraint_name)s',
          'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s', 'pk': 'pk_%(table_name)s'}
JSONType = JSON().with_variant(JSONB(), 'postgresql')


def utcnow() -> datetime: return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class CreatedMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
