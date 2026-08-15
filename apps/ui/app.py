"""TradeLab AI Streamlit entrypoint — research workspace."""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(page_title="TradeLab AI", layout="wide")
st.title("TradeLab AI")
st.caption("Investigación cuantitativa auditable — sin trading real ni órdenes.")

api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
st.info(f"API: `{api_base}` · demo_mode=`{os.getenv('DEMO_MODE', 'true')}`")

st.markdown(
    """
### Flujo
1. **Catálogo** — elige dataset por instrumento y cobertura (DEMO vs histórico real).
2. **Backtest** — ORB+ATR con costes; el holdout queda bloqueado por defecto.
3. **Análisis** — selecciona dataset y experimento en listas; el copiloto cita tools e informes.

En Análisis **no pegues UUIDs**: si dejas “sin experimento”, el copiloto no podrá hablar de PnL.
"""
)
