"""Copiloto: selectores de dataset y experimento, no UUIDs a mano."""

from __future__ import annotations

import os

import httpx
import streamlit as st

from helpers import (
    NONE_DATASET,
    NONE_EXPERIMENT,
    dataset_label,
    experiment_label,
    is_demo,
    preferred_source,
)

st.set_page_config(page_title="Análisis | TradeLab AI", layout="wide")
st.title("Copiloto de investigación")
st.caption("Las cifras salen de tools deterministas. El modelo solo interpreta evidencia citada.")

api = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    with httpx.Client(base_url=api) as client:
        datasets = client.get("/v1/datasets", timeout=30).json().get("items", [])
        experiments = client.get("/v1/experiments", timeout=30).json().get("items", [])
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo contactar la API ({api}): {exc}")
    st.stop()

datasets_by_id = {str(d["dataset_id"]): d for d in datasets}

st.markdown("#### 1. Contexto de evidencia")
st.caption(
    "Elige **qué** quieres que consulte el copiloto. "
    "Sin dataset ni experimento solo puede citar políticas e informes indexados "
    "(no podrá responder net PnL ni calidad de barras)."
)

ds_options = [NONE_DATASET] + [dataset_label(d) for d in datasets]
ds_choice = st.selectbox("Dataset", ds_options, help="Fixture DEMO vs histórico real IBKR/NT.")
dataset_id = None
selected_ds = None
if ds_choice != NONE_DATASET:
    selected_ds = next(d for d in datasets if dataset_label(d) == ds_choice)
    dataset_id = str(selected_ds["dataset_id"])

filtered_exps = experiments
if dataset_id:
    filtered_exps = [e for e in experiments if str(e.get("dataset_id")) == dataset_id]

exp_options = [NONE_EXPERIMENT] + [experiment_label(e, datasets_by_id) for e in filtered_exps]
if dataset_id and not filtered_exps:
    st.info("Este dataset aún no tiene backtests. Ejecuta uno en la página **Backtest** o deja el experimento vacío.")

exp_choice = st.selectbox(
    "Experimento (backtest)",
    exp_options,
    help="Necesario para comparar train vs validation, drawdown, número de trades, etc.",
)
experiment_id = None
selected_exp = None
if exp_choice != NONE_EXPERIMENT and filtered_exps:
    selected_exp = next(
        e for e in filtered_exps if experiment_label(e, datasets_by_id) == exp_choice
    )
    experiment_id = str(selected_exp["experiment_id"])

with st.expander("Detalle del contexto seleccionado", expanded=bool(dataset_id or experiment_id)):
    col_a, col_b = st.columns(2)
    with col_a:
        if selected_ds:
            st.markdown(
                f"**Dataset** `{selected_ds.get('instrument')} {selected_ds.get('contract_month')}`  \n"
                f"- Tipo: **{'DEMO (fixture 2024)' if is_demo(selected_ds) else 'histórico real'}**  \n"
                f"- Calidad: `{selected_ds.get('quality_status')}`  \n"
                f"- Fuente: `{preferred_source(selected_ds)}`  \n"
                f"- Cobertura: `{str(selected_ds.get('coverage_start_utc') or '')[:10]}` → "
                f"`{str(selected_ds.get('coverage_end_utc') or '')[:10]}`  \n"
                f"- id: `{selected_ds['dataset_id']}`"
            )
        else:
            st.markdown("**Dataset:** ninguno. El copiloto no consultará calidad de barras.")
    with col_b:
        if selected_exp:
            by = selected_exp.get("metrics_by_split") or {}
            train = by.get("train") if isinstance(by.get("train"), dict) else {}
            val = by.get("validation") if isinstance(by.get("validation"), dict) else {}
            st.markdown(
                f"**Experimento** `{selected_exp.get('strategy_id')}`  \n"
                f"- Train net PnL: `{train.get('net_pnl', '—')}`  \n"
                f"- Validation net PnL: `{val.get('net_pnl', '—')}`  \n"
                f"- Holdout: `{'consumido' if selected_exp.get('holdout_consumed') else 'bloqueado'}`  \n"
                f"- id: `{selected_exp['experiment_id']}`"
            )
        else:
            st.markdown("**Experimento:** ninguno. Preguntas de métricas devolverán evidencia insuficiente.")

st.markdown("#### 2. Pregunta")
query = st.text_area(
    "Pregunta de investigación",
    "¿Por qué el resultado de validation es distinto de train y qué evidencia lo demuestra?",
    height=110,
)

if not dataset_id and not experiment_id:
    st.warning("Sin dataset ni experimento el análisis se limita a documentos (políticas, ADRs, informes).")

if st.button("Analizar", type="primary", disabled=not query.strip()):
    payload: dict = {"query": query.strip()}
    if dataset_id:
        payload["dataset_id"] = dataset_id
    if experiment_id:
        payload["experiment_id"] = experiment_id
    with st.spinner("Consultando tools y sintetizando respuesta…"):
        r = httpx.post(f"{api}/v1/analysis", json=payload, timeout=120)
    if r.status_code >= 400:
        st.error(r.text)
        st.stop()
    body = r.json()
    status = body.get("status")
    if status == "rejected":
        st.error(f"Rechazado: {body.get('answer')}")
    elif status == "insufficient_evidence":
        st.warning(body.get("answer"))
    else:
        st.success(f"Estado: {status}")
        st.markdown(body.get("answer") or "")

    tabs = st.tabs(["Métricas (tools)", "Fuentes citadas", "Tools invocadas", "JSON"])
    with tabs[0]:
        metrics = body.get("metrics") or []
        if metrics:
            st.dataframe(metrics, use_container_width=True, hide_index=True)
        else:
            st.caption("Sin métricas: no se pasó un experimento o el holdout está bloqueado.")
    with tabs[1]:
        sources = body.get("sources") or []
        if not sources:
            st.caption("Sin citas.")
        for src in sources:
            st.markdown(f"**{src.get('title') or src.get('document_id', '')[:8]}**")
            st.caption(src.get("citation") or src.get("excerpt") or "")
    with tabs[2]:
        st.json(body.get("tool_invocations") or [])
    with tabs[3]:
        st.json(body)
