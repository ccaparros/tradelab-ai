"""Typed research tools — allowlist only; no order placement."""

from __future__ import annotations

from typing import Any

from tradelab.backtesting.service import run_experiment
from tradelab.backtesting.strategies.registry import list_strategy_specs
from tradelab.datasets.store import get_dataset, get_experiment, list_datasets
from tradelab.quality.reconcile import reconcile_frames

ALLOWED_TOOLS = frozenset(
    {
        "get_dataset_quality",
        "compare_sources",
        "run_backtest",
        "get_experiment_metrics",
        "get_trade_sample",
        "search_research_documents",
        "generate_experiment_report",
    }
)

FORBIDDEN_TOOLS = frozenset(
    {
        "place_order",
        "submit_order",
        "cancel_order",
        "modify_order",
    }
)


def get_dataset_quality(dataset_id: str) -> dict[str, Any]:
    ds = get_dataset(dataset_id)
    if not ds:
        raise FileNotFoundError("not_found")
    return {
        "dataset_id": dataset_id,
        "quality_status": ds.get("quality_status"),
        **(ds.get("quality") or {}),
    }


def compare_sources_tool(
    left_bars,
    right_bars,
    *,
    tick_size: float = 0.25,
) -> dict[str, Any]:
    from decimal import Decimal

    return reconcile_frames(left_bars, right_bars, tick_size=Decimal(str(tick_size)))


def run_backtest_tool(
    dataset_id: str,
    allowed_parameters: dict[str, Any],
    consume_holdout: bool = False,
    strategy_id: str = "orb_atr_intraday",
) -> dict[str, Any]:
    return run_experiment(
        dataset_id=dataset_id,
        strategy_id=strategy_id,
        parameters=allowed_parameters,
        consume_holdout=consume_holdout,
    )


def get_experiment_metrics(experiment_id: str) -> dict[str, Any]:
    exp = get_experiment(experiment_id)
    if not exp:
        raise FileNotFoundError("not_found")
    return {
        "experiment_id": experiment_id,
        "metrics_by_split": exp.get("metrics_by_split"),
        "integrity_hash": exp.get("integrity_hash"),
    }


def get_trade_sample(experiment_id: str, *, split_label: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    exp = get_experiment(experiment_id)
    if not exp:
        raise FileNotFoundError("not_found")
    trades = exp.get("trades") or []
    if split_label:
        trades = [t for t in trades if t.get("split_label") == split_label]
    return trades[:limit]


def search_research_documents(
    query: str,
    *,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from tradelab.rag.retrieve import hybrid_search

    return hybrid_search(query, top_k=top_k, filters=filters)


def generate_experiment_report(experiment_id: str) -> dict[str, Any]:
    exp = get_experiment(experiment_id)
    if not exp:
        raise FileNotFoundError("not_found")
    return {
        "experiment_id": experiment_id,
        "markdown_uri": exp.get("report_uri") or f"memory://experiments/{experiment_id}",
        "integrity_hash": exp["integrity_hash"],
        "baseline_notes": (
            "Includes session-long baseline, expanding walk-forward on train+validation, "
            "and cost/nearby-parameter sensitivity. Holdout is never used for these checks."
        ),
        "walk_forward": exp.get("walk_forward"),
        "sensitivity": exp.get("sensitivity"),
        "baseline": exp.get("baseline"),
    }


def list_strategies() -> list[dict[str, Any]]:
    return list_strategy_specs()


def assert_tool_allowed(name: str) -> None:
    if name in FORBIDDEN_TOOLS or name not in ALLOWED_TOOLS:
        raise PermissionError(f"rejected: tool '{name}' is not permitted (research-only)")
