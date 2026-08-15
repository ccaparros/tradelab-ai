"""Load demo snapshot into local store for evaluator happy path (no broker)."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pandas as pd

from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import upsert_dataset
from tradelab.observability.settings import get_settings
from tradelab.rag.indexer import index_markdown, reindex_reports


def main() -> None:
    settings = get_settings()
    fixture = Path("data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.parquet")
    if not fixture.exists():
        raise SystemExit(f"Missing fixture {fixture}")

    demo_dir = Path("data_catalog/demo_snapshot")
    demo_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(fixture)
    published = publish_canonical_dataset(
        df,
        contract_id=uuid.uuid4(),
        preferred_source_id="ninjatrader",
        lineage={"demo": True, "source": "ninjatrader"},
    )
    record = {
        "dataset_id": str(published["dataset_id"]),
        "contract_id": str(published["contract_id"]),
        "instrument": "MES",
        "contract_month": "202609",
        "bar_size": "5 mins",
        "quality_status": published["quality_status"],
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "coverage_start_utc": str(published["coverage_start_utc"]),
        "coverage_end_utc": str(published["coverage_end_utc"]),
        "quality": published["quality"],
        "lineage": published["lineage"],
        "preferred_source": "ninjatrader",
    }
    upsert_dataset(record)

    meta = {"dataset_id": record["dataset_id"], "quality_status": record["quality_status"]}
    (demo_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    index_markdown(
        "Demo quality report",
        f"Demo dataset {record['dataset_id']} loaded with status {record['quality_status']}.",
        source_uri="demo://quality",
        doc_type="demo",
    )
    rag = reindex_reports()
    print(json.dumps({"ok": True, **meta, "rag": rag}, indent=2))


if __name__ == "__main__":
    main()
