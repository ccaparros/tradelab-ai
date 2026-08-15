import os

import httpx
import streamlit as st

st.set_page_config(page_title="Catálogo | TradeLab AI", layout="wide")
st.title("Catálogo y calidad")

api = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    datasets = httpx.get(f"{api}/v1/datasets", timeout=30).json().get("items", [])
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo contactar la API ({api}): {exc}")
    st.stop()

if not datasets:
    st.warning("No hay datasets. Ejecuta `tradelab-load-demo` o POST /v1/ingestions.")
else:
    labels = {f"{d.get('instrument')} {d.get('contract_month')} ({d['dataset_id'][:8]})": d for d in datasets}
    choice = st.selectbox("Dataset", list(labels.keys()))
    ds = labels[choice]
    st.json(ds)
    q = httpx.get(f"{api}/v1/datasets/{ds['dataset_id']}/quality", timeout=30).json()
    st.subheader("Informe de calidad")
    st.json(q)
