"""Catálogo de datasets canónicos con etiquetas legibles."""

from __future__ import annotations

import os

import httpx
import streamlit as st

from helpers import dataset_label, get_json, is_demo, preferred_source

st.set_page_config(page_title="Catálogo | TradeLab AI", layout="wide")
st.title("Catálogo y calidad")
st.caption("Elige un dataset por instrumento, tipo (DEMO vs real) y cobertura. No hace falta copiar el UUID.")

api = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    datasets = get_json(f"{api}/v1/datasets").get("items", [])
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo contactar la API ({api}): {exc}")
    st.stop()

if not datasets:
    st.warning("No hay datasets. Ejecuta `tradelab-load-demo` o publica canónicos IBKR/NT.")
    st.stop()

labels = {dataset_label(d): d for d in datasets}
choice = st.selectbox("Dataset", list(labels.keys()))
ds = labels[choice]

kind = "DEMO (fixture corto, no uses esto para la defensa con datos reales)" if is_demo(ds) else "Histórico real"
st.info(
    f"**{ds.get('instrument')} {ds.get('contract_month')}** · {kind}  \n"
    f"Calidad `{ds.get('quality_status')}` · fuente `{preferred_source(ds)}`  \n"
    f"Cobertura `{str(ds.get('coverage_start_utc') or '')[:19]}` → `{str(ds.get('coverage_end_utc') or '')[:19]}`"
)

q = httpx.get(f"{api}/v1/datasets/{ds['dataset_id']}/quality", timeout=30).json()
quality = q.get("quality") or q
col1, col2, col3, col4 = st.columns(4)
col1.metric("Duplicados", quality.get("duplicate_count", "—"))
col2.metric("Gaps", quality.get("gap_count", "—"))
col3.metric("Violaciones OHLC", quality.get("ohlc_violations", "—"))
col4.metric("Estado", quality.get("quality_status") or ds.get("quality_status") or "—")

gaps = quality.get("gaps") or []
if gaps:
    st.subheader("Gaps clasificados")
    st.caption("`session_closed` = cierre de sesión / noche / fin de semana, no un fallo de ingesta.")
    st.dataframe(gaps, use_container_width=True, hide_index=True)

with st.expander("Linaje y JSON completo"):
    st.json(ds)
    st.json(q)
