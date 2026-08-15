"""In-memory / file-backed research store for demo and early API wiring.

Persists dataset/experiment/analysis metadata as JSON under DATA_ROOT so the
happy path works without requiring Postgres to be up (Postgres remains the
production target via Alembic models).
"""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from tradelab.observability.settings import get_settings

_lock = threading.Lock()


def _store_path() -> Path:
    root = Path(get_settings().data_root)
    root.mkdir(parents=True, exist_ok=True)
    return root / "store.json"


def _load() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"datasets": {}, "experiments": {}, "analyses": {}, "documents": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def upsert_dataset(record: dict[str, Any]) -> dict[str, Any]:
    with _lock:
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
    with _lock:
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
    with _lock:
        data = _load()
        key = str(record["analysis_id"])
        data.setdefault("analyses", {})[key] = record
        _save(data)
        return record


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    return _load().get("analyses", {}).get(str(analysis_id))


def new_id() -> str:
    return str(uuid.uuid4())
