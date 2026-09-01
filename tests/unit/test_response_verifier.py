"""Response verifier unit tests."""

from __future__ import annotations

import pytest

from tradelab.agents.schema import (
    AnalysisOutput,
    MetricRef,
    SourceRef,
    evidence_numeric_values,
    verify_analysis,
)


@pytest.mark.unit
def test_rejects_hallucinated_metric():
    out = AnalysisOutput(
        analysis_id="a1",
        status="completed",
        answer="x",
        metrics=[MetricRef(name="net_pnl", value=999.0, experiment_id="e1")],
        sources=[],
        confidence=0.9,
    )
    verified = verify_analysis(out, known_metric_values=set(), known_document_ids=set())
    assert verified.status == "insufficient_evidence"


@pytest.mark.unit
def test_rejects_unknown_document():
    out = AnalysisOutput(
        analysis_id="a1",
        status="completed",
        answer="x",
        metrics=[],
        sources=[SourceRef(document_id="missing", citation="hi")],
        confidence=0.9,
    )
    verified = verify_analysis(out, known_metric_values=set(), known_document_ids={"real"})
    assert verified.status == "insufficient_evidence"


@pytest.mark.unit
def test_numeric_evidence_excludes_untrusted_question_numbers():
    values = evidence_numeric_values(
        {
            "query": "¿Está confirmado un beneficio de 999.99?",
            "experiment": {"net_pnl": 12.5},
        }
    )
    assert "12.5" in values
    assert "999.99" not in values
