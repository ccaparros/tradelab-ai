"""Quality / reconciliation / quarantine models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tradelab.datasets.models import Base


class QuarantineStatus(StrEnum):
    open = "open"
    accepted_divergence = "accepted_divergence"
    resolved = "resolved"


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canonical_datasets.id"), nullable=True
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True
    )
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    gap_count: Mapped[int] = mapped_column(Integer, default=0)
    gaps: Mapped[list] = mapped_column(JSONB, default=list)
    ohlc_violations: Mapped[int] = mapped_column(Integer, default=0)
    summary_markdown_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReconciliationReport(Base):
    __tablename__ = "reconciliation_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    common_coverage: Mapped[dict] = mapped_column(JSONB, default=dict)
    price_discrepancies: Mapped[list] = mapped_column(JSONB, default=list)
    volume_rel_diff: Mapped[dict] = mapped_column(JSONB, default=dict)
    report_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuarantineItem(Base):
    __tablename__ = "quarantine_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliation_reports.id"), nullable=False
    )
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    source_a_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    source_b_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[QuarantineStatus] = mapped_column(
        Enum(QuarantineStatus), default=QuarantineStatus.open
    )
