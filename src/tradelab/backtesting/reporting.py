"""Write experiment markdown report to data_catalog/reports/experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


def write_experiment_report(experiment: dict[str, Any]) -> str:
    out_dir = Path("data_catalog/reports/experiments")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{experiment['experiment_id']}.md"
    wf = experiment.get("walk_forward") or {}
    sens = experiment.get("sensitivity") or {}
    lines = [
        f"# Experiment {experiment['experiment_id']}",
        "",
        f"- strategy: `{experiment.get('strategy_id')}`",
        f"- integrity_hash: `{experiment.get('integrity_hash')}`",
        f"- holdout_consumed: `{experiment.get('holdout_consumed')}`",
        f"- dataset_id: `{experiment.get('dataset_id')}`",
        "",
        "## Metrics by split",
        "",
        "```json",
        _json(experiment.get("metrics_by_split")),
        "```",
        "",
        "## Baseline (session long)",
        "",
        "Naive long each session open→close with the same commission/slippage. Holdout excluded.",
        "",
        "```json",
        _json(experiment.get("baseline")),
        "```",
        "",
        "## Walk-forward (expanding, train+validation only)",
        "",
        f"Status: `{wf.get('status')}` · OOS net PnL sum: `{wf.get('oos_net_pnl_sum')}`",
        "",
        "```json",
        _json(wf),
        "```",
        "",
        "## Sensitivity (costs and nearby parameters)",
        "",
        f"Status: `{sens.get('status')}` · variants: `{len(sens.get('variants') or [])}`",
        "",
        "```json",
        _json(sens),
        "```",
        "",
        "Walk-forward and sensitivity never read the holdout split.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    try:
        from tradelab.rag.indexer import index_file

        index_file(path)
    except Exception:
        pass
    return str(path)
