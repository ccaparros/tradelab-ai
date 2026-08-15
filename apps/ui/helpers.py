"""Etiquetas legibles para selectores de la UI Streamlit."""

from __future__ import annotations

from typing import Any

NONE_DATASET = "— Sin dataset (solo políticas / informes) —"
NONE_EXPERIMENT = "— Sin experimento (sin métricas de backtest) —"


def _short(uid: str | None, n: int = 8) -> str:
    if not uid:
        return "?"
    return str(uid)[:n]


def _coverage(ds: dict[str, Any]) -> str:
    start = str(ds.get("coverage_start_utc") or "")[:10]
    end = str(ds.get("coverage_end_utc") or "")[:10]
    if start and end:
        return f"{start} → {end}"
    return "sin cobertura"


def is_demo(ds: dict[str, Any]) -> bool:
    return bool((ds.get("lineage") or {}).get("demo"))


def preferred_source(ds: dict[str, Any]) -> str:
    return str(
        ds.get("preferred_source")
        or (ds.get("lineage") or {}).get("preferred_source")
        or "?"
    )


def dataset_label(ds: dict[str, Any]) -> str:
    instrument = ds.get("instrument") or "?"
    month = ds.get("contract_month") or ""
    status = ds.get("quality_status") or "?"
    tag = "DEMO" if is_demo(ds) else "real"
    return (
        f"{instrument} {month} · {tag} · {status} · "
        f"{preferred_source(ds)} · {_coverage(ds)} · {_short(ds.get('dataset_id'))}"
    )


def experiment_label(exp: dict[str, Any], datasets_by_id: dict[str, dict[str, Any]] | None = None) -> str:
    datasets_by_id = datasets_by_id or {}
    ds = datasets_by_id.get(str(exp.get("dataset_id")), {})
    instrument = ds.get("instrument") or "?"
    by = exp.get("metrics_by_split") or {}
    train = by.get("train") if isinstance(by.get("train"), dict) else {}
    val = by.get("validation") if isinstance(by.get("validation"), dict) else {}
    strategy = exp.get("strategy_id") or "orb_atr"
    holdout = "holdout leído" if exp.get("holdout_consumed") else "holdout bloqueado"
    return (
        f"{instrument} · {strategy} · "
        f"train PnL={train.get('net_pnl', '—')} · val PnL={val.get('net_pnl', '—')} · "
        f"{holdout} · {_short(exp.get('experiment_id'))}"
    )


def fetch_json(client, path: str) -> dict[str, Any]:
    r = client.get(path, timeout=30)
    r.raise_for_status()
    return r.json()
