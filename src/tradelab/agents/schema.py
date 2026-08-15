"""Structured agent response + numeric/citation verifier."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MetricRef(BaseModel):
    name: str
    value: Any
    experiment_id: str


class SourceRef(BaseModel):
    document_id: str
    citation: str
    chunk_id: str | None = None


class AnalysisOutput(BaseModel):
    analysis_id: str
    status: Literal["completed", "needs_clarification", "insufficient_evidence", "rejected"]
    answer: str
    metrics: list[MetricRef] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    tool_invocations: list[dict[str, Any]] = Field(default_factory=list)


def verify_analysis(
    output: AnalysisOutput,
    *,
    known_metric_values: set[tuple[str, str, str]],
    known_document_ids: set[str],
) -> AnalysisOutput:
    """Reject hallucinated metrics/IDs. known_metric_values: (name, str(value), experiment_id)."""
    for m in output.metrics:
        key = (m.name, str(m.value), m.experiment_id)
        if key not in known_metric_values:
            return output.model_copy(
                update={
                    "status": "insufficient_evidence",
                    "warnings": [
                        *output.warnings,
                        f"Metric {m.name}={m.value} not present in tool results",
                    ],
                    "confidence": min(output.confidence, 0.2),
                }
            )
    for s in output.sources:
        if s.document_id not in known_document_ids:
            return output.model_copy(
                update={
                    "status": "insufficient_evidence",
                    "warnings": [
                        *output.warnings,
                        f"Unknown document_id {s.document_id}",
                    ],
                    "confidence": min(output.confidence, 0.2),
                }
            )
    return output
