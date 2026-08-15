"""Backtest experiment orchestration service."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from tradelab.backtesting.hashing import experiment_integrity_hash
from tradelab.backtesting.metrics import compute_metrics
from tradelab.backtesting.splits import (
    SplitSpec,
    apply_temporal_split,
    assert_holdout_policy,
    default_split_from_frame,
    split_spec_to_dict,
)
from tradelab.backtesting.strategies.registry import get_strategy
from tradelab.backtesting.reporting import write_experiment_report
from tradelab.datasets.store import get_dataset, upsert_experiment
from tradelab.observability.settings import get_settings


def run_experiment(
    *,
    dataset_id: str,
    parameters: dict[str, Any],
    consume_holdout: bool = False,
    split_spec: dict[str, Any] | None = None,
    strategy_id: str = "orb_atr_intraday",
) -> dict[str, Any]:
    assert_holdout_policy(consume_holdout=consume_holdout, selecting_parameters=not consume_holdout)

    dataset = get_dataset(dataset_id)
    if not dataset:
        raise FileNotFoundError("dataset not found")
    if dataset.get("quality_status") != "usable":
        raise ValueError("dataset_not_usable")

    spec = get_strategy(strategy_id)
    params = spec.validate(parameters)
    path = Path(dataset["storage_uri"])
    df = pd.read_parquet(path)

    split = (
        SplitSpec(**split_spec)
        if split_spec
        else default_split_from_frame(df)
    )
    parts = apply_temporal_split(df, split)

    settings = get_settings()
    trades_all = []
    metrics_by_split: dict[str, Any] = {}
    for label in ("train", "validation"):
        fills = spec.run(parts[label], params, split_label=label)
        trades_all.extend(fills)
        metrics_by_split[label] = compute_metrics(fills)

    holdout_consumed = False
    if consume_holdout:
        fills = spec.run(parts["holdout"], params, split_label="holdout")
        trades_all.extend(fills)
        metrics_by_split["holdout"] = compute_metrics(fills)
        holdout_consumed = True
    else:
        metrics_by_split["holdout"] = {"blocked": True, "trade_count": 0}

    integrity = experiment_integrity_hash(
        dataset_checksum=dataset["content_checksum"],
        code_version=f"{settings.code_version}:{spec.version}",
        strategy_id=spec.strategy_id,
        parameters=params.model_dump(),
    )

    experiment_id = str(uuid.uuid4())
    record = {
        "experiment_id": experiment_id,
        "dataset_id": dataset_id,
        "strategy_id": spec.strategy_id,
        "parameters": params.model_dump(),
        "code_version": f"{settings.code_version}:{spec.version}",
        "integrity_hash": integrity,
        "split_spec": split_spec_to_dict(split),
        "status": "succeeded",
        "holdout_consumed": holdout_consumed,
        "metrics_by_split": metrics_by_split,
        "trades": [t.__dict__ for t in trades_all],
        "report_uri": None,
    }
    record["report_uri"] = write_experiment_report(record)
    upsert_experiment(record)
    return record
