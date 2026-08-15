import os

import httpx
import streamlit as st

st.set_page_config(page_title="Análisis | TradeLab AI", layout="wide")
st.title("Copiloto de investigación")
st.caption("Cifras solo desde tools — sin órdenes reales.")

api = os.getenv("API_BASE_URL", "http://localhost:8000")
query = st.text_area("Pregunta", "¿Por qué el resultado de validación es peor que train y qué evidencia lo demuestra?")
dataset_id = st.text_input("dataset_id (opcional)")
experiment_id = st.text_input("experiment_id (opcional)")

if st.button("Analizar", type="primary"):
    payload = {"query": query}
    if dataset_id:
        payload["dataset_id"] = dataset_id
    if experiment_id:
        payload["experiment_id"] = experiment_id
    r = httpx.post(f"{api}/v1/analysis", json=payload, timeout=120)
    if r.status_code >= 400:
        st.error(r.text)
    else:
        body = r.json()
        st.subheader(f"Estado: {body['status']}")
        st.write(body["answer"])
        st.write("Métricas")
        st.json(body.get("metrics"))
        st.write("Fuentes")
        st.json(body.get("sources"))
        st.write("Tools")
        st.json(body.get("tool_invocations"))
