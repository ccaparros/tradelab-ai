"""Integrity hash for reproducible experiments."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def experiment_integrity_hash(
    *,
    dataset_checksum: str,
    code_version: str,
    strategy_id: str,
    parameters: dict[str, Any],
) -> str:
    payload = {
        "dataset_checksum": dataset_checksum,
        "code_version": code_version,
        "strategy_id": strategy_id,
        "parameters": parameters,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
