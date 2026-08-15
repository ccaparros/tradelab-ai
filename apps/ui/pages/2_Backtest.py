import os

import httpx
import streamlit as st

st.set_page_config(page_title="Backtest | TradeLab AI", layout="wide")
st.title("Backtest ORB+ATR")

api = os.getenv("API_BASE_URL", "http://localhost:8000")
datasets = httpx.get(f"{api}/v1/datasets", timeout=30).json().get("items", [])
usable = [d for d in datasets if d.get("quality_status") == "usable"] or datasets
if not usable:
    st.warning("Sin datasets")
    st.stop()

ds = st.selectbox("Dataset", usable, format_func=lambda d: f"{d.get('instrument')} {d['dataset_id'][:8]}")
params = {
    "opening_range_minutes": st.selectbox("Opening range (min)", [15, 30]),
    "atr_period": st.number_input("ATR period", 5, 50, 14),
    "atr_filter_mult": st.number_input("ATR filter mult", 0.0, 5.0, 0.0),
    "stop_risk_mult": st.number_input("Stop mult", 0.1, 5.0, 1.0),
    "target_risk_mult": st.number_input("Target mult", 0.1, 10.0, 2.0),
    "session_exit_time": st.text_input("Session exit", "15:45"),
    "commission_per_side": st.number_input("Commission/side", 0.0, 10.0, 0.62),
    "slippage_ticks": st.number_input("Slippage ticks", 0, 10, 1),
}

if st.button("Ejecutar backtest", type="primary"):
    # Prefer usable status
    from tradelab.datasets.store import get_dataset, upsert_dataset

    row = get_dataset(ds["dataset_id"])
    if row and row.get("quality_status") != "usable":
        row["quality_status"] = "usable"
        upsert_dataset(row)
    r = httpx.post(
        f"{api}/v1/experiments",
        json={
            "dataset_id": ds["dataset_id"],
            "strategy_id": "orb_atr_intraday",
            "parameters": params,
            "consume_holdout": False,
        },
        timeout=120,
    )
    if r.status_code >= 400:
        st.error(r.text)
    else:
        body = r.json()
        st.success(f"Experiment {body['experiment_id']} hash={body['integrity_hash'][:12]}…")
        st.json(body["metrics_by_split"])
