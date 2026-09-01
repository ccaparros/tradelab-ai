"""Integrity hash for reproducible experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def implementation_fingerprint(strategy_id: str) -> str:
    """Hash the executable research method, independent of manual version bumps."""
    root = Path(__file__).resolve().parent
    strategy_file = "vwap_fade.py" if strategy_id == "vwap_fade_intraday" else "orb_atr.py"
    paths = [
        root.parent / "instruments.py",
        root / "engine.py",
        root / "hashing.py",
        root / "metrics.py",
        root / "robustness.py",
        root / "sessions.py",
        root / "service.py",
        root / "splits.py",
        root / "strategies" / "registry.py",
        root / "strategies" / strategy_file,
    ]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def experiment_integrity_hash(
    *,
    dataset_checksum: str,
    code_version: str,
    strategy_id: str,
    parameters: dict[str, Any],
    market: dict[str, Any] | None = None,
    split_spec: dict[str, Any] | None = None,
    consume_holdout: bool = False,
) -> str:
    payload = {
        "dataset_checksum": dataset_checksum,
        "code_version": code_version,
        "strategy_id": strategy_id,
        "parameters": parameters,
        "consume_holdout": consume_holdout,
    }
    if market is not None:
        payload["market"] = market
    if split_spec is not None:
        payload["split_spec"] = split_spec
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
