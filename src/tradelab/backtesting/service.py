"""Backtest experiment orchestration service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from tradelab.backtesting.hashing import experiment_integrity_hash, implementation_fingerprint
from tradelab.backtesting.metrics import compute_metrics
from tradelab.backtesting.reporting import write_experiment_report
from tradelab.backtesting.robustness import (
    run_sensitivity,
    run_session_long_baseline,
    run_walk_forward,
)
from tradelab.backtesting.sessions import with_session_date
from tradelab.backtesting.splits import (
    SplitSpec,
    apply_temporal_split,
    default_split_from_frame,
    split_spec_to_dict,
)
from tradelab.backtesting.strategies.registry import get_strategy
from tradelab.datasets.store import (
    claim_holdout,
    get_dataset,
    get_holdout_claim,
    release_holdout_claim,
    upsert_experiment,
)
from tradelab.instruments import resolve_instrument_spec
from tradelab.observability.settings import get_settings


def run_experiment(
    *,
    dataset_id: str,
    parameters: dict[str, Any],
    consume_holdout: bool = False,
    split_spec: dict[str, Any] | None = None,
    strategy_id: str = "orb_atr_intraday",
) -> dict[str, Any]:
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise FileNotFoundError("dataset not found")
    if dataset.get("quality_status") != "usable":
        raise ValueError("dataset_not_usable")
    previous_holdout = get_holdout_claim(dataset_id)
    if consume_holdout and previous_holdout:
        raise PermissionError(
            "holdout_already_consumed: "
            f"dataset={dataset_id} experiment={previous_holdout.get('experiment_id')}"
        )

    spec = get_strategy(strategy_id)
    params = spec.validate(parameters)
    path = Path(dataset["storage_uri"])
    df = pd.read_parquet(path)
    market = resolve_instrument_spec(dataset, df)
    df = with_session_date(df, market.session_timezone)

    split = (
        SplitSpec(**split_spec)
        if split_spec
        else default_split_from_frame(df, session_timezone=market.session_timezone)
    )
    parts = apply_temporal_split(df, split, session_timezone=market.session_timezone)

    settings = get_settings()
    code_version = (
        f"{settings.code_version}:{spec.version}:{implementation_fingerprint(spec.strategy_id)}"
    )
    trades_all = []
    metrics_by_split: dict[str, Any] = {}
    for label in ("train", "validation"):
        fills = spec.run(
            parts[label],
            params,
            split_label=label,
            tick_size=market.tick_size,
            multiplier=market.multiplier,
            session_timezone=market.session_timezone,
        )
        trades_all.extend(fills)
        metrics_by_split[label] = compute_metrics(fills)

    holdout_consumed = False
    if consume_holdout:
        if parts["holdout"].empty:
            raise ValueError("holdout_empty: at least three exchange sessions are required")
        fills = spec.run(
            parts["holdout"],
            params,
            split_label="holdout",
            tick_size=market.tick_size,
            multiplier=market.multiplier,
            session_timezone=market.session_timezone,
        )
        trades_all.extend(fills)
        metrics_by_split["holdout"] = compute_metrics(fills)
        holdout_consumed = True
    else:
        metrics_by_split["holdout"] = {"blocked": True, "trade_count": 0}

    research_df = pd.concat([parts["train"], parts["validation"]], ignore_index=True)
    walk_forward = run_walk_forward(
        research_df,
        spec,
        params,
        tick_size=market.tick_size,
        multiplier=market.multiplier,
        session_timezone=market.session_timezone,
    )
    sensitivity = run_sensitivity(
        parts["train"],
        parts["validation"],
        spec,
        params,
        tick_size=market.tick_size,
        multiplier=market.multiplier,
        session_timezone=market.session_timezone,
    )
    comm = float(params.model_dump().get("commission_per_side", 0.62))
    slip = int(params.model_dump().get("slippage_ticks", 1))
    baseline = {
        "train": run_session_long_baseline(
            parts["train"],
            commission_per_side=comm,
            slippage_ticks=slip,
            tick_size=market.tick_size,
            multiplier=market.multiplier,
            session_timezone=market.session_timezone,
        ),
        "validation": run_session_long_baseline(
            parts["validation"],
            commission_per_side=comm,
            slippage_ticks=slip,
            tick_size=market.tick_size,
            multiplier=market.multiplier,
            session_timezone=market.session_timezone,
        ),
    }

    integrity = experiment_integrity_hash(
        dataset_checksum=dataset["content_checksum"],
        code_version=code_version,
        strategy_id=spec.strategy_id,
        parameters=params.model_dump(),
        market=market.to_dict(),
        split_spec=split_spec_to_dict(split),
        consume_holdout=consume_holdout,
    )

    experiment_id = str(uuid.uuid4())
    record = {
        "experiment_id": experiment_id,
        "dataset_id": dataset_id,
        "strategy_id": spec.strategy_id,
        "parameters": params.model_dump(),
        "market": market.to_dict(),
        "code_version": code_version,
        "integrity_hash": integrity,
        "split_spec": split_spec_to_dict(split),
        "status": "succeeded",
        "holdout_consumed": holdout_consumed,
        "metrics_by_split": metrics_by_split,
        "walk_forward": walk_forward,
        "sensitivity": sensitivity,
        "baseline": baseline,
        "trades": [t.__dict__ for t in trades_all],
        "report_uri": None,
    }
    claimed = False
    if consume_holdout:
        claim_holdout(
            dataset_id,
            {
                "dataset_id": dataset_id,
                "experiment_id": experiment_id,
                "strategy_id": spec.strategy_id,
                "integrity_hash": integrity,
                "consumed_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        claimed = True
    try:
        record["report_uri"] = write_experiment_report(record)
        upsert_experiment(record)
    except Exception:
        if claimed:
            release_holdout_claim(dataset_id, experiment_id)
        raise
    return record
