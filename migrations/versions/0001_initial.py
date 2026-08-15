"""Initial catalog schema."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol_root", sa.String(16), nullable=False),
        sa.Column("asset_class", sa.String(64), nullable=False),
        sa.Column("tick_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("multiplier", sa.Numeric(18, 8), nullable=False),
        sa.Column("timezone_session", sa.String(64), nullable=False),
        sa.Column("session_calendar_id", sa.String(64), nullable=False),
    )
    op.create_index("ix_instruments_symbol_root", "instruments", ["symbol_root"])

    op.create_table(
        "source_systems",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("connector_version", sa.String(32), nullable=False),
    )

    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("contract_month", sa.String(6), nullable=False),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("local_symbol", sa.String(64), nullable=False),
        sa.Column("ib_con_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("active", "expired", "demo", name="contractstatus"), nullable=False),
        sa.UniqueConstraint("instrument_id", "contract_month", "exchange"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("source_systems.id"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("bar_size", sa.String(32), nullable=False),
        sa.Column("start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_params", postgresql.JSONB(), nullable=False),
        sa.Column("timezone_original", sa.String(64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "succeeded", "failed", "partial", name="ingestionstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "raw_bar_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_runs.id"), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("raw_checksum", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("manifest_uri", sa.Text(), nullable=False),
        sa.Column("immutable", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "canonical_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("bar_size", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("normalizer_version", sa.String(32), nullable=False),
        sa.Column("preferred_source_id", sa.String(32), nullable=True),
        sa.Column("coverage_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column(
            "quality_status",
            sa.Enum("usable", "quarantine", "insufficient", "draft", name="qualitystatus"),
            nullable=False,
        ),
        sa.Column("lineage", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Quality tables
    op.create_table(
        "quality_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("canonical_datasets.id"), nullable=True),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_runs.id"), nullable=True),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("gap_count", sa.Integer(), nullable=False),
        sa.Column("gaps", postgresql.JSONB(), nullable=False),
        sa.Column("ohlc_violations", sa.Integer(), nullable=False),
        sa.Column("summary_markdown_uri", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reconciliation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("common_coverage", postgresql.JSONB(), nullable=False),
        sa.Column("price_discrepancies", postgresql.JSONB(), nullable=False),
        sa.Column("volume_rel_diff", postgresql.JSONB(), nullable=False),
        sa.Column("report_uri", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "quarantine_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reconciliation_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reconciliation_reports.id"),
            nullable=False,
        ),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("field", sa.String(32), nullable=False),
        sa.Column("source_a_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("source_b_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "accepted_divergence", "resolved", name="quarantinestatus"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("quarantine_items")
    op.drop_table("reconciliation_reports")
    op.drop_table("quality_reports")
    op.drop_table("canonical_datasets")
    op.drop_table("raw_bar_batches")
    op.drop_table("ingestion_runs")
    op.drop_table("contracts")
    op.drop_table("source_systems")
    op.drop_table("instruments")
    op.execute("DROP TYPE IF EXISTS quarantinestatus")
    op.execute("DROP TYPE IF EXISTS qualitystatus")
    op.execute("DROP TYPE IF EXISTS ingestionstatus")
    op.execute("DROP TYPE IF EXISTS contractstatus")
