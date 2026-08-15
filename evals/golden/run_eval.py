"""Minimal golden eval runner skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradelab.agents.graph import run_analysis

QUESTIONS = Path(__file__).with_name("questions.jsonl")


@pytest.mark.fast
def test_prediction_case_rejected():
    rows = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    pred = next(r for r in rows if r.get("expect_status") == "rejected")
    out = run_analysis(query=pred["question"])
    assert out["status"] == "rejected"
