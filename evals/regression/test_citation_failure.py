"""Regression: citation failure must surface as insufficient_evidence."""

from __future__ import annotations

import pytest

from tradelab.agents.schema import AnalysisOutput, SourceRef, verify_analysis


@pytest.mark.fast
def test_unknown_citation_regression():
    out = AnalysisOutput(
        analysis_id="reg1",
        status="completed",
        answer="Invented citation",
        sources=[SourceRef(document_id="does-not-exist", citation="fake")],
        confidence=0.99,
    )
    verified = verify_analysis(out, known_metric_values=set(), known_document_ids={"real-doc"})
    assert verified.status == "insufficient_evidence"
