"""In-memory / file-backed research store for demo and early API wiring.

Persists dataset/experiment/analysis metadata as JSON under DATA_ROOT so the
happy path works without requiring Postgres to be up (Postgres remains the
production target via Alembic models).
"""

from __future__ import annotations

import json
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock

from tradelab.ingestion.storage import atomic_write_text
from tradelab.observability.settings import get_settings

_lock = threading.Lock()


def _store_path() -> Path:
    root = Path(get_settings().data_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / "store.json"


def _load() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {
            "datasets": {},
            "experiments": {},
            "analyses": {},
            "documents": {},
            "holdout_claims": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("holdout_claims", {})
    return data


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    atomic_write_text(path, json.dumps(data, indent=2, default=str))


@contextmanager
def _write_guard():
    with _lock:
        with FileLock(f"{_store_path()}.lock"):
            yield


def upsert_dataset(record: dict[str, Any]) -> dict[str, Any]:
    with _write_guard():
        data = _load()
        key = str(record["dataset_id"])
        data["datasets"][key] = record
        _save(data)
        return record


def list_datasets(quality_status: str | None = None) -> list[dict[str, Any]]:
    data = _load()
    items = list(data["datasets"].values())
    if quality_status:
        items = [d for d in items if d.get("quality_status") == quality_status]
    return items


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    return _load()["datasets"].get(str(dataset_id))


def upsert_experiment(record: dict[str, Any]) -> dict[str, Any]:
    with _write_guard():
        data = _load()
        key = str(record["experiment_id"])
        data["experiments"][key] = record
        _save(data)
        return record


def get_experiment(experiment_id: str) -> dict[str, Any] | None:
    return _load()["experiments"].get(str(experiment_id))


def list_experiments(dataset_id: str | None = None) -> list[dict[str, Any]]:
    items = list(_load()["experiments"].values())
    if dataset_id:
        items = [e for e in items if str(e.get("dataset_id")) == str(dataset_id)]
    return items


def upsert_analysis(record: dict[str, Any]) -> dict[str, Any]:
    with _write_guard():
        data = _load()
        key = str(record["analysis_id"])
        data.setdefault("analyses", {})[key] = record
        _save(data)
        return record


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    return _load().get("analyses", {}).get(str(analysis_id))


def get_holdout_claim(dataset_id: str) -> dict[str, Any] | None:
    return _load().get("holdout_claims", {}).get(str(dataset_id))


def claim_holdout(dataset_id: str, claim: dict[str, Any]) -> dict[str, Any]:
    """Atomically claim the dataset holdout once within this store process."""
    with _write_guard():
        data = _load()
        claims = data.setdefault("holdout_claims", {})
        key = str(dataset_id)
        existing = claims.get(key)
        if existing:
            raise PermissionError(
                "holdout_already_consumed: "
                f"dataset={key} experiment={existing.get('experiment_id')}"
            )
        claims[key] = claim
        _save(data)
        return claim


def release_holdout_claim(dataset_id: str, experiment_id: str) -> None:
    """Release only an incomplete claim created by the same experiment."""
    with _write_guard():
        data = _load()
        claims = data.setdefault("holdout_claims", {})
        key = str(dataset_id)
        existing = claims.get(key)
        if existing and str(existing.get("experiment_id")) == str(experiment_id):
            del claims[key]
            _save(data)


def new_id() -> str:
    return str(uuid.uuid4())
