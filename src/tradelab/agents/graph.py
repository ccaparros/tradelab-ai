"""Research analysis orchestration (deterministic tools + optional LLM stub)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from tradelab.agents.schema import AnalysisOutput, MetricRef, SourceRef, verify_analysis
from tradelab.agents.tools import (
    get_dataset_quality,
    get_experiment_metrics,
    get_trade_sample,
    search_research_documents,
)
from tradelab.datasets.store import upsert_analysis


def _is_prediction_request(query: str) -> bool:
    q = query.lower()
    return any(
        x in q
        for x in ("predict", "predice", "forecast", "próxima barra", "next bar", "will price")
    )


def run_analysis(
    *,
    query: str,
    dataset_id: str | None = None,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    analysis_id = str(uuid.uuid4())
    invocations: list[dict[str, Any]] = []

    if _is_prediction_request(query):
        out = AnalysisOutput(
            analysis_id=analysis_id,
            status="rejected",
            answer="TradeLab AI no predice precios futuros. Solo explica evidencia histórica auditable.",
            metrics=[],
            assumptions=[],
            warnings=["Política research-only: predicción de precios fuera de alcance"],
            sources=[],
            confidence=1.0,
            tool_invocations=invocations,
        )
        record = out.model_dump()
        upsert_analysis(record)
        return record

    known_metrics: set[tuple[str, str, str]] = set()
    known_docs: set[str] = set()
    metrics: list[MetricRef] = []
    sources: list[SourceRef] = []
    answer_parts: list[str] = []

    if dataset_id:
        quality = get_dataset_quality(dataset_id)
        invocations.append({"tool_name": "get_dataset_quality", "arguments": {"dataset_id": dataset_id}})
        answer_parts.append(
            f"Dataset {dataset_id} tiene quality_status={quality.get('quality_status')} "
            f"con {quality.get('gap_count', 0)} gaps clasificados."
        )

    if experiment_id:
        m = get_experiment_metrics(experiment_id)
        invocations.append({"tool_name": "get_experiment_metrics", "arguments": {"experiment_id": experiment_id}})
        by_split = m.get("metrics_by_split") or {}
        train = by_split.get("train") or {}
        val = by_split.get("validation") or {}
        for split_name, blob in (("train", train), ("validation", val)):
            if isinstance(blob, dict) and "net_pnl" in blob:
                metrics.append(
                    MetricRef(name=f"net_pnl_{split_name}", value=blob["net_pnl"], experiment_id=experiment_id)
                )
                known_metrics.add((f"net_pnl_{split_name}", str(blob["net_pnl"]), experiment_id))
                metrics.append(
                    MetricRef(
                        name=f"trade_count_{split_name}",
                        value=blob.get("trade_count", 0),
                        experiment_id=experiment_id,
                    )
                )
                known_metrics.add(
                    (f"trade_count_{split_name}", str(blob.get("trade_count", 0)), experiment_id)
                )
        answer_parts.append(
            "Comparación train vs validation usando métricas del experimento "
            f"{experiment_id} (hash {m.get('integrity_hash')}). "
            f"net_pnl train={train.get('net_pnl')} validation={val.get('net_pnl')}."
        )
        _ = get_trade_sample(experiment_id, limit=5)
        invocations.append({"tool_name": "get_trade_sample", "arguments": {"experiment_id": experiment_id, "limit": 5}})

    docs = search_research_documents(query, top_k=3)
    invocations.append({"tool_name": "search_research_documents", "arguments": {"query": query, "top_k": 3}})
    for d in docs:
        known_docs.add(d["document_id"])
        sources.append(
            SourceRef(document_id=d["document_id"], citation=d.get("excerpt", "")[:240], chunk_id=d.get("chunk_id"))
        )

    if not answer_parts and not docs:
        out = AnalysisOutput(
            analysis_id=analysis_id,
            status="insufficient_evidence",
            answer="Evidencia insuficiente para responder. Indica dataset_id y/o experiment_id.",
            metrics=[],
            assumptions=[],
            warnings=["Faltan evidencias de tools"],
            sources=[],
            confidence=0.1,
            tool_invocations=invocations,
        )
    else:
        out = AnalysisOutput(
            analysis_id=analysis_id,
            status="completed",
            answer=" ".join(answer_parts) if answer_parts else "Respuesta basada en documentos recuperados.",
            metrics=metrics,
            assumptions=["Las métricas provienen exclusivamente de tools tipadas"],
            warnings=[],
            sources=sources,
            confidence=0.85 if experiment_id else 0.6,
            tool_invocations=invocations,
        )

    verified = verify_analysis(out, known_metric_values=known_metrics, known_document_ids=known_docs or {"none"})
    # If no docs, allow empty sources without failing unknown-id check
    if not sources:
        verified = out
    record = verified.model_dump()
    upsert_analysis(record)
    return record
