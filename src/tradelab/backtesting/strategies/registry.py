"""Strategy registry — allowlisted research strategies only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tradelab.backtesting.engine import TradeFill, run_orb_atr
from tradelab.backtesting.strategies import orb_atr, vwap_fade


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    name: str
    version: str
    description: str
    validate: Callable[[dict[str, Any]], Any]
    run: Callable[..., list[TradeFill]]
    schema: Callable[[], dict[str, Any]]


REGISTRY: dict[str, StrategySpec] = {
    orb_atr.STRATEGY_ID: StrategySpec(
        strategy_id=orb_atr.STRATEGY_ID,
        name="Opening Range Breakout + ATR",
        version=orb_atr.STRATEGY_VERSION,
        description=(
            "Ruptura del rango de apertura con filtro de volatilidad ATR. "
            "Una entrada por sesión, stop/objetivo como múltiplos del rango, salida de sesión."
        ),
        validate=orb_atr.validate_parameters,
        run=run_orb_atr,
        schema=orb_atr.allowed_parameters_schema,
    ),
    vwap_fade.STRATEGY_ID: StrategySpec(
        strategy_id=vwap_fade.STRATEGY_ID,
        name="Fade a VWAP de sesión",
        version=vwap_fade.STRATEGY_VERSION,
        description=(
            "Mean-reversion intradía: si el cierre previo se aleja del VWAP de sesión "
            "entre extension_atr y max_extension_atr, se entra a favor de la reversión "
            "hacia el VWAP. No se opera en días de tendencia extrema. ATR y VWAP van "
            "desplazados 1 barra (anti look-ahead)."
        ),
        validate=vwap_fade.validate_parameters,
        run=vwap_fade.run_vwap_fade,
        schema=vwap_fade.allowed_parameters_schema,
    ),
}


def get_strategy(strategy_id: str) -> StrategySpec:
    spec = REGISTRY.get(strategy_id)
    if not spec:
        allowed = ", ".join(sorted(REGISTRY))
        raise ValueError(f"unsupported strategy '{strategy_id}'. Allowed: {allowed}")
    return spec


def list_strategy_specs() -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": s.strategy_id,
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "allowed_parameters_schema": s.schema(),
        }
        for s in REGISTRY.values()
    ]
