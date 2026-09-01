"""Structured agent response + numeric/citation verifier."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
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


_NUMERIC_TOKEN = re.compile(
    r"(?<![\w-])[-+]?(?:\d+[.,]\d+|\d+)%?(?![\w-])",
    flags=re.UNICODE,
)


def _normalize_numeric_token(token: str) -> str:
    percent = token.endswith("%")
    raw = token[:-1] if percent else token
    try:
        value = Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return token
    normalized = format(value.normalize(), "f")
    if normalized == "-0":
        normalized = "0"
    return f"{normalized}%" if percent else normalized


def numeric_tokens(text: str) -> set[str]:
    return {_normalize_numeric_token(match.group(0)) for match in _NUMERIC_TOKEN.finditer(text)}


def evidence_numeric_values(evidence: Any) -> set[str]:
    """Collect explicit numbers plus exact percentage renderings from typed evidence."""
    values: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float, Decimal)):
            normalized = _normalize_numeric_token(str(value))
            values.add(normalized)
            numeric = Decimal(str(value))
            if Decimal("0") <= numeric <= Decimal("1"):
                values.add(_normalize_numeric_token(f"{numeric * 100}%"))
            return
        if isinstance(value, dict):
            for child_key, child in value.items():
                normalized_key = str(child_key).lower()
                if normalized_key == "query":
                    continue
                visit(child, normalized_key)
            return
        if isinstance(value, (list, tuple, set)):
            for child in value:
                visit(child, key)
            return
        if isinstance(value, str):
            if any(part in key for part in ("_id", "hash", "checksum", "uri")):
                return
            values.update(numeric_tokens(value))

    visit(evidence)
    return values


def verify_analysis(
    output: AnalysisOutput,
    *,
    known_metric_values: set[tuple[str, str, str]],
    known_document_ids: set[str],
    known_numeric_values: set[str] | None = None,
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
    if known_numeric_values is not None:
        unsupported = numeric_tokens(output.answer) - known_numeric_values
        if unsupported:
            rendered = ", ".join(sorted(unsupported))
            return output.model_copy(
                update={
                    "status": "insufficient_evidence",
                    "answer": (
                        "Evidencia insuficiente: la síntesis generada contenía cifras "
                        "no respaldadas y fue descartada."
                    ),
                    "warnings": [
                        *output.warnings,
                        f"Unsupported numeric claims in answer: {rendered}",
                    ],
                    "confidence": min(output.confidence, 0.2),
                }
            )
    return output
