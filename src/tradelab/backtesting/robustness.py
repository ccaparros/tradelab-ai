"""Walk-forward, cost/parameter sensitivity, and a naive baseline.

Always runs on the research window (train + validation). Holdout is never used.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from tradelab.backtesting.engine import TradeFill
from tradelab.backtesting.metrics import compute_metrics
from tradelab.backtesting.sessions import with_session_date
from tradelab.backtesting.splits import expanding_walk_forward_windows
from tradelab.backtesting.strategies.registry import StrategySpec


def _metrics_blob(fills: list[TradeFill]) -> dict[str, Any]:
    m = compute_metrics(fills)
    return {
        "trade_count": m["trade_count"],
        "net_pnl": m["net_pnl"],
        "max_drawdown": m["max_drawdown"],
        "win_rate": m["win_rate"],
    }


def run_session_long_baseline(
    df: pd.DataFrame,
    *,
    commission_per_side: float,
    slippage_ticks: int,
    tick_size: float = 0.25,
    multiplier: float = 5.0,
    session_timezone: str = "America/Chicago",
) -> dict[str, Any]:
    """One long per session: first bar open → last bar close, with costs."""
    if df.empty:
        return {"kind": "session_long", "trade_count": 0, "net_pnl": 0.0}
    work = with_session_date(df, session_timezone)
    slip = slippage_ticks * tick_size
    fills: list[TradeFill] = []
    for session, g in work.groupby("session_date", sort=True):
        g = g.sort_values("timestamp_utc")
        if g.empty:
            continue
        first, last = g.iloc[0], g.iloc[-1]
        entry = float(first["open"]) + slip
        exit_px = float(last["close"]) - slip
        pnl_gross = (exit_px - entry) * multiplier
        costs = 2 * commission_per_side
        fills.append(
            TradeFill(
                session_date=str(session),
                side="long",
                entry_ts=str(first["timestamp_utc"]),
                exit_ts=str(last["timestamp_utc"]),
                entry_price=entry,
                exit_price=exit_px,
                qty=1,
                pnl_gross=pnl_gross,
                pnl_net=pnl_gross - costs,
                exit_reason="session_exit",
                split_label="baseline",
            )
        )
    blob = _metrics_blob(fills)
    blob["kind"] = "session_long"
    blob["note"] = "Naive long each RTH session (open→close). Not a trading recommendation."
    return blob


def run_walk_forward(
    research_df: pd.DataFrame,
    spec: StrategySpec,
    params: Any,
    *,
    n_folds: int = 3,
    tick_size: float,
    multiplier: float,
    session_timezone: str,
) -> dict[str, Any]:
    windows = expanding_walk_forward_windows(
        research_df,
        n_folds=n_folds,
        session_timezone=session_timezone,
    )
    if not windows:
        return {"status": "skipped", "reason": "insufficient_sessions", "folds": []}
    folds = []
    oos_pnls: list[float] = []
    for w in windows:
        is_fills = spec.run(
            w["train_df"],
            params,
            split_label=f"wf{w['fold']}_is",
            tick_size=tick_size,
            multiplier=multiplier,
            session_timezone=session_timezone,
        )
        oos_fills = spec.run(
            w["test_df"],
            params,
            split_label=f"wf{w['fold']}_oos",
            tick_size=tick_size,
            multiplier=multiplier,
            session_timezone=session_timezone,
        )
        is_m = _metrics_blob(is_fills)
        oos_m = _metrics_blob(oos_fills)
        oos_pnls.append(float(oos_m["net_pnl"]))
        folds.append(
            {
                "fold": w["fold"],
                "train_start": w["train_start"],
                "train_end": w["train_end"],
                "test_start": w["test_start"],
                "test_end": w["test_end"],
                "train_sessions": w["train_sessions"],
                "test_sessions": w["test_sessions"],
                "is": is_m,
                "oos": oos_m,
            }
        )
    return {
        "status": "ok",
        "scheme": "expanding",
        "n_folds": len(folds),
        "oos_net_pnl_sum": float(sum(oos_pnls)),
        "folds": folds,
        "note": "Walk-forward expanding on train+validation only. Holdout excluded.",
    }


def _strip_label(params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    p = dict(params)
    label = str(p.pop("_label", "variant"))
    return label, p


def neighbor_parameter_sets(strategy_id: str, base: dict[str, Any]) -> list[dict[str, Any]]:
    p = dict(base)
    out: list[dict[str, Any]] = []
    if strategy_id == "orb_atr_intraday":
        other = 30 if int(p.get("opening_range_minutes", 15)) == 15 else 15
        out.append({**p, "opening_range_minutes": other, "_label": f"orb={other}m"})
        sm = float(p.get("stop_risk_mult", 1.0))
        out.append({**p, "stop_risk_mult": round(max(0.15, sm * 0.75), 4), "_label": "stop-25%"})
        tm = float(p.get("target_risk_mult", 2.0))
        out.append({**p, "target_risk_mult": round(tm * 1.25, 4), "_label": "target+25%"})
    elif strategy_id == "vwap_fade_intraday":
        ext = float(p.get("extension_atr", 0.7))
        mx = float(p.get("max_extension_atr", 2.4))
        for delta, lab in ((-0.2, "ext-0.2"), (0.2, "ext+0.2")):
            nxt = round(max(0.2, ext + delta), 4)
            if nxt < mx:
                out.append({**p, "extension_atr": nxt, "_label": lab})
        stop = float(p.get("stop_atr_mult", 0.8))
        out.append({**p, "stop_atr_mult": round(max(0.2, stop * 0.75), 4), "_label": "stop-25%"})
    return out


def cost_parameter_sets(base: dict[str, Any]) -> list[dict[str, Any]]:
    p = dict(base)
    comm = float(p.get("commission_per_side", 0.62))
    slip = int(p.get("slippage_ticks", 1))
    return [
        {**p, "commission_per_side": round(comm * 0.5, 4), "_label": "commission_x0.5"},
        {**p, "commission_per_side": round(comm * 2.0, 4), "_label": "commission_x2"},
        {**p, "slippage_ticks": 0, "_label": "slippage_0"},
        {**p, "slippage_ticks": max(slip, 1) + 1, "_label": "slippage_+1"},
    ]


def run_sensitivity(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    spec: StrategySpec,
    base_params: Any,
    *,
    tick_size: float,
    multiplier: float,
    session_timezone: str,
) -> dict[str, Any]:
    base = base_params.model_dump()
    rows: list[dict[str, Any]] = []
    variants = [("param", x) for x in neighbor_parameter_sets(spec.strategy_id, base)]
    variants += [("cost", x) for x in cost_parameter_sets(base)]
    for kind, raw in variants:
        label, payload = _strip_label(raw)
        try:
            parsed = spec.validate(payload)
        except Exception:
            continue
        train_m = _metrics_blob(
            spec.run(
                train_df,
                parsed,
                split_label="sens_train",
                tick_size=tick_size,
                multiplier=multiplier,
                session_timezone=session_timezone,
            )
        )
        val_m = _metrics_blob(
            spec.run(
                val_df,
                parsed,
                split_label="sens_val",
                tick_size=tick_size,
                multiplier=multiplier,
                session_timezone=session_timezone,
            )
        )
        rows.append(
            {
                "label": label,
                "kind": kind,
                "parameters": parsed.model_dump(),
                "train": train_m,
                "validation": val_m,
            }
        )
    return {
        "status": "ok" if rows else "skipped",
        "base_parameters": base,
        "variants": rows,
        "note": "Neighbors and cost shocks on train/validation only. Holdout excluded.",
    }
