"""Write experiment markdown report to data_catalog/reports/experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_experiment_report(experiment: dict[str, Any]) -> str:
    out_dir = Path("data_catalog/reports/experiments")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{experiment['experiment_id']}.md"
    lines = [
        f"# Experiment {experiment['experiment_id']}",
        "",
        f"- strategy: `{experiment.get('strategy_id')}`",
        f"- integrity_hash: `{experiment.get('integrity_hash')}`",
        f"- holdout_consumed: `{experiment.get('holdout_consumed')}`",
        "",
        "## Metrics by split",
        "",
        "```json",
        str(experiment.get("metrics_by_split")),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
