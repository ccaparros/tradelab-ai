"""Tracing helpers for analysis/experiment correlation."""

from __future__ import annotations

from typing import Any


def span_fields(
    *,
    analysis_id: str | None = None,
    experiment_id: str | None = None,
    tool_name: str | None = None,
    latency_ms: int | None = None,
    token_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "experiment_id": experiment_id,
        "tool_name": tool_name,
        "latency_ms": latency_ms,
        "token_usage": token_usage,
    }
