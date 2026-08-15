"""Experiment metrics (computed in code — never by LLM)."""

from __future__ import annotations

from typing import Any

import numpy as np

from tradelab.backtesting.engine import TradeFill


def compute_metrics(trades: list[TradeFill]) -> dict[str, Any]:
    if not trades:
        return {
            "trade_count": 0,
            "net_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0,
            "sharpe_approx": 0.0,
            "convention_notes": "Sharpe approx uses trade PnL stdev; not annualized.",
        }

    pnls = np.array([t.pnl_net for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    std = float(pnls.std(ddof=1)) if len(pnls) > 1 else 0.0
    sharpe = float(pnls.mean() / std) if std > 0 else 0.0

    return {
        "trade_count": int(len(trades)),
        "net_pnl": float(pnls.sum()),
        "win_rate": float((pnls > 0).mean()),
        "profit_factor": pf if np.isfinite(pf) else None,
        "max_drawdown": float(dd.min()) if len(dd) else 0.0,
        "expectancy": float(pnls.mean()),
        "sharpe_approx": sharpe,
        "convention_notes": "Sharpe approx uses per-trade net PnL mean/std; not annualized.",
    }
