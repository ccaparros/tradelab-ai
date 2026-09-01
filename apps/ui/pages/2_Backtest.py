"""Backtest con selector de estrategia y parámetros según esquema."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st
from helpers import dataset_label, get_json, is_demo

st.set_page_config(page_title="Backtest | TradeLab AI", layout="wide")
st.title("Backtest")
st.caption(
    "Elige dataset y estrategia. Métricas con costes. "
    "El holdout queda bloqueado salvo que lo actives al final. "
    "La rentabilidad no es el criterio de éxito del proyecto."
)

api = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    datasets = get_json(f"{api}/v1/datasets").get("items", [])
    strategies = get_json(f"{api}/v1/strategies").get("items", [])
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo contactar la API ({api}): {exc}")
    st.stop()

usable = [d for d in datasets if d.get("quality_status") == "usable"] or datasets
if not usable:
    st.warning("Sin datasets. Carga el demo o publica canónicos desde Catálogo.")
    st.stop()
if not strategies:
    st.error("La API no devolvió estrategias.")
    st.stop()

ds = st.selectbox(
    "Dataset",
    usable,
    format_func=dataset_label,
    help="Prefiere históricos reales (IBKR) frente al fixture DEMO de 2024.",
)
if is_demo(ds):
    st.warning("Dataset DEMO (unas horas de 2024). Para la defensa elige MES/MNQ reales.")

strat_labels = {f"{s['name']}  ({s['strategy_id']})": s for s in strategies}
choice = st.selectbox("Estrategia", list(strat_labels.keys()))
strat = strat_labels[choice]
st.info(strat.get("description") or strat["strategy_id"])

HIDDEN_PARAMS = {"max_entries_per_session"}


def _widget_for(name: str, spec: dict[str, Any], *, strategy_id: str) -> Any:
    default = spec.get("default")
    title = spec.get("title") or name
    key = f"p_{strategy_id}_{name}"
    enum = spec.get("enum")
    if enum:
        idx = enum.index(default) if default in enum else 0
        return st.selectbox(title, enum, index=idx, key=key)
    typ = spec.get("type")
    ge = spec.get("minimum")
    le = spec.get("maximum")
    if typ == "integer":
        return int(
            st.number_input(
                title,
                min_value=int(ge) if ge is not None else 0,
                max_value=int(le) if le is not None else 10_000,
                value=int(default) if default is not None else 0,
                step=1,
                key=key,
            )
        )
    if typ == "number":
        return float(
            st.number_input(
                title,
                min_value=float(ge) if ge is not None else 0.0,
                max_value=float(le) if le is not None else 1_000_000.0,
                value=float(default) if default is not None else 0.0,
                key=key,
            )
        )
    return st.text_input(title, value=str(default or ""), key=key)


schema = strat.get("allowed_parameters_schema") or {}
props: dict[str, Any] = schema.get("properties") or {}
st.markdown("#### Parámetros")
params: dict[str, Any] = {}
for name, spec in props.items():
    if name in HIDDEN_PARAMS:
        if spec.get("default") is not None:
            params[name] = spec["default"]
        continue
    params[name] = _widget_for(name, spec, strategy_id=strat["strategy_id"])

consume_holdout = st.checkbox(
    "Consumir holdout (solo lectura final; no para elegir parámetros)",
    value=False,
)

if st.button("Ejecutar backtest", type="primary"):
    r = httpx.post(
        f"{api}/v1/experiments",
        json={
            "dataset_id": ds["dataset_id"],
            "strategy_id": strat["strategy_id"],
            "parameters": params,
            "consume_holdout": consume_holdout,
        },
        timeout=180,
    )
    if r.status_code >= 400:
        st.error(r.text)
    else:
        body = r.json()
        st.success(
            f"**{strat['name']}** · hash `{str(body.get('integrity_hash') or '')[:12]}…`  \n"
            f"id `{body['experiment_id']}` — disponible en **Análisis**."
        )
        st.subheader("Métricas por split")
        by = body.get("metrics_by_split") or {}
        cols = st.columns(3)
        for i, split in enumerate(("train", "validation", "holdout")):
            blob = by.get(split) or {}
            with cols[i]:
                st.markdown(f"**{split}**")
                if blob.get("blocked"):
                    st.caption("bloqueado")
                else:
                    st.metric("net PnL", f"{blob.get('net_pnl', '—')}")
                    st.caption(
                        f"trades={blob.get('trade_count', '—')} · DD={blob.get('max_drawdown', '—')}"
                    )
        wf = body.get("walk_forward") or {}
        st.subheader("Walk-forward (sin holdout)")
        if wf.get("status") != "ok":
            st.caption(
                f"No aplicable: {wf.get('reason') or wf.get('status')}. Hace falta más de una sesión."
            )
        else:
            st.caption(
                f"Esquema expanding · {wf.get('n_folds')} folds · "
                f"OOS net PnL suma `{wf.get('oos_net_pnl_sum')}`"
            )
            fold_rows = []
            for f in wf.get("folds") or []:
                fold_rows.append(
                    {
                        "fold": f.get("fold"),
                        "train": f"{f.get('train_start')} → {f.get('train_end')}",
                        "test": f"{f.get('test_start')} → {f.get('test_end')}",
                        "IS pnl": (f.get("is") or {}).get("net_pnl"),
                        "OOS pnl": (f.get("oos") or {}).get("net_pnl"),
                        "OOS trades": (f.get("oos") or {}).get("trade_count"),
                    }
                )
            st.dataframe(fold_rows, use_container_width=True, hide_index=True)
        base = body.get("baseline") or {}
        st.subheader("Baseline (largo de sesión)")
        bcols = st.columns(2)
        for i, split in enumerate(("train", "validation")):
            blob = base.get(split) or {}
            with bcols[i]:
                st.metric(f"{split} net PnL", f"{blob.get('net_pnl', '—')}")
                st.caption(f"trades={blob.get('trade_count', '—')}")
        sens = body.get("sensitivity") or {}
        st.subheader("Sensibilidad a costes y parámetros cercanos")
        st.caption("Solo train/validation. El holdout no entra en estas pruebas.")
        srows = []
        for v in sens.get("variants") or []:
            srows.append(
                {
                    "variante": v.get("label"),
                    "tipo": v.get("kind"),
                    "train PnL": (v.get("train") or {}).get("net_pnl"),
                    "val PnL": (v.get("validation") or {}).get("net_pnl"),
                    "val trades": (v.get("validation") or {}).get("trade_count"),
                }
            )
        if srows:
            st.dataframe(srows, use_container_width=True, hide_index=True)
        else:
            st.caption("Sin variantes (dataset demasiado corto o parámetros inválidos).")
        with st.expander("JSON métricas / robustez"):
            st.json(
                {
                    "metrics_by_split": by,
                    "walk_forward": wf,
                    "sensitivity": sens,
                    "baseline": base,
                }
            )
