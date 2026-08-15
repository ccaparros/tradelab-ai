"""TradeLab AI Streamlit entrypoint — research workspace."""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(page_title="TradeLab AI", layout="wide")
st.title("TradeLab AI")
st.caption("Plataforma de investigación cuantitativa auditable — sin trading real.")

api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
st.info(
    f"Demo mode: `{os.getenv('DEMO_MODE', 'true')}`. "
    f"API: `{api_base}`. Usa el menú de páginas para Catálogo, Backtest y Análisis."
)
st.markdown(
    """
### Flujo de investigación
1. **Catálogo** — calidad y linaje de datasets  
2. **Backtest** — ORB+ATR determinista con costes  
3. **Análisis** — explicación citada (cifras solo desde tools)

Consulta `specs/001-tradelab-mvp/quickstart.md` para validar el happy path sin broker.
"""
)
