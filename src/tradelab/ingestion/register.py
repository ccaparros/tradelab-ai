"""Register local raw batches (manifest + parquet) into the ingestion contract."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from tradelab.ingestion.storage import sha256_file


def register_raw_batch(
    *,
    source: str,
    instrument: str,
    contract_month: str,
    parquet_uri: str,
    manifest_uri: str,
    checksum: str | None = None,
    request_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parquet_path = Path(parquet_uri)
    manifest_path = Path(manifest_uri)
    if not parquet_path.exists():
        raise FileNotFoundError(parquet_uri)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_uri)

    actual = sha256_file(parquet_path)
    if checksum and checksum != actual:
        raise ValueError("checksum mismatch for parquet batch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = uuid.uuid4()
    return {
        "ingestion_run_id": run_id,
        "source": source,
        "instrument": instrument,
        "contract_month": contract_month,
        "parquet_uri": str(parquet_path),
        "manifest_uri": str(manifest_path),
        "checksum": actual,
        "row_count": int(manifest.get("row_count", 0)),
        "request_params": request_params or manifest.get("request_params", {}),
        "status": "succeeded",
    }
