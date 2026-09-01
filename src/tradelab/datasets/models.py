"""SQLAlchemy catalog models — Instrument through CanonicalDataset."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class QualityStatus(StrEnum):
    usable = "usable"
    quarantine = "quarantine"
    insufficient = "insufficient"
    draft = "draft"


class IngestionStatus(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"


class ContractStatus(StrEnum):
    active = "active"
    expired = "expired"
    demo = "demo"


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_root: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(64), default="future_micro_index")
    tick_size: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    timezone_session: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    session_calendar_id: Mapped[str] = mapped_column(String(64), default="CME_EQUITY_RTH")

    contracts: Mapped[list[Contract]] = relationship(back_populates="instrument")


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (UniqueConstraint("instrument_id", "contract_month", "exchange"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    contract_month: Mapped[str] = mapped_column(String(6), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    local_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    ib_con_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.active
    )

    instrument: Mapped[Instrument] = relationship(back_populates="contracts")


class SourceSystem(Base):
    __tablename__ = "source_systems"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # ninjatrader | ibkr
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    connector_version: Mapped[str] = mapped_column(String(32), default="0.1.0")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_systems.id"), nullable=False)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    bar_size: Mapped[str] = mapped_column(String(32), default="5 mins")
    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    timezone_original: Mapped[str] = mapped_column(String(64), default="UTC")
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus), default=IngestionStatus.running
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    raw_batches: Mapped[list[RawBarBatch]] = relationship(back_populates="ingestion_run")


class RawBarBatch(Base):
    __tablename__ = "raw_bar_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False
    )
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    raw_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)

    ingestion_run: Mapped[IngestionRun] = relationship(back_populates="raw_batches")


class CanonicalDataset(Base):
    __tablename__ = "canonical_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    bar_size: Mapped[str] = mapped_column(String(32), default="5 mins")
    version: Mapped[int] = mapped_column(Integer, default=1)
    normalizer_version: Mapped[str] = mapped_column(String(32), default="0.1.0")
    preferred_source_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coverage_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    coverage_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_status: Mapped[QualityStatus] = mapped_column(
        Enum(QualityStatus), default=QualityStatus.draft
    )
    lineage: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
