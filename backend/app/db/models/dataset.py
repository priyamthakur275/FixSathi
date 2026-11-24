from datetime import date
from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base, CreatedMixin, IdMixin, JSONType


class RepairRecordRow(IdMixin, CreatedMixin, Base):
    """Unified, source-attributed repair knowledge (see app/datasets/schema.py). The full record lives in `data`; key fields are columns for filtering."""
    __tablename__ = 'repair_records'
    record_id: Mapped[str] = mapped_column(String(120), unique=True)
    appliance_category: Mapped[str] = mapped_column(String(40), index=True)
    appliance_brand: Mapped[str | None] = mapped_column(String(60), index=True)
    appliance_model: Mapped[str | None] = mapped_column(String(80))
    market: Mapped[str | None] = mapped_column(String(8))
    error_code: Mapped[str | None] = mapped_column(String(20), index=True)
    severity: Mapped[str | None] = mapped_column(String(20))
    requires_power_off: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(String(24), index=True)
    source_name: Mapped[str] = mapped_column(String(200))
    source_license: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_record_id: Mapped[str] = mapped_column(String(120))
    search_text: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONType)
    last_updated: Mapped[date] = mapped_column(Date)
    __table_args__ = (Index('ix_repair_records_fts', text("to_tsvector('english', search_text)"), postgresql_using='gin'),)


class DatasetMedia(IdMixin, CreatedMixin, Base):
    """Metadata for future image/audio training or reference data. Stores references and labels only; no model is trained from this yet."""
    __tablename__ = 'dataset_media'
    media_type: Mapped[str] = mapped_column(String(20))  # appliance_photo | component_photo | fault_image | audio_recording
    uri: Mapped[str] = mapped_column(Text)
    repair_record_id: Mapped[str | None] = mapped_column(ForeignKey('repair_records.record_id', ondelete='SET NULL'), index=True)
    appliance_category: Mapped[str | None] = mapped_column(String(40))
    component_labels: Mapped[list] = mapped_column(JSONType, default=list)
    annotations: Mapped[list] = mapped_column(JSONType, default=list, comment='e.g. [{"label": "capacitor", "box": {"x_min":..}}] in 0-1000 coords')
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    source_name: Mapped[str] = mapped_column(String(200))
    source_license: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    license_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(String(24), default='unverified')
