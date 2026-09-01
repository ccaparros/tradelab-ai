"""Register local raw batches (manifest + parquet) into the ingestion contract."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

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

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"invalid manifest: {manifest_uri}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")

    try:
        frame = pd.read_parquet(parquet_path)
    except Exception as exc:
        raise ValueError(f"invalid parquet batch: {parquet_uri}") from exc

    expected = {
        "source": str(source).strip().lower(),
        "instrument": str(instrument).strip().upper(),
        "contract_month": str(contract_month).strip(),
    }
    for field, expected_value in expected.items():
        manifest_value = str(manifest.get(field) or "").strip()
        if field == "source":
            manifest_value = manifest_value.lower()
        elif field == "instrument":
            manifest_value = manifest_value.upper()
        if manifest_value != expected_value:
            raise ValueError(
                f"manifest {field} mismatch: request={expected_value} manifest={manifest_value or 'missing'}"
            )
        if field not in frame.columns:
            raise ValueError(f"parquet missing metadata column: {field}")
        values = {
            str(value).strip().upper()
            if field == "instrument"
            else str(value).strip().lower()
            if field == "source"
            else str(value).strip()
            for value in frame[field].dropna().unique()
        }
        if values != {expected_value}:
            raise ValueError(
                f"parquet {field} mismatch: request={expected_value} parquet={sorted(values)}"
            )

    manifest_bar_size = str(manifest.get("bar_size") or "").strip()
    if manifest_bar_size != "5 mins":
        raise ValueError(
            f"manifest bar_size must be '5 mins', got {manifest_bar_size or 'missing'}"
        )
    if "bar_size" not in frame.columns or set(frame["bar_size"].dropna().astype(str)) != {"5 mins"}:
        raise ValueError("parquet bar_size must contain only '5 mins'")

    manifest_rows = manifest.get("row_count")
    if manifest_rows is None or int(manifest_rows) != len(frame):
        raise ValueError(
            f"manifest row_count mismatch: manifest={manifest_rows} parquet={len(frame)}"
        )
    manifest_checksum = (
        manifest.get("checksum") or manifest.get("raw_checksum") or manifest.get("content_checksum")
    )
    if manifest_checksum and str(manifest_checksum) != actual:
        raise ValueError("checksum mismatch between manifest and parquet batch")
    if request_params and manifest.get("request_params") not in (None, request_params):
        raise ValueError("request_params mismatch between request and manifest")

    run_id = uuid.uuid4()
    return {
        "ingestion_run_id": run_id,
        "source": source,
        "instrument": instrument,
        "contract_month": contract_month,
        "parquet_uri": str(parquet_path),
        "manifest_uri": str(manifest_path),
        "checksum": actual,
        "row_count": len(frame),
        "request_params": request_params or manifest.get("request_params", {}),
        "status": "succeeded",
    }
