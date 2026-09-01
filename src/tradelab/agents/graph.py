"""Research analysis orchestration — tools first, DeepSeek synthesizes, verifier guards numbers."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from tradelab.agents.llm import chat_completion, llm_configured
from tradelab.agents.schema import (
    AnalysisOutput,
    MetricRef,
    SourceRef,
    evidence_numeric_values,
    verify_analysis,
)
from tradelab.agents.tools import (
    get_dataset_quality,
    get_experiment_metrics,
    get_trade_sample,
    search_research_documents,
)
from tradelab.datasets.store import upsert_analysis
from tradelab.observability.settings import get_settings
from tradelab.observability.tracing import span_fields


def _is_prediction_request(query: str) -> bool:
    q = query.lower()
    return any(
        x in q
        for x in (
            "predict",
            "predice",
            "forecast",
            "próxima barra",
            "proxima barra",
            "next bar",
            "will price",
            "will price go",
            "precio subirá",
            "precio subira",
            "subirá el precio",
            "subira el precio",
        )
    )


def _is_live_trading_request(query: str) -> bool:
    q = query.lower()
    return any(
        x in q
        for x in (
            "place a live",
            "place_order",
            "market order",
            "orden de mercado",
            "submit an order",
            "submit order",
            "envía una orden",
            "envia una orden",
            "coloca una orden",
            "orden real",
            "place live order",
            "send a live order",
            "execute mes",
            "execute mnq",
            "ejecuta compras",
            "cancel my open",
            "cancel orders",
            "cancela automáticamente",
            "cancela automaticamente",
            "órdenes abiertas",
            "ordenes abiertas",
            "act as a broker",
            "actúa como broker",
            "actua como broker",
            "ibkr paper account now",
            "cuenta paper de ibkr",
            "orden a la cuenta paper",
        )
    )


def _asks_bound_experiment_metrics(query: str) -> bool:
    """Numeric/experiment-bound questions require an experiment_id."""
    q = query.lower()
    return any(
        x in q
        for x in (
            "experiment results",
            "resultado del experimento",
            "resultados del experimento",
            "net pnl",
            "net_pnl",
            "cuál es el net",
            "cual es el net",
            "integrity hash of the experiment",
            "integrity hash del experimento",
            "max drawdown on train",
            "max drawdown en train",
            "profit factor on validation",
            "profit factor en validation",
        )
    )


def _load_system_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "prompts" / "system_research.j2"
    base = path.read_text(encoding="utf-8") if path.exists() else ""
    return (
        base + "\n\nYou MUST reply with a JSON object only, keys: "
        "answer (string), assumptions (string[]), warnings (string[]), confidence (0..1). "
        "Do NOT invent financial figures. Use ONLY numbers present in EVIDENCE. "
        "If evidence is insufficient, say so clearly. Research-only: never suggest live orders."
    )


def _collect_evidence(
    *,
    query: str,
    dataset_id: str | None,
    experiment_id: str | None,
) -> tuple[
    list[dict[str, Any]],
    list[MetricRef],
    list[SourceRef],
    set[tuple[str, str, str]],
    set[str],
    dict[str, Any],
]:
    invocations: list[dict[str, Any]] = []
    metrics: list[MetricRef] = []
    sources: list[SourceRef] = []
    known_metrics: set[tuple[str, str, str]] = set()
    known_docs: set[str] = set()
    pack: dict[str, Any] = {
        "query": query,
        "dataset": None,
        "experiment": None,
        "trades_sample": [],
        "documents": [],
    }

    if dataset_id:
        quality = get_dataset_quality(dataset_id)
        invocations.append(
            {"tool_name": "get_dataset_quality", "arguments": {"dataset_id": dataset_id}}
        )
        pack["dataset"] = quality

    if experiment_id:
        m = get_experiment_metrics(experiment_id)
        invocations.append(
            {"tool_name": "get_experiment_metrics", "arguments": {"experiment_id": experiment_id}}
        )
        pack["experiment"] = m
        by_split = m.get("metrics_by_split") or {}
        for split_name, blob in by_split.items():
            if not isinstance(blob, dict) or blob.get("blocked"):
                continue
            for key in (
                "net_pnl",
                "trade_count",
                "win_rate",
                "max_drawdown",
                "profit_factor",
                "expectancy",
            ):
                if key in blob:
                    name = f"{key}_{split_name}"
                    metrics.append(
                        MetricRef(name=name, value=blob[key], experiment_id=experiment_id)
                    )
                    known_metrics.add((name, str(blob[key]), experiment_id))
        trades = get_trade_sample(experiment_id, limit=5)
        invocations.append(
            {
                "tool_name": "get_trade_sample",
                "arguments": {"experiment_id": experiment_id, "limit": 5},
            }
        )
        pack["trades_sample"] = trades

    docs = search_research_documents(query, top_k=3)
    invocations.append(
        {"tool_name": "search_research_documents", "arguments": {"query": query, "top_k": 3}}
    )
    pack["documents"] = docs
    for d in docs:
        known_docs.add(d["document_id"])
        sources.append(
            SourceRef(
                document_id=d["document_id"],
                citation=d.get("excerpt", "")[:240],
                chunk_id=d.get("chunk_id"),
            )
        )

    return invocations, metrics, sources, known_metrics, known_docs, pack


def _fallback_answer(pack: dict[str, Any], metrics: list[MetricRef]) -> str:
    parts: list[str] = []
    if pack.get("dataset"):
        d = pack["dataset"]
        parts.append(
            f"Dataset {d.get('dataset_id')} status={d.get('quality_status')} gaps={d.get('gap_count', 0)}."
        )
    if pack.get("experiment"):
        e = pack["experiment"]
        by = e.get("metrics_by_split") or {}
        train, val = by.get("train") or {}, by.get("validation") or {}
        parts.append(
            f"Experimento {e.get('experiment_id')} hash={e.get('integrity_hash')}. "
            f"net_pnl train={train.get('net_pnl')} validation={val.get('net_pnl')}."
        )
    if not parts and metrics:
        parts.append("Métricas recuperadas de tools tipadas.")
    return " ".join(parts) if parts else "Evidencia insuficiente."


class AgentState(TypedDict, total=False):
    query: str
    dataset_id: str | None
    experiment_id: str | None
    analysis_id: str
    record: dict[str, Any]
    done: bool
    graph: str


def _persist(out: AnalysisOutput, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    record = out.model_dump()
    if extra:
        record.update(extra)
    upsert_analysis(record)
    return record


def _node_guards(state: AgentState) -> AgentState:
    query = state["query"]
    analysis_id = state["analysis_id"]
    experiment_id = state.get("experiment_id")

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
            tool_invocations=[],
        )
        rec = _persist(out, {"llm": {"provider": "guard"}, "graph": "langgraph"})
        return {**state, "record": rec, "done": True, "graph": "langgraph"}

    if _is_live_trading_request(query):
        out = AnalysisOutput(
            analysis_id=analysis_id,
            status="rejected",
            answer=(
                "TradeLab AI es solo investigación: no envía, modifica ni cancela órdenes. "
                "Usa el catálogo, backtests y el copiloto sobre evidencia histórica."
            ),
            metrics=[],
            assumptions=[],
            warnings=["Política research-only: trading en vivo fuera de alcance"],
            sources=[],
            confidence=1.0,
            tool_invocations=[],
        )
        rec = _persist(out, {"llm": {"provider": "guard"}, "graph": "langgraph"})
        return {**state, "record": rec, "done": True, "graph": "langgraph"}

    if _asks_bound_experiment_metrics(query) and not experiment_id:
        out = AnalysisOutput(
            analysis_id=analysis_id,
            status="insufficient_evidence",
            answer="Evidencia insuficiente: indica experiment_id para consultar métricas del experimento.",
            metrics=[],
            assumptions=[],
            warnings=["Falta experiment_id para métricas numéricas"],
            sources=[],
            confidence=0.1,
            tool_invocations=[],
        )
        rec = _persist(out, {"llm": {"provider": "guard"}, "graph": "langgraph"})
        return {**state, "record": rec, "done": True, "graph": "langgraph"}

    return {**state, "done": False, "graph": "langgraph"}


def _node_research(state: AgentState) -> AgentState:
    query = state["query"]
    analysis_id = state["analysis_id"]
    dataset_id = state.get("dataset_id")
    experiment_id = state.get("experiment_id")

    invocations, metrics, sources, known_metrics, known_docs, pack = _collect_evidence(
        query=query, dataset_id=dataset_id, experiment_id=experiment_id
    )

    if not metrics and not pack.get("dataset") and not pack.get("documents"):
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
        rec = _persist(out, {"llm": {"provider": "stub"}, "graph": "langgraph"})
        return {**state, "record": rec, "done": True}

    llm_meta: dict[str, Any] = {"provider": "stub"}
    assumptions = ["Las métricas provienen exclusivamente de tools tipadas"]
    warnings: list[str] = []
    confidence = 0.85 if experiment_id else 0.6
    answer = _fallback_answer(pack, metrics)

    if llm_configured():
        try:
            system = _load_system_prompt()
            user = (
                "USER_QUESTION:\n"
                f"{query}\n\n"
                "EVIDENCE (JSON from typed tools — numbers are ground truth):\n"
                f"{json.dumps(pack, default=str)}\n\n"
                "Write a clear Spanish research answer grounded only in EVIDENCE."
            )
            result = chat_completion(system=system, user=user)
            parsed = result["parsed"]
            if isinstance(parsed.get("answer"), str) and parsed["answer"].strip():
                answer = parsed["answer"].strip()
            if isinstance(parsed.get("assumptions"), list):
                assumptions = [str(a) for a in parsed["assumptions"]] or assumptions
            if isinstance(parsed.get("warnings"), list):
                warnings = [str(w) for w in parsed["warnings"]]
            if isinstance(parsed.get("confidence"), (int, float)):
                confidence = float(max(0.0, min(1.0, parsed["confidence"])))
            llm_meta = {
                "provider": "openai_compatible",
                "model": result.get("model"),
                "base_url": result.get("base_url"),
                "usage": result.get("usage"),
            }
            llm_meta["trace"] = span_fields(
                analysis_id=analysis_id,
                experiment_id=experiment_id,
                token_usage=result.get("usage"),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"LLM unavailable, using deterministic fallback: {exc}")
            llm_meta = {"provider": "fallback", "error": str(exc)}
    else:
        warnings.append("LLM_API_KEY not set — deterministic synthesis only")

    out = AnalysisOutput(
        analysis_id=analysis_id,
        status="completed",
        answer=answer,
        metrics=metrics,
        assumptions=assumptions,
        warnings=warnings,
        sources=sources,
        confidence=confidence,
        tool_invocations=invocations,
    )
    verified = verify_analysis(
        out,
        known_metric_values=known_metrics,
        known_document_ids=known_docs or {"none"},
        known_numeric_values=evidence_numeric_values(pack),
    )
    record = _persist(verified, {"llm": llm_meta, "graph": "langgraph"})
    return {**state, "record": record, "done": True}


def _route_after_guards(state: AgentState) -> str:
    return "end" if state.get("done") else "research"


def _compile_graph():
    builder = StateGraph(AgentState)
    builder.add_node("guards", _node_guards)
    builder.add_node("research", _node_research)
    builder.add_edge(START, "guards")
    builder.add_conditional_edges(
        "guards",
        _route_after_guards,
        {"end": END, "research": "research"},
    )
    builder.add_edge("research", END)
    return builder.compile(checkpointer=MemorySaver())


_ANALYSIS_GRAPH = _compile_graph()


def run_analysis(
    *,
    query: str,
    dataset_id: str | None = None,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    get_settings.cache_clear()
    analysis_id = str(uuid.uuid4())
    result = _ANALYSIS_GRAPH.invoke(
        {
            "query": query,
            "dataset_id": dataset_id,
            "experiment_id": experiment_id,
            "analysis_id": analysis_id,
            "done": False,
        },
        config={"configurable": {"thread_id": analysis_id}},
    )
    return result["record"]
